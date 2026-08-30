/**
 * Export the production LLM router's predictions (Model D in the routing
 * benchmark), and — when no credential is present — the cost this evaluation
 * would incur.
 *
 * Two things this deliberately keeps apart:
 *
 *   llm_predicted        what the model itself returned
 *   fallback_used        whether the run fell back to the heuristic
 *
 * `classify()` silently falls back to `classifyHeuristic` when Haiku is
 * unavailable, unparseable, or returns an id that maps to no department. That
 * is correct product behaviour and useless benchmark behaviour: scoring the
 * blend would credit the LLM for the heuristic's answers. This calls
 * `classifyWithHaiku` directly and records `null` where it failed, so the
 * malformed rate is visible instead of absorbed.
 *
 *   node --experimental-strip-types evals/export-llm-predictions.ts < asks.jsonl
 *   node --experimental-strip-types evals/export-llm-predictions.ts --estimate-only < asks.jsonl
 */

import { createInterface } from "node:readline";
import { classifyWithHaiku } from "../src/agent-os/agents/_classifier.ts";
import { registry } from "../src/agent-os/agents/_registry.ts";
import {
  estimateCostUsd,
  isModelAvailable,
} from "../src/agent-os/lib/anthropic.ts";

const ROUTING_MODEL =
  process.env.ANTHROPIC_MODEL_ROUTING ?? "claude-haiku-4-5-20251001";
const estimateOnly = process.argv.includes("--estimate-only");
const liveRequested = process.argv.includes("--live");

/** The catalogue block the routing prompt embeds, verbatim from the registry. */
function cataloguePromptSize(): number {
  return registry
    .routable()
    .map(
      (a) =>
        `- ${a.agent_id} (${a.bucket}): ${a.purpose} Routes here when: ${a.routes_here_when.join("; ")}`,
    )
    .join("\n").length;
}

/** ~4 characters per token: adequate for a cost estimate, stated as approximate. */
const CHARS_PER_TOKEN = 4;
/** Fixed instruction text in `buildRoutingPrompt`, measured rather than guessed. */
const SYSTEM_OVERHEAD_CHARS = 520;
/** Observed shape of the JSON the router is asked to return. */
const OUTPUT_TOKENS_PER_CALL = 90;

const asks: string[] = [];
const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  const t = line.trim();
  if (t) asks.push((JSON.parse(t) as { ask: string }).ask);
}

const promptChars = cataloguePromptSize() + SYSTEM_OVERHEAD_CHARS;
const meanAskChars = asks.length
  ? asks.reduce((s, a) => s + a.length, 0) / asks.length
  : 0;
const inputTokens = Math.round(
  (promptChars + meanAskChars + 20) / CHARS_PER_TOKEN,
);
const costPerCall = estimateCostUsd(
  ROUTING_MODEL,
  inputTokens,
  OUTPUT_TOKENS_PER_CALL,
);

const estimate = {
  kind: "estimate",
  model: ROUTING_MODEL,
  credential_present: isModelAvailable(),
  asks: asks.length,
  approx_input_tokens_per_call: inputTokens,
  assumed_output_tokens_per_call: OUTPUT_TOKENS_PER_CALL,
  approx_cost_usd_per_call: Number(costPerCall.toFixed(6)),
  approx_cost_usd_per_1k_calls: Number((costPerCall * 1000).toFixed(4)),
  approx_cost_usd_for_this_run: Number((costPerCall * asks.length).toFixed(4)),
  note:
    "Token counts are a 4-chars-per-token approximation over the real routing prompt " +
    "(registry catalogue + fixed instructions + the ask). Prompt caching is not modelled; " +
    "with the catalogue cached the input cost would be materially lower.",
};

if (liveRequested && !isModelAvailable()) {
  console.error(
    "Haiku evaluation requested but ANTHROPIC_API_KEY is unavailable.",
  );
  process.exit(2);
}

if (estimateOnly || !liveRequested) {
  estimate.note += " Live calls require the explicit --live flag.";
  console.log(JSON.stringify(estimate, null, 2));
  process.exit(0);
}

let malformed = 0;
for (const ask of asks) {
  const started = process.hrtime.bigint();
  const cls = await classifyWithHaiku(ask);
  const latencyMs = Number(process.hrtime.bigint() - started) / 1e6;
  if (!cls || cls.candidates.length === 0) malformed++;
  console.log(
    JSON.stringify({
      ask,
      llm_predicted: cls?.candidates[0]?.agentId ?? null,
      confidence: cls?.candidates[0]?.confidence ?? 0,
      ranked: (cls?.candidates ?? []).map((c) => c.agentId),
      // True when the LLM produced nothing usable. Production would fall back to
      // the heuristic here; the benchmark must not.
      fallback_would_be_used: !cls || cls.candidates.length === 0,
      latency_ms: latencyMs,
    }),
  );
}
console.error(
  JSON.stringify({
    ...estimate,
    kind: "run_summary",
    malformed_or_unmapped: malformed,
  }),
);
