/**
 * Signed Haiku-vs-H measurement protocol (routing-only).
 *
 * This module is scoring + freeze checks. It does not import the production
 * classifier, eval-core (which deletes ANTHROPIC_API_KEY), or the action
 * executor. The CLI runner calls classifyWithHaiku itself.
 */

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const EXPECTED_N = 215;
export const EXPECTED_CLASSIFIER_BLOB_SHA =
  "3a5251f6ee4c5b93839c5f87f721725610e9a8e2";
export const HAIKU_MODEL_ID = "claude-haiku-4-5-20251001";
/** Protocol temperature. classifyWithHaiku/complete() on the frozen blob do not pass temperature. */
export const PROTOCOL_TEMPERATURE = 0;
export const DATASET_VERSION = "action-eval-v1";

const HERE = dirname(fileURLToPath(import.meta.url));
export const DEFAULT_DATASET_PATH = join(
  HERE,
  "..",
  "datasets",
  "action-eval-v1.json",
);
export const DEFAULT_CLASSIFIER_PATH = join(
  HERE,
  "..",
  "..",
  "src",
  "agent-os",
  "agents",
  "_classifier.ts",
);
export const DEFAULT_RESULTS_DIR = join(HERE, "..", "results");

export interface FrozenEvalCase {
  id: string;
  ask: string;
  expected_department: string;
}

export interface DatasetFile {
  dataset_version?: string;
  frozen?: boolean;
  cases: FrozenEvalCase[];
}

export interface CaseScore {
  id: string;
  predicted: string | null;
  expected: string;
  null: boolean;
  cost: number;
  correct: boolean;
  error: boolean;
}

export interface RunTotals {
  n: number;
  correct: number;
  acc: number;
  nulls: number;
  errors: number;
  costUsd: number;
}

export interface HaikuVsHResult extends RunTotals {
  protocol: "haiku-vs-h-v1";
  scope: "routing-only";
  unsafe: null;
  unsafeNote: string;
  model: string;
  temperature: number;
  blobSha: string;
  gitSha: string;
  dataset: string;
  fallback: false;
  winner: null;
  cases: CaseScore[];
}

export function gitBlobSha(filePath: string): string {
  const content = readFileSync(filePath);
  const header = Buffer.from(`blob ${content.length}\0`);
  return createHash("sha1")
    .update(Buffer.concat([header, content]))
    .digest("hex");
}

export function assertClassifierBlobSha(filePath: string): string {
  const actual = gitBlobSha(filePath);
  if (actual !== EXPECTED_CLASSIFIER_BLOB_SHA) {
    throw new ClassifierBlobMismatchError(actual);
  }
  return actual;
}

export class ClassifierBlobMismatchError extends Error {
  readonly actualSha: string;
  constructor(actualSha: string) {
    super(
      `classifier blob SHA mismatch: expected ${EXPECTED_CLASSIFIER_BLOB_SHA}, got ${actualSha}. Refusing to continue.`,
    );
    this.name = "ClassifierBlobMismatchError";
    this.actualSha = actualSha;
  }
}

export function loadFrozenCases(datasetPath: string): FrozenEvalCase[] {
  const data = JSON.parse(readFileSync(datasetPath, "utf8")) as DatasetFile;
  const cases = data.cases ?? [];
  if (cases.length !== EXPECTED_N) {
    throw new Error(
      `frozen dataset must have n=${EXPECTED_N} cases, got ${cases.length}. Refusing to continue.`,
    );
  }
  for (const c of cases) {
    if (
      !c.id ||
      typeof c.ask !== "string" ||
      typeof c.expected_department !== "string"
    ) {
      throw new Error(`malformed frozen case: ${JSON.stringify({ id: c.id })}`);
    }
  }
  return cases;
}

/** Predicted department is the top candidate agentId. Null/empty is incorrect. Never drop. */
export function scorePrediction(
  predicted: string | null | undefined,
  expected: string,
): { predicted: string | null; isNull: boolean; correct: boolean } {
  const trimmed = typeof predicted === "string" ? predicted.trim() : "";
  const isNull = predicted == null || trimmed.length === 0;
  const value = isNull ? null : trimmed;
  return { predicted: value, isNull, correct: !isNull && value === expected };
}

export function aggregateScores(cases: CaseScore[]): RunTotals {
  const n = cases.length;
  const correct = cases.filter((c) => c.correct).length;
  const nulls = cases.filter((c) => c.null).length;
  const errors = cases.filter((c) => c.error).length;
  const costUsd = cases.reduce((s, c) => s + c.cost, 0);
  return {
    n,
    correct,
    acc: n === 0 ? 0 : correct / n,
    nulls,
    errors,
    costUsd,
  };
}

export function hasAnthropicApiKey(
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  const key = env.ANTHROPIC_API_KEY;
  return typeof key === "string" && key.trim().length > 0;
}

export function gitSha(cwd: string = join(HERE, "..", "..", "..")): string {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], {
      cwd,
      encoding: "utf8",
    }).trim();
  } catch {
    return "unknown";
  }
}

export const UNSAFE_NOTE =
  "N/A — routing-only runner. Tools, send_email, and the action executor are not invoked. Unsafe/e2e is out of scope (e2e would use the heuristic executor).";
