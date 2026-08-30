import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assertFrozenBlob, loadDataset, FROZEN_PATH } from "./lib/dataset.ts";

test("frozen 215 blob SHA and case count match FROZEN.json", () => {
  const meta = assertFrozenBlob();
  const dataset = loadDataset(FROZEN_PATH);
  assert.equal(dataset.cases.length, 215);
  assert.equal(meta.blob_sha1, "b9a662da7ac33c322b96c978e7ca49eb8a62e4bd");
  assert.equal(dataset.frozen, true);
  for (const c of dataset.cases) {
    assert.ok(c.id && c.ask && c.expected_department && c.expected_behavior);
  }
});

test("no eval CLI accepts an approve/send flag", () => {
  const dir = dirname(fileURLToPath(import.meta.url));
  const files = readdirSync(dir).filter(
    (f) => f.endsWith(".ts") && !f.endsWith(".test.ts"),
  );
  for (const f of files) {
    const src = readFileSync(join(dir, f), "utf8");
    assert.equal(src.includes("--send"), false, f);
    assert.equal(src.includes("--approve"), false, f);
    assert.equal(src.includes("--yes"), false, f);
    assert.equal(src.includes("--force"), false, f);
  }
});
