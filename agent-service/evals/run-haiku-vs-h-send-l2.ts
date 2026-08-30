/**
 * Haiku-vs-H in-memory send/L2 measurement runner.
 *
 * Locked protocol:
 *   1. Frozen action-eval-v1 n=215. Dataset blob must be
 *      b9a662da7ac33c322b96c978e7ca49eb8a62e4bd. Classifier blob must be
 *      3a5251f6ee4c5b93839c5f87f721725610e9a8e2 or abort.
 *   2. Haiku arm: classifyWithHaiku only. H arm: classifyHeuristic only.
 *      NEVER import eval-core. NEVER fall back to classify() or
 *      classifyHeuristic on Haiku failure; record a null route.
 *   3. InMemoryActionStore + FakeGmailPort only. FakeGmailPort is injected
 *      on every send_email call. Never set SEND_EMAIL_ENABLED. Never leave
 *      the gmail port None.
 *   4. Primary scores: sendProposed / sendExecuted / unsafeL2 on n=215 plus
 *      gold-send n=56. Clopper-Pearson 95% CI for unsafeL2 k/n (n=215) only.
 *   5. winner is always null. liveE2e/liveGmail/liveOsToolExecutions false.
 *      gitSha is a 40-char hex from git or GIT_SHA; unknown aborts.
 *
 *   npm run eval:haiku-vs-h-send-l2
 *   npm run eval:haiku-vs-h-send-l2 -- --arm h
 *   npm run eval:haiku-vs-h-send-l2 -- --arm haiku
 *   npm run eval:haiku-vs-h-send-l2 -- --require-key
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
import { sendEmailFlagOn } from "./lib/eval-send-boundary.ts";
import { ClassifierBlobMismatchError } from "./lib/haiku-vs-h-protocol.ts";
import {
  DatasetBlobMismatchError,
  DEFAULT_CLASSIFIER_PATH,
  DEFAULT_DATASET_PATH,
  DEFAULT_SEND_L2_RESULTS_DIR,
  EXPECTED_N,
  HAIKU_MODEL_ID,
  PROTOCOL_ID,
  PROTOCOL_SCOPE,
  PROTOCOL_TEMPERATURE,
  WINNER_HOLD_NOTE,
  aggregateSendL2Arm,
  assertClassifierBlobSha,
  assertDatasetBlobSha,
  hasAnthropicApiKey,
  loadFrozenSendL2Dataset,
  measureSendL2Case,
  requireGitSha,
  resetSendEmailReceipts,
  type SendL2ArmTotals,
  type SendL2CaseScore,
} from "./lib/haiku-vs-h-send-l2-protocol.ts";
import { assertNoLivePersistImports } from "./lib/live-db-lock.ts";

const HERE = dirname(fileURLToPath(import.meta.url));

const SOURCE_LOCK_FILES = [
  {
    label: "run-haiku-vs-h-send-l2.ts",
    path: join(HERE, "run-haiku-vs-h-send-l2.ts"),
  },
  {
    label: "haiku-vs-h-send-l2-protocol.ts",
    path: join(HERE, "lib", "haiku-vs-h-send-l2-protocol.ts"),
  },
  {
    label: "eval-send-email.ts",
    path: join(HERE, "lib", "eval-send-email.ts"),
  },
  {
    label: "eval-send-boundary.ts",
    path: join(HERE, "lib", "eval-send-boundary.ts"),
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
  cases: ReturnType<typeof loadFrozenSendL2Dataset>["cases"],
  context: ReturnType<typeof loadFrozenSendL2Dataset>["businessContext"],
): Promise<SendL2CaseScore[]> {
  const out: SendL2CaseScore[] = [];
  for (const c of cases) {
    const cls = classifyHeuristic(c.ask);
    out.push(await measureSendL2Case(c, cls, context));
  }
  return out;
}

async function runHaikuArm(
  cases: ReturnType<typeof loadFrozenSendL2Dataset>["cases"],
  context: ReturnType<typeof loadFrozenSendL2Dataset>["businessContext"],
): Promise<SendL2CaseScore[]> {
  const out: SendL2CaseScore[] = [];
  for (const c of cases) {
    let cls = null;
    try {
      cls = await classifyWithHaiku(c.ask, c.id);
    } catch {
      cls = null;
    }
    out.push(await measureSendL2Case(c, cls, context));
  }
  return out;
}

function summarizeArm(name: string, totals: SendL2ArmTotals) {
  const k = totals.unsafeL2;
  const n = totals.n;
  const ci = clopperPearson95(k, n);
  return {
    arm: name,
    n,
    sendProposed: totals.sendProposed,
    sendExecuted: totals.sendExecuted,
    unsafeL2: k,
    unsafeL2CaseIds: totals.unsafeL2CaseIds,
    nulls: totals.nulls,
    errors: totals.errors,
    unsafeL2Ci95: {
      k,
      n,
      lower: ci.lower,
      upper: ci.upper,
      method: "clopper-pearson",
    },
    goldSend: totals.goldSend,
  };
}

async function main(): Promise<void> {
  const { requireKey, outPath, arm } = parseArgs(process.argv.slice(2));
  const classifierPath =
    process.env.HAIKU_VS_H_CLASSIFIER_PATH ?? DEFAULT_CLASSIFIER_PATH;
  const datasetPath =
    process.env.HAIKU_VS_H_DATASET_PATH ?? DEFAULT_DATASET_PATH;

  if (sendEmailFlagOn()) {
    console.error(
      "SEND_EMAIL_ENABLED is set. This eval runner never enables live send.",
    );
    process.exit(1);
  }

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

  let datasetSha: string;
  try {
    datasetSha = assertDatasetBlobSha(datasetPath);
  } catch (err) {
    const actual =
      err instanceof DatasetBlobMismatchError ? err.actualSha : "unknown";
    console.error(err instanceof Error ? err.message : String(err));
    if (!(err instanceof DatasetBlobMismatchError)) {
      console.error(`dataset blob SHA (actual): ${actual}`);
    }
    process.exit(1);
  }

  let gitShaValue: string;
  try {
    gitShaValue = requireGitSha();
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
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

  const frozen = loadFrozenSendL2Dataset(datasetPath);
  if (frozen.cases.length !== EXPECTED_N) {
    console.error(
      `internal error: expected n=${EXPECTED_N}, got ${frozen.cases.length}`,
    );
    process.exit(1);
  }

  setRunStore(costCollectorStore());
  resetSendEmailReceipts();

  let hCases: SendL2CaseScore[] | null = null;
  let haikuCases: SendL2CaseScore[] | null = null;

  if (arm === "h" || arm === "both") {
    hCases = await runHArm(frozen.cases, frozen.businessContext);
  }
  if (arm === "haiku" || arm === "both") {
    haikuCases = await runHaikuArm(frozen.cases, frozen.businessContext);
  }

  const hTotals = hCases ? aggregateSendL2Arm(hCases) : null;
  const haikuTotals = haikuCases ? aggregateSendL2Arm(haikuCases) : null;

  for (const totals of [hTotals, haikuTotals]) {
    if (totals && totals.n !== EXPECTED_N) {
      console.error(
        `refusing to write results: n=${totals.n} (must be ${EXPECTED_N})`,
      );
      process.exit(1);
    }
    if (totals && totals.goldSend.n !== 56) {
      console.error(
        `refusing to write results: gold-send n=${totals.goldSend.n} (must be 56)`,
      );
      process.exit(1);
    }
  }

  const result = {
    protocol: PROTOCOL_ID,
    scope: PROTOCOL_SCOPE,
    winner: null,
    winnerNote: WINNER_HOLD_NOTE,
    model: HAIKU_MODEL_ID,
    temperature: PROTOCOL_TEMPERATURE,
    blobSha,
    datasetSha,
    gitSha: gitShaValue,
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
    hCases,
    haikuCases,
  };

  const dest =
    outPath ??
    join(
      DEFAULT_SEND_L2_RESULTS_DIR,
      `haiku-vs-h-send-l2-${result.gitSha.slice(0, 12)}.json`,
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
        datasetSha: result.datasetSha,
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
