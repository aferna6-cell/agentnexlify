/**
 * Haiku-vs-H proposal-level unsafe-action measurement runner.
 *
 * Locked protocol:
 *   1. Not live e2e. Proposal-level safety-gate on frozen labels.
 *      FakeGmailPort + in-memory executor only. No live Gmail, no real send.
 *   2. Null department = dept miss, NOT unsafe (no action yielded).
 *   3. Safety predicates are copied from safety-gate safetyVerdict.
 *      Do not load the action-eval harness core (it deletes ANTHROPIC_API_KEY).
 *   4. Frozen action-eval-v1, n=215 always. Nulls are wrong for dept acc.
 *   5. Haiku arm: classifyWithHaiku only. No production-classifier fallback.
 *      H arm: classifyHeuristic only.
 *   6. Blob SHA of _classifier.ts must be the signed freeze or abort.
 *   7. Missing ANTHROPIC_API_KEY when the Haiku arm is requested: exit 2,
 *      no heuristic numbers.
 *   8. ZERO writes to live os_tool_executions. In-memory store + FakeGmailPort
 *      only. Any code path that could persist to the production table aborts.
 *
 *   npm run eval:haiku-vs-h-unsafe
 *   npm run eval:haiku-vs-h-unsafe -- --arm h
 *   npm run eval:haiku-vs-h-unsafe -- --arm haiku
 *   npm run eval:haiku-vs-h-unsafe -- --require-key
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  classifyHeuristic,
  classifyWithHaiku,
} from "../src/agent-os/agents/_classifier.ts";
import {
  setRunStore,
  type RunStore,
} from "../src/agent-os/lib/providers/run-store.ts";
import { clopperPearson95 } from "./lib/clopper-pearson.ts";
import { ClassifierBlobMismatchError } from "./lib/haiku-vs-h-protocol.ts";
import { assertNoLivePersistImports } from "./lib/live-db-lock.ts";
import {
  DEFAULT_CLASSIFIER_PATH,
  DEFAULT_DATASET_PATH,
  DEFAULT_UNSAFE_RESULTS_DIR,
  EXPECTED_N,
  HAIKU_MODEL_ID,
  PROTOCOL_ID,
  PROTOCOL_SCOPE,
  PROTOCOL_TEMPERATURE,
  WINNER_HOLD_NOTE,
  aggregateUnsafeArm,
  assertClassifierBlobSha,
  gitSha,
  hasAnthropicApiKey,
  loadFrozenUnsafeDataset,
  measureProposalCase,
  type CaseArmScore,
  type UnsafeArmTotals,
} from "./lib/haiku-vs-h-unsafe-protocol.ts";

const HERE = dirname(fileURLToPath(import.meta.url));

const SOURCE_LOCK_FILES = [
  {
    label: "run-haiku-vs-h-unsafe.ts",
    path: join(HERE, "run-haiku-vs-h-unsafe.ts"),
  },
  {
    label: "haiku-vs-h-unsafe-protocol.ts",
    path: join(HERE, "lib", "haiku-vs-h-unsafe-protocol.ts"),
  },
  {
    label: "safety-predicates.ts",
    path: join(HERE, "lib", "safety-predicates.ts"),
  },
  {
    label: "fake-gmail-port.ts",
    path: join(HERE, "lib", "fake-gmail-port.ts"),
  },
];

function assertEntrypointCannotHitLiveDb(): void {
  for (const file of SOURCE_LOCK_FILES) {
    assertNoLivePersistImports(readFileSync(file.path, "utf8"), file.label);
  }
}

type ArmName = "h" | "haiku" | "both";

function parseArgs(argv: string[]): {
  requireKey: boolean;
  outPath: string | null;
  arm: ArmName;
} {
  let requireKey = false;
  let outPath: string | null = null;
  let arm: ArmName = "both";
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--require-key") requireKey = true;
    else if (arg === "--out") {
      outPath = argv[++i] ?? null;
      if (!outPath) {
        console.error("error: --out requires a path");
        process.exit(2);
      }
    } else if (arg === "--arm") {
      const value = argv[++i];
      if (value !== "h" && value !== "haiku" && value !== "both") {
        console.error("error: --arm must be h, haiku, or both");
        process.exit(2);
      }
      arm = value;
    }
  }
  return { requireKey, outPath, arm };
}

function costCollectorStore(): RunStore {
  return {
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
    async logModelCall() {},
  };
}

function refuseMissingKey(requireKey: boolean): never {
  const extra = requireKey ? " (--require-key)" : "";
  console.error(
    `ANTHROPIC_API_KEY is not set${extra}. Refusing to run. ` +
      "The Haiku arm calls classifyWithHaiku only and never falls back to the " +
      "production classifier or classifyHeuristic. This command will not emit heuristic numbers. " +
      "Re-run with ANTHROPIC_API_KEY in the process env to measure Haiku.",
  );
  process.exit(2);
}

async function runHArm(
  cases: ReturnType<typeof loadFrozenUnsafeDataset>["cases"],
  context: ReturnType<typeof loadFrozenUnsafeDataset>["businessContext"],
): Promise<CaseArmScore[]> {
  const out: CaseArmScore[] = [];
  for (const c of cases) {
    const cls = classifyHeuristic(c.ask);
    out.push(await measureProposalCase(c, cls, context));
  }
  return out;
}

async function runHaikuArm(
  cases: ReturnType<typeof loadFrozenUnsafeDataset>["cases"],
  context: ReturnType<typeof loadFrozenUnsafeDataset>["businessContext"],
): Promise<CaseArmScore[]> {
  const out: CaseArmScore[] = [];
  for (const c of cases) {
    let cls = null;
    try {
      cls = await classifyWithHaiku(c.ask, c.id);
    } catch {
      cls = null;
    }
    out.push(await measureProposalCase(c, cls, context));
  }
  return out;
}

function summarizeArm(name: string, totals: UnsafeArmTotals) {
  const k = totals.unsafe;
  const n = totals.n;
  const ci = clopperPearson95(k, n);
  return {
    arm: name,
    n,
    deptCorrect: totals.deptCorrect,
    acc: totals.acc,
    nulls: totals.nulls,
    errors: totals.errors,
    unsafe: k,
    unsafeCaseIds: totals.unsafeCaseIds,
    unsafeCi95: {
      k,
      n,
      lower: ci.lower,
      upper: ci.upper,
      method: "clopper-pearson",
    },
  };
}

async function main(): Promise<void> {
  const { requireKey, outPath, arm } = parseArgs(process.argv.slice(2));
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

  try {
    assertEntrypointCannotHitLiveDb();
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
  }

  const wantsHaiku = arm === "both" || arm === "haiku";
  if (wantsHaiku && !hasAnthropicApiKey()) {
    refuseMissingKey(requireKey);
  }
  if (requireKey && !hasAnthropicApiKey()) {
    refuseMissingKey(true);
  }

  const frozen = loadFrozenUnsafeDataset(datasetPath);
  if (frozen.cases.length !== EXPECTED_N) {
    console.error(
      `internal error: expected n=${EXPECTED_N}, got ${frozen.cases.length}`,
    );
    process.exit(1);
  }

  setRunStore(costCollectorStore());

  let hCases: CaseArmScore[] | null = null;
  let haikuCases: CaseArmScore[] | null = null;

  if (arm === "h" || arm === "both") {
    hCases = await runHArm(frozen.cases, frozen.businessContext);
  }
  if (arm === "haiku" || arm === "both") {
    haikuCases = await runHaikuArm(frozen.cases, frozen.businessContext);
  }

  const hTotals = hCases ? aggregateUnsafeArm(hCases) : null;
  const haikuTotals = haikuCases ? aggregateUnsafeArm(haikuCases) : null;

  for (const totals of [hTotals, haikuTotals]) {
    if (totals && totals.n !== EXPECTED_N) {
      console.error(
        `refusing to write results: n=${totals.n} (must be ${EXPECTED_N})`,
      );
      process.exit(1);
    }
  }

  const mcnemar =
    hCases && haikuCases
      ? frozen.cases.map((c, i) => ({
          id: c.id,
          expected: c.expected_department,
          h: hCases![i],
          haiku: haikuCases![i],
        }))
      : null;

  const result = {
    protocol: PROTOCOL_ID,
    scope: PROTOCOL_SCOPE,
    winner: null,
    winnerNote: WINNER_HOLD_NOTE,
    model: HAIKU_MODEL_ID,
    temperature: PROTOCOL_TEMPERATURE,
    blobSha,
    gitSha: gitSha(),
    dataset: "action-eval-v1",
    fallback: false,
    n: EXPECTED_N,
    liveE2e: false,
    liveGmail: false,
    liveOsToolExecutions: false,
    arms: {
      ...(hTotals ? { h: summarizeArm("h", hTotals) } : {}),
      ...(haikuTotals ? { haiku: summarizeArm("haiku", haikuTotals) } : {}),
    },
    cases: mcnemar,
    hCases,
    haikuCases,
  };

  const dest =
    outPath ??
    join(
      DEFAULT_UNSAFE_RESULTS_DIR,
      `haiku-vs-h-unsafe-${result.gitSha.slice(0, 12)}.json`,
    );
  mkdirSync(join(dest, ".."), { recursive: true });
  writeFileSync(dest, `${JSON.stringify(result, null, 2)}\n`);

  console.log(
    JSON.stringify(
      {
        wrote: dest,
        protocol: result.protocol,
        scope: result.scope,
        n: result.n,
        winner: result.winner,
        winnerNote: result.winnerNote,
        blobSha: result.blobSha,
        gitSha: result.gitSha,
        liveE2e: result.liveE2e,
        liveGmail: result.liveGmail,
        liveOsToolExecutions: result.liveOsToolExecutions,
        arms: result.arms,
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
