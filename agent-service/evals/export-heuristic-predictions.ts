/**
 * Export the production heuristic router's predictions for a set of asks.
 *
 * The ML experiment lives in Python; the heuristic router lives in TypeScript
 * and is the baseline every candidate is measured against. Rather than
 * reimplement its scoring in Python — which would benchmark a copy of the
 * baseline rather than the baseline — this runs the real `classifyHeuristic`
 * and writes what it decided.
 *
 * Reads JSONL on stdin (one {"ask": "..."} per line), writes JSONL on stdout
 * with the ranked candidates, the top-1 confidence, and whether any department
 * scored at all.
 *
 *   node --experimental-strip-types evals/export-heuristic-predictions.ts < asks.jsonl > preds.jsonl
 */

delete process.env.ANTHROPIC_API_KEY;

import { createInterface } from "node:readline";
import { classifyHeuristic } from "../src/agent-os/agents/_classifier.ts";

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });

for await (const line of rl) {
  const trimmed = line.trim();
  if (!trimmed) continue;
  const { ask } = JSON.parse(trimmed) as { ask: string };

  const started = process.hrtime.bigint();
  const { candidates } = classifyHeuristic(ask);
  const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;

  process.stdout.write(
    JSON.stringify({
      ask,
      // `null` rather than a guess: a department that scored nothing was not
      // chosen, and recording it as a wrong prediction would hide the failure
      // mode this whole experiment exists to measure.
      predicted: candidates[0]?.agentId ?? null,
      confidence: candidates[0]?.confidence ?? 0,
      score: candidates[0]?.score ?? 0,
      top2: candidates.slice(0, 2).map((c) => c.agentId),
      ranked: candidates.map((c) => ({ agentId: c.agentId, confidence: c.confidence, score: c.score })),
      no_evidence: candidates.length === 0,
      latency_ms: elapsedMs,
    }) + "\n",
  );
}
