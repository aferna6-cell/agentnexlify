import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

import { DATASET_PATH, loadDataset } from "./lib/eval-core.ts";

const FROZEN_ACTION_EVAL_SHA256 =
  "0997c4de4a82afba3bcf3befa25c2c7b3fc898c14da1960d8bbe9856b849d6b0";

test("the frozen 215-case benchmark has not changed", () => {
  const bytes = readFileSync(DATASET_PATH);
  const digest = createHash("sha256").update(bytes).digest("hex");
  const dataset = loadDataset();

  assert.equal(digest, FROZEN_ACTION_EVAL_SHA256);
  assert.equal(dataset.frozen, true);
  assert.equal(dataset.cases.length, 215);
});
