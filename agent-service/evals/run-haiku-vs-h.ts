/**
 * Haiku-vs-H measurement runner (routing-only, no fallback).
 *
 * Signed protocol:
 *   1. Freeze-check blob SHA of agents/_classifier.ts before any scoring.
 *   2. Call classifyWithHaiku ONLY for every frozen action-eval-v1 case (n=215).
 *   3. Do not call classify() or classifyHeuristic. Do not import eval-core
 *      (it deletes ANTHROPIC_API_KEY).
 *   4. Null / throw / empty candidates → predicted null, scored incorrect.
 *   5. Never drop cases. n is always 215.
 *   6. Routing-only: no tools, no send_email, no action executor. unsafe = N/A.
 *
 * Missing ANTHROPIC_API_KEY: exit 2, no heuristic numbers.
 * --require-key: same fail-closed gate, for explicit CI invocation.
 *
 * This runner does not ship a winner. Compare Haiku acc against a separately
 * measured heuristic H on the same frozen labels; that decision is human.
 *
 *   npm run eval:haiku-vs-h
 *   npm run eval:haiku-vs-h -- --require-key
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { classifyWithHaiku } from "../src/agent-os/agents/_classifier.ts";
import {
  setRunStore,
  type RunStore,
} from "../src/agent-os/lib/providers/run-store.ts";
import {
  ClassifierBlobMismatchError,
  DEFAULT_CLASSIFIER_PATH,
  DEFAULT_DATASET_PATH,
  DEFAULT_RESULTS_DIR,
  EXPECTED_N,
  HAIKU_MODEL_ID,
  PROTOCOL_TEMPERATURE,
  UNSAFE_NOTE,
  aggregateScores,
  assertClassifierBlobSha,
  gitSha,
  hasAnthropicApiKey,
  loadFrozenCases,
  scorePrediction,
  type CaseScore,
  type HaikuVsHResult,
} from "./lib/haiku-vs-h-protocol.ts";

function parseArgs(argv: string[]): {
  requireKey: boolean;
  outPath: string | null;
} {
  let requireKey = false;
  let outPath: string | null = null;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--require-key") requireKey = true;
    else if (arg === "--out") {
      outPath = argv[++i] ?? null;
      if (!outPath) {
        console.error("error: --out requires a path");
        process.exit(2);
      }
    }
  }
  return { requireKey, outPath };
}

function costCollector(): {
  store: RunStore;
  costFor: (runId: string) => number;
} {
  const costs = new Map<string, number>();
  const store: RunStore = {
    async createRoutingDecision() {
      return { id: "eval-rd" };
    },
    async markRoutingDecisionOverridden() {},
    async createRun() {
      return { id: "eval-run" };
    },
    async setRunStatus() {},
    async createDraft() {
      return { id: "eval-draft" };
    },
    async captureWishlist() {},
    async recordTraceStep() {},
    async logModelCall(input) {
      if (!input.runId) return;
      costs.set(
        input.runId,
        (costs.get(input.runId) ?? 0) + (input.costUsd ?? 0),
      );
    },
  };
  return {
    store,
    costFor(runId: string) {
      return costs.get(runId) ?? 0;
    },
  };
}

async function measureCase(
  id: string,
  ask: string,
  expected: string,
  costFor: (runId: string) => number,
): Promise<CaseScore> {
  let predicted: string | null = null;
  let threw = false;
  try {
    const cls = await classifyWithHaiku(ask, id);
    predicted = cls?.candidates[0]?.agentId ?? null;
  } catch {
    threw = true;
    predicted = null;
  }
  const scored = scorePrediction(predicted, expected);
  return {
    id,
    predicted: scored.predicted,
    expected,
    null: scored.isNull,
    cost: costFor(id),
    correct: scored.correct,
    error: threw,
  };
}

async function main(): Promise<void> {
  const { requireKey, outPath } = parseArgs(process.argv.slice(2));
  const classifierPath =
    process.env.HAIKU_VS_H_CLASSIFIER_PATH ?? DEFAULT_CLASSIFIER_PATH;
  const datasetPath =
    process.env.HAIKU_VS_H_DATASET_PATH ?? DEFAULT_DATASET_PATH;

  let blobSha: string;
  try {
    blobSha = assertClassifierBlobSha(classifierPath);
  } catch (err) {
    const actual =
      err instanceof ClassifierBlobMismatchError ? err.actualSha : "unknown";
    console.error(err instanceof Error ? err.message : String(err));
    if (!(err instanceof ClassifierBlobMismatchError)) {
      console.error(`classifier blob SHA (actual): ${actual}`);
    }
    process.exit(1);
  }

  if (!hasAnthropicApiKey()) {
    const extra = requireKey ? " (--require-key)" : "";
    console.error(
      `ANTHROPIC_API_KEY is not set${extra}. Refusing to run. ` +
        "This runner never falls back to the heuristic and will not emit heuristic numbers. " +
        "Re-run with ANTHROPIC_API_KEY in the process env to measure Haiku.",
    );
    process.exit(2);
  }

  const frozen = loadFrozenCases(datasetPath);
  if (frozen.length !== EXPECTED_N) {
    console.error(
      `internal error: expected n=${EXPECTED_N}, got ${frozen.length}`,
    );
    process.exit(1);
  }

  const { store, costFor } = costCollector();
  setRunStore(store);

  const cases: CaseScore[] = [];
  for (const c of frozen) {
    cases.push(await measureCase(c.id, c.ask, c.expected_department, costFor));
  }

  const totals = aggregateScores(cases);
  if (totals.n !== EXPECTED_N) {
    console.error(
      `refusing to write results: n=${totals.n} (must be ${EXPECTED_N})`,
    );
    process.exit(1);
  }

  const result: HaikuVsHResult = {
    protocol: "haiku-vs-h-v1",
    scope: "routing-only",
    unsafe: null,
    unsafeNote: UNSAFE_NOTE,
    ...totals,
    model: HAIKU_MODEL_ID,
    temperature: PROTOCOL_TEMPERATURE,
    blobSha,
    gitSha: gitSha(),
    dataset: "action-eval-v1",
    fallback: false,
    winner: null,
    cases,
  };

  const dest =
    outPath ??
    join(DEFAULT_RESULTS_DIR, `haiku-vs-h-${result.gitSha.slice(0, 12)}.json`);
  mkdirSync(join(dest, ".."), { recursive: true });
  writeFileSync(dest, `${JSON.stringify(result, null, 2)}\n`);

  console.log(
    JSON.stringify(
      {
        wrote: dest,
        n: result.n,
        correct: result.correct,
        acc: result.acc,
        nulls: result.nulls,
        errors: result.errors,
        costUsd: result.costUsd,
        model: result.model,
        temperature: result.temperature,
        blobSha: result.blobSha,
        gitSha: result.gitSha,
        unsafe: result.unsafe,
        winner: result.winner,
        scope: result.scope,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
