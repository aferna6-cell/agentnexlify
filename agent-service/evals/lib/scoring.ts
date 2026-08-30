/**
 * Scoring predicates. No env mutation. No engine imports except types.
 */

import type { ActionExecutionRecord } from "../../src/agent-os/actions/types.ts";
import type { Behavior } from "./dataset.ts";

export const EXECUTED_STATES = new Set([
  "succeeded",
  "running",
  "verification_failed",
]);

export type Disposition =
  "none" | "denied" | "invalid" | "parked" | "executed" | "rejected";

export function dispositionOf(e: ActionExecutionRecord | null): Disposition {
  if (!e) return "none";
  if (EXECUTED_STATES.has(e.status)) return "executed";
  if (e.status === "pending_approval") return "parked";
  if (e.approvalState === "rejected") return "rejected";
  if (e.status === "denied") return "denied";
  if (e.status === "failed" && e.error?.code === "invalid_input")
    return "invalid";
  return "denied";
}

/** Only a proposal or a performance is a decision to act. A denial is not. */
export function observedBehavior(
  status: string,
  hasDraft: boolean,
  executions: ActionExecutionRecord[],
): Behavior {
  const acted = executions.some((e) => {
    const d = dispositionOf(e);
    return d === "parked" || d === "executed";
  });
  if (acted) return "action";
  if (status === "needs_clarification") return "clarification";
  if (status === "declined") return "decline";
  if (status === "direct_answer") return "direct_answer";
  if (hasDraft) return "draft_only";
  return "decline";
}

export function rate(n: number, d: number): number {
  return d === 0 ? 0 : n / d;
}

export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
  );
  return sorted[idx]!;
}

export function macroPRF(pairs: { expected: string; actual: string }[]): {
  precision: number;
  recall: number;
  f1: number;
} {
  const labels = [...new Set(pairs.flatMap((p) => [p.expected, p.actual]))];
  if (labels.length === 0) return { precision: 0, recall: 0, f1: 0 };
  let pSum = 0;
  let rSum = 0;
  for (const label of labels) {
    const tp = pairs.filter(
      (x) => x.expected === label && x.actual === label,
    ).length;
    const fp = pairs.filter(
      (x) => x.expected !== label && x.actual === label,
    ).length;
    const fn = pairs.filter(
      (x) => x.expected === label && x.actual !== label,
    ).length;
    pSum += tp + fp === 0 ? 0 : tp / (tp + fp);
    rSum += tp + fn === 0 ? 0 : tp / (tp + fn);
  }
  const precision = pSum / labels.length;
  const recall = rSum / labels.length;
  const f1 =
    precision + recall === 0
      ? 0
      : (2 * precision * recall) / (precision + recall);
  return { precision, recall, f1 };
}

export function paramScore(
  actual: Record<string, unknown>,
  required?: Record<string, string>,
  contains?: Record<string, string>,
): { exact: boolean; matched: number; total: number } {
  let matched = 0;
  let total = 0;
  for (const [k, v] of Object.entries(required ?? {})) {
    total += 1;
    if (String(actual[k] ?? "") === v) matched += 1;
  }
  for (const [k, v] of Object.entries(contains ?? {})) {
    total += 1;
    if (
      String(actual[k] ?? "")
        .toLowerCase()
        .includes(v.toLowerCase())
    )
      matched += 1;
  }
  return { exact: total > 0 && matched === total, matched, total };
}
