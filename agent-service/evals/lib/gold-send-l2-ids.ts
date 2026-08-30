/**
 * Frozen gold send/L2 case ids for action-eval-v1.
 *
 * Source of truth: ../gold-send-l2-ids.json (committed, not a comment).
 * Must equal every frozen case with expected_tool===send_email,
 * expected_risk_level===2, and expected_requires_approval===true.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const GOLD_SEND_L2_PATH = join(HERE, "..", "gold-send-l2-ids.json");
export const EXPECTED_GOLD_SEND_N = 56;

interface GoldSendL2File {
  id?: string;
  n: number;
  ids: string[];
}

const loaded = JSON.parse(
  readFileSync(GOLD_SEND_L2_PATH, "utf8"),
) as GoldSendL2File;
if (!Array.isArray(loaded.ids) || loaded.n !== EXPECTED_GOLD_SEND_N) {
  throw new Error(
    `gold-send-l2-ids.json must declare n=${EXPECTED_GOLD_SEND_N} and an ids array`,
  );
}

export const GOLD_SEND_L2_IDS: readonly string[] = Object.freeze([
  ...loaded.ids,
]);
export const GOLD_SEND_L2_SET: ReadonlySet<string> = new Set(GOLD_SEND_L2_IDS);

export function isGoldSendL2Label(c: {
  expected_tool?: unknown;
  expected_risk_level?: unknown;
  expected_requires_approval?: unknown;
}): boolean {
  return (
    c.expected_tool === "send_email" &&
    c.expected_risk_level === 2 &&
    c.expected_requires_approval === true
  );
}

export function assertGoldSendL2Freeze(): readonly string[] {
  if (GOLD_SEND_L2_IDS.length !== EXPECTED_GOLD_SEND_N) {
    throw new Error(
      `gold send/L2 freeze must have n=${EXPECTED_GOLD_SEND_N}, got ${GOLD_SEND_L2_IDS.length}`,
    );
  }
  const sorted = [...GOLD_SEND_L2_IDS].sort((a, b) => a.localeCompare(b));
  if (sorted.join("\n") !== GOLD_SEND_L2_IDS.join("\n")) {
    throw new Error("gold send/L2 ids must be sorted");
  }
  return GOLD_SEND_L2_IDS;
}
