/**
 * Anthropic SDK wrapper with cost tracking.
 *
 * Every model call is logged to ModelCallLog (model, tokens, cost) so credit
 * exhaustion is never silent — the failure mode the previous product had. Per
 * the cost-discipline plan, routing/classification uses Haiku and owner-facing
 * drafts use Sonnet. When ANTHROPIC_API_KEY is unset the client is unavailable
 * and `complete()` throws ModelUnavailableError, which agents translate into an
 * honest "service temporarily unavailable" message (never a silent empty draft).
 */

import Anthropic from "@anthropic-ai/sdk";
import { getRunStore } from "./providers/run-store.ts";
import { isCapExceeded } from "./usage.ts";

export type ModelPurpose = "routing" | "draft" | "other";

const ROUTING_MODEL = process.env.ANTHROPIC_MODEL_ROUTING ?? "claude-haiku-4-5-20251001";
const DRAFT_MODEL = process.env.ANTHROPIC_MODEL_DRAFT ?? "claude-sonnet-4-6";

/** USD per million tokens. Update as pricing changes. */
const PRICING: Record<string, { input: number; output: number }> = {
  "claude-haiku-4-5-20251001": { input: 1.0, output: 5.0 },
  "claude-sonnet-4-6": { input: 3.0, output: 15.0 },
};

/** Anthropic server-side web search: USD per 1,000 searches. */
const WEB_SEARCH_USD_PER_1000 = 10.0;

function priceFor(model: string): { input: number; output: number } {
  return PRICING[model] ?? { input: 3.0, output: 15.0 };
}

export function estimateCostUsd(model: string, inputTokens: number, outputTokens: number): number {
  const p = priceFor(model);
  return (inputTokens / 1_000_000) * p.input + (outputTokens / 1_000_000) * p.output;
}

export class ModelUnavailableError extends Error {
  constructor(message = "Anthropic API key not configured") {
    super(message);
    this.name = "ModelUnavailableError";
  }
}

/** Thrown when the daily usage cap for a purpose is hit (offline fallback then applies). */
export class UsageCapExceededError extends Error {
  readonly purpose: "routing" | "draft";
  constructor(purpose: "routing" | "draft", message = `Daily ${purpose} usage cap reached`) {
    super(message);
    this.purpose = purpose;
    this.name = "UsageCapExceededError";
  }
}

let client: Anthropic | null | undefined;
function getClient(): Anthropic | null {
  if (client !== undefined) return client;
  const apiKey = process.env.ANTHROPIC_API_KEY;
  client = apiKey ? new Anthropic({ apiKey }) : null;
  return client;
}

export function isModelAvailable(): boolean {
  return getClient() !== null;
}

export interface CompleteArgs {
  purpose: ModelPurpose;
  system: string;
  prompt: string;
  maxTokens?: number;
  /** Associates the cost log with an agent run. */
  runId?: string;
  /** Override the model; defaults to the per-purpose model. */
  model?: string;
}

