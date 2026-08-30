import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, statSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { DATASET_PATH, loadDataset } from "./lib/eval-core.ts";

const here = dirname(fileURLToPath(import.meta.url));
const META = join(here, "datasets", "FROZEN.json");

test("frozen 215 blob SHA and case count match FROZEN.json", () => {
  const meta = JSON.parse(readFileSync(META, "utf8"))["action-eval-v1.json"];
  const actual = execFileSync("git", ["hash-object", DATASET_PATH], {
    encoding: "utf8",
  }).trim();
  const bytes = statSync(DATASET_PATH).size;
  const dataset = loadDataset();
  assert.equal(dataset.cases.length, 215);
  assert.equal(dataset.frozen, true);
  assert.equal(actual, meta.blob_sha1);
  assert.equal(bytes, meta.bytes);
});

test("no eval CLI parses an approve flag", () => {
  const files = readdirSync(here).filter(
    (f) => f.endsWith(".ts") && !f.endsWith(".test.ts"),
  );
  for (const f of files) {
    const src = readFileSync(join(here, f), "utf8");
    assert.equal(src.includes('args.includes("--approve")'), false, f);
    assert.equal(src.includes('args.includes("--send")'), false, f);
  }
});
