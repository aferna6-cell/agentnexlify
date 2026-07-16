/**
 * Market Research skill + web-search plumbing.
 *
 * Contract:
 *  1. runWebSearchLoop resumes on pause_turn (bounded), accumulates usage +
 *     search counts, and concatenates text blocks across turns.
 *  2. Research-shaped asks pick the market_research skill inside Marketing.
 *  3. Without an API key the agent returns an honest noDraftReason - never
 *     an ungrounded "research" draft.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { runWebSearchLoop } from "../../lib/anthropic.ts";
import { pickSkill } from "../_department.ts";
import { marketing } from "../departments.ts";
import { marketResearch } from "./agent.ts";
import type { SharedContext } from "../../types/agent.ts";

function response(opts: {
  stop?: string;
  text?: string;
  searches?: number;
  input?: number;
  output?: number;
}) {
  return {
    stop_reason: opts.stop ?? "end_turn",
    content: opts.text ? [{ type: "text", text: opts.text }] : [],
    usage: {
      input_tokens: opts.input ?? 10,
      output_tokens: opts.output ?? 5,
      server_tool_use: { web_search_requests: opts.searches ?? 0 },
    },
  };
}

test("runWebSearchLoop resumes on pause_turn and accumulates usage", async () => {
  const calls: unknown[][] = [];
  const responses = [
    response({ stop: "pause_turn", text: "Part one. ", searches: 2 }),
    response({ stop: "end_turn", text: "Part two.", searches: 1 }),
  ];
  const result = await runWebSearchLoop(async (messages) => {
    calls.push([...messages]);
    return responses[calls.length - 1]!;
  }, "research brake prices");

  assert.equal(result.text, "Part one. Part two.");
  assert.equal(result.webSearches, 3);
  assert.equal(result.inputTokens, 20);
  assert.equal(result.outputTokens, 10);
  assert.equal(calls.length, 2);
  // The resume carries the partial assistant turn back.
  assert.equal((calls[1]![1] as { role: string }).role, "assistant");
});

test("runWebSearchLoop bounds pause_turn resumes", async () => {
  let n = 0;
  const result = await runWebSearchLoop(
    async () => {
      n++;
      return response({ stop: "pause_turn", text: "x" });
    },
    "ask",
    2,
  );
  // initial call + 2 resumes, then the bound stops the loop.
  assert.equal(n, 3);
  assert.equal(result.text, "xxx");
});

test("research asks pick the market_research skill in Marketing", () => {
  const spec = (marketing as unknown as { __department: Parameters<typeof pickSkill>[0] }).__department;
  for (const ask of [
    "Research what other auto shops charge for brake jobs",
    "Find out what people are saying about online booking",
    "What's the going rate for lawn care in our area?",
  ]) {
    assert.equal(pickSkill(spec, ask).agent.agent_id, "market_research", ask);
  }
  // Non-research marketing asks stay with their own skills.
  assert.notEqual(
    pickSkill(spec, "Write a Facebook post about our weekend hours").agent.agent_id,
    "market_research",
  );
});

test("agent returns an honest no-draft outage without an API key", async () => {
  // Test env has no ANTHROPIC_API_KEY: the model is unavailable, and web
  // research must refuse rather than fabricate an ungrounded report.
  const traces: string[] = [];
  const context = {
    businessProfile: { businessName: "Keys Koffee", businessType: "cafe" },
    pipelineLeads: [],
    kb: [],
  } as unknown as SharedContext;

  const out = await marketResearch.run({
    ownerAsk: "Research oat milk supplier pricing",
    input: {},
    context,
    runId: "run-1",
    emitTrace: {
      emit: async (step: string) => {
        traces.push(step);
      },
      work: async (step: string) => {
        traces.push(step);
      },
    },
  } as never);

  assert.equal(out.draft, undefined);
  assert.ok(out.noDraftReason?.includes("live model"));
  assert.ok(out.orchestratorNotes?.some((n: string) => n.includes("temporarily unavailable")));
});