export interface CompleteResult {
  text: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

/** Run a completion, logging cost. Throws ModelUnavailableError when no key. */
export async function complete(args: CompleteArgs): Promise<CompleteResult> {
  const model =
    args.model ?? (args.purpose === "routing" ? ROUTING_MODEL : DRAFT_MODEL);
  const anthropic = getClient();

  if (!anthropic) {
    await logCall({ runId: args.runId, purpose: args.purpose, model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: "no_api_key" });
    throw new ModelUnavailableError();
  }

  // Hard daily cap (demo spend protection). When hit, refuse BEFORE calling
  // Anthropic so the agent falls back to the offline composer honestly.
  if ((args.purpose === "routing" || args.purpose === "draft") && (await isCapExceeded(args.purpose))) {
    await logCall({ runId: args.runId, purpose: args.purpose, model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: "usage_cap_exceeded" });
    throw new UsageCapExceededError(args.purpose);
  }

  try {
    const res = await anthropic.messages.create({
      model,
      max_tokens: args.maxTokens ?? 1024,
      system: args.system,
      messages: [{ role: "user", content: args.prompt }],
    });
    const inputTokens = res.usage.input_tokens;
    const outputTokens = res.usage.output_tokens;
    const costUsd = estimateCostUsd(model, inputTokens, outputTokens);
    const text = res.content
      .filter((b): b is Anthropic.TextBlock => b.type === "text")
      .map((b) => b.text)
      .join("");
    await logCall({ runId: args.runId, purpose: args.purpose, model, inputTokens, outputTokens, costUsd, ok: true });
    return { text, model, inputTokens, outputTokens, costUsd };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    await logCall({ runId: args.runId, purpose: args.purpose, model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: message });
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Web-grounded completion (market research). Uses Anthropic's server-side
// web_search tool: no external search credentials, runs on the platform key.
// The API may stop with `pause_turn` mid-search; the loop resumes by sending
// the partial assistant turn back, bounded so a stuck search can't spin.
// ---------------------------------------------------------------------------

export interface WebSearchLoopResult {
  text: string;
  inputTokens: number;
  outputTokens: number;
  webSearches: number;
}

interface LoopResponse {
  stop_reason?: string | null;
  content: unknown[];
  usage: {
    input_tokens: number;
    output_tokens: number;
    server_tool_use?: { web_search_requests?: number } | null;
  };
}

/**
 * Pure pause_turn resume loop, injectable for tests. `createFn` performs one
 * messages.create call with the running message list and returns the response.
 */
export async function runWebSearchLoop(
  createFn: (messages: { role: string; content: unknown }[]) => Promise<LoopResponse>,
  prompt: string,
  maxResumes = 3,
): Promise<WebSearchLoopResult> {
  const messages: { role: string; content: unknown }[] = [{ role: "user", content: prompt }];
  let inputTokens = 0;
  let outputTokens = 0;
  let webSearches = 0;
  const texts: string[] = [];

  for (let turn = 0; ; turn++) {
    const res = await createFn(messages);
    inputTokens += res.usage.input_tokens;
    outputTokens += res.usage.output_tokens;
    webSearches += res.usage.server_tool_use?.web_search_requests ?? 0;
    for (const block of res.content) {
      const b = block as { type?: string; text?: string };
      if (b.type === "text" && typeof b.text === "string") texts.push(b.text);
    }
    if (res.stop_reason !== "pause_turn" || turn >= maxResumes) break;
    // Resume: hand the partial assistant turn back and let it continue.
    messages.push({ role: "assistant", content: res.content });
  }

  return { text: texts.join(""), inputTokens, outputTokens, webSearches };
}

export interface WebSearchCompleteArgs {
  system: string;
  prompt: string;
  maxTokens?: number;
  runId?: string;
  model?: string;
  /** Cap on server-side searches per request (spend control). */
  maxSearches?: number;
}

/**
 * Run a web-grounded completion (server-side web_search tool), logging cost
 * including the per-search fee. Throws ModelUnavailableError when no key and
 * UsageCapExceededError at the daily draft cap - callers surface an honest
 * "temporarily unavailable" instead of an ungrounded draft.
 */
export async function completeWithWebSearch(args: WebSearchCompleteArgs): Promise<CompleteResult> {
  const model = args.model ?? DRAFT_MODEL;
  const anthropic = getClient();

  if (!anthropic) {
    await logCall({ runId: args.runId, purpose: "draft", model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: "no_api_key" });
    throw new ModelUnavailableError();
  }
  if (await isCapExceeded("draft")) {
    await logCall({ runId: args.runId, purpose: "draft", model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: "usage_cap_exceeded" });
    throw new UsageCapExceededError("draft");
  }

  try {
    const loop = await runWebSearchLoop(
      (messages) =>
        anthropic.messages.create({
          model,
          max_tokens: args.maxTokens ?? 2048,
          system: args.system,
          messages: messages as Anthropic.MessageParam[],
          tools: [
            {
              type: "web_search_20250305",
              name: "web_search",
              max_uses: args.maxSearches ?? 3,
            },
          ],
        }) as unknown as Promise<LoopResponse>,
      args.prompt,
    );
    const costUsd =
      estimateCostUsd(model, loop.inputTokens, loop.outputTokens) +
      (loop.webSearches / 1000) * WEB_SEARCH_USD_PER_1000;
    await logCall({ runId: args.runId, purpose: "draft", model, inputTokens: loop.inputTokens, outputTokens: loop.outputTokens, costUsd, ok: true });
    return { text: loop.text, model, inputTokens: loop.inputTokens, outputTokens: loop.outputTokens, costUsd };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    await logCall({ runId: args.runId, purpose: "draft", model, inputTokens: 0, outputTokens: 0, costUsd: 0, ok: false, error: message });
    throw err;
  }
}

async function logCall(args: {
  runId?: string;
  purpose: ModelPurpose;
  model: string;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  ok: boolean;
  error?: string;
}): Promise<void> {
  try {
    await getRunStore().logModelCall({
      runId: args.runId,
      purpose: args.purpose,
      model: args.model,
      inputTokens: args.inputTokens,
      outputTokens: args.outputTokens,
      costUsd: args.costUsd,
      ok: args.ok,
      error: args.error,
    });
  } catch {
    // Never let cost logging break a request.
  }
}

export { ROUTING_MODEL, DRAFT_MODEL };
