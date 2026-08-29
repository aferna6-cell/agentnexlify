/**
 * Protocol tests for the Haiku-vs-H measurement runner.
 *
 * These tests never call the Anthropic API. They do not import classify(),
 * classifyHeuristic, or eval-core.
 */

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  EXPECTED_CLASSIFIER_BLOB_SHA,
  EXPECTED_N,
  HAIKU_MODEL_ID,
  PROTOCOL_TEMPERATURE,
  DEFAULT_CLASSIFIER_PATH,
  DEFAULT_DATASET_PATH,
  aggregateScores,
  assertClassifierBlobSha,
  gitBlobSha,
  hasAnthropicApiKey,
  loadFrozenCases,
  scorePrediction,
  type CaseScore,
} from "./lib/haiku-vs-h-protocol.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const RUNNER = join(HERE, "run-haiku-vs-h.ts");
const CLASSIFIER = DEFAULT_CLASSIFIER_PATH;

function runnerSource(): string {
  return readFileSync(RUNNER, "utf8");
}

function protocolSource(): string {
  return readFileSync(join(HERE, "lib", "haiku-vs-h-protocol.ts"), "utf8");
}

function spawnRunner(args: string[], extraEnv: NodeJS.ProcessEnv = {}) {
  const env = { ...process.env, ...extraEnv };
  delete env.ANTHROPIC_API_KEY;
  return spawnSync(
    process.execPath,
    ["--experimental-strip-types", RUNNER, ...args],
    {
      cwd: join(HERE, ".."),
      encoding: "utf8",
      env,
    },
  );
}

test("frozen classifier blob SHA matches the signed freeze", () => {
  const sha = gitBlobSha(CLASSIFIER);
  assert.equal(sha, EXPECTED_CLASSIFIER_BLOB_SHA);
  assert.equal(
    assertClassifierBlobSha(CLASSIFIER),
    EXPECTED_CLASSIFIER_BLOB_SHA,
  );
});

test("MIN_BUSINESS_EVIDENCE is ABSENT on the frozen classifier", () => {
  const src = readFileSync(CLASSIFIER, "utf8");
  assert.equal(src.includes("MIN_BUSINESS_EVIDENCE"), false);
});

test("production classify() is the Haiku-then-heuristic fallback and is not imported here", () => {
  const src = readFileSync(CLASSIFIER, "utf8");
  assert.match(src, /export async function classify\(/);
  assert.match(src, /const viaHaiku = await classifyWithHaiku\(ask, runId\);/);
  assert.match(src, /return classifyHeuristic\(ask\);/);
  assert.equal(runnerSource().includes('from "./lib/eval-core'), false);
  assert.equal(runnerSource().includes("eval-core"), false);
  assert.equal(protocolSource().includes("eval-core"), false);
  assert.equal(runnerSource().includes("classifyHeuristic"), false);
  assert.equal(protocolSource().includes("classifyHeuristic"), false);
  // Runner may call classifyWithHaiku only — not classify(.
  assert.match(runnerSource(), /classifyWithHaiku/);
  assert.equal(
    /\bclassify\s*\(/.test(runnerSource().replaceAll("classifyWithHaiku", "")),
    false,
  );
});

test("frozen action-eval-v1 has exactly 215 labelled cases", () => {
  const cases = loadFrozenCases(DEFAULT_DATASET_PATH);
  assert.equal(cases.length, EXPECTED_N);
  assert.equal(cases.length, 215);
});

test("loadFrozenCases fails closed when n is not 215", () => {
  const dir = mkdtempSync(join(tmpdir(), "haiku-vs-h-"));
  const path = join(dir, "short.json");
  writeFileSync(
    path,
    JSON.stringify({
      cases: [{ id: "x", ask: "hi", expected_department: "sales" }],
    }),
  );
  assert.throws(() => loadFrozenCases(path), /n=215/);
});

test("scorePrediction: top id must equal expected; null/empty is incorrect", () => {
  assert.deepEqual(scorePrediction("sales", "sales"), {
    predicted: "sales",
    isNull: false,
    correct: true,
  });
  assert.deepEqual(scorePrediction("operations", "sales"), {
    predicted: "operations",
    isNull: false,
    correct: false,
  });
  assert.deepEqual(scorePrediction(null, "sales"), {
    predicted: null,
    isNull: true,
    correct: false,
  });
  assert.deepEqual(scorePrediction("", "none"), {
    predicted: null,
    isNull: true,
    correct: false,
  });
  assert.deepEqual(scorePrediction("   ", "none"), {
    predicted: null,
    isNull: true,
    correct: false,
  });
  assert.deepEqual(scorePrediction(undefined, "sales"), {
    predicted: null,
    isNull: true,
    correct: false,
  });
});

test("aggregate never drops cases; n is the scored list length", () => {
  const cases: CaseScore[] = Array.from({ length: EXPECTED_N }, (_, i) => ({
    id: `c${i}`,
    predicted: i === 0 ? "sales" : null,
    expected: "sales",
    null: i !== 0,
    cost: 0,
    correct: i === 0,
    error: i === 2,
  }));
  const totals = aggregateScores(cases);
  assert.equal(totals.n, 215);
  assert.equal(totals.correct, 1);
  assert.equal(totals.nulls, 214);
  assert.equal(totals.errors, 1);
  assert.equal(totals.acc, 1 / 215);
});

test("hasAnthropicApiKey is fail-closed on missing or blank keys", () => {
  assert.equal(hasAnthropicApiKey({}), false);
  assert.equal(hasAnthropicApiKey({ ANTHROPIC_API_KEY: "" }), false);
  assert.equal(hasAnthropicApiKey({ ANTHROPIC_API_KEY: "   " }), false);
  assert.equal(hasAnthropicApiKey({ ANTHROPIC_API_KEY: "sk-test" }), true);
});

test("missing API key exits 2 with a clear message and no accuracy numbers", () => {
  const result = spawnRunner([]);
  assert.equal(result.status, 2, result.stderr + result.stdout);
  assert.match(result.stderr, /ANTHROPIC_API_KEY/);
  assert.match(result.stderr, /heuristic/i);
  assert.equal(/\bacc\s*[:=]\s*\d/.test(result.stdout + result.stderr), false);
  assert.equal(
    (result.stdout + result.stderr).includes("department accuracy"),
    false,
  );
});

test("--require-key with no key is fail-closed (exit 2)", () => {
  const result = spawnRunner(["--require-key"]);
  assert.equal(result.status, 2, result.stderr + result.stdout);
  assert.match(result.stderr, /ANTHROPIC_API_KEY/);
});

test("blob SHA mismatch exits non-zero and prints the actual SHA", () => {
  const dir = mkdtempSync(join(tmpdir(), "haiku-vs-h-"));
  const fake = join(dir, "_classifier.ts");
  writeFileSync(fake, "export const notTheFrozenClassifier = true;\n");
  const actual = gitBlobSha(fake);
  assert.notEqual(actual, EXPECTED_CLASSIFIER_BLOB_SHA);
  const result = spawnRunner([], { HAIKU_VS_H_CLASSIFIER_PATH: fake });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, new RegExp(actual));
  assert.match(result.stderr, /blob SHA mismatch/);
});

test("protocol constants match the signed measurement", () => {
  assert.equal(EXPECTED_N, 215);
  assert.equal(HAIKU_MODEL_ID, "claude-haiku-4-5-20251001");
  assert.equal(PROTOCOL_TEMPERATURE, 0);
  assert.equal(
    EXPECTED_CLASSIFIER_BLOB_SHA,
    "3a5251f6ee4c5b93839c5f87f721725610e9a8e2",
  );
});
