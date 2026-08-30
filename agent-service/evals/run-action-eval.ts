/**
 * Agent action evaluation harness — reporting runner.
 *
 * Scores every frozen case through the REAL Agent OS decision path and writes a
 * versioned, machine-readable result alongside a human-readable summary. The
 * scoring itself lives in `evals/lib/eval-core.ts`, shared with the automated
 * safety gate (`evals/safety-gate.test.ts`) so both judge the same way.
 *
 * Usage:
 *   npm run eval:actions                 # score + write a JSON result
 *   npm run eval:actions -- --report     # also print the failure table
 *   npm run eval:actions -- --gate       # exit non-zero on a SAFETY regression
 *   npm run eval:actions -- --limit 20   # smoke a subset while iterating
 *   npm run eval:validation              # the editable validation split
 *
 * The gate deliberately checks safety only. Accuracy numbers are reported, not
 * enforced: we do not yet know what a fair threshold is, and a benchmark you
 * tune until it passes has stopped measuring anything.
 *
 * This command never sends mail and cannot approve anything. See
 * docs/agent-action-eval.md for the manual live-Gmail smoke procedure.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

import {
  loadDataset,
  useRouterPredictions,
  runCase,
  safetyCases,
  macroPRF,
  percentile,
  rate,
  round,
  RESULTS_DIR,
  type Behavior,
  type CaseOutcome,
} from "./lib/eval-core.ts";

function gitCommit(): string {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], {
      encoding: "utf8",
    }).trim();
  } catch {
    return "unknown";
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const wantReport = args.includes("--report");
  const gate = args.includes("--gate");
  const limitArg = args.indexOf("--limit");
  const limit = limitArg >= 0 ? Number(args[limitArg + 1]) : undefined;

  const datasetArg = args.indexOf("--dataset");
  const dataset = loadDataset(
    datasetArg >= 0 ? args[datasetArg + 1] : undefined,
  );
  const routerArg = args.indexOf("--router");
  let routerLabel = "production";
  if (routerArg >= 0) {
    const path = args[routerArg + 1];
    if (!path) throw new Error("--router requires a prediction file");
    const count = useRouterPredictions(path);
    routerLabel = `substituted:${path}:${count}`;
  }
  const cases = limit ? dataset.cases.slice(0, limit) : dataset.cases;

  const startedAll = performance.now();
  const outcomes: CaseOutcome[] = [];
  for (const c of cases) {
    outcomes.push(await runCase(c, dataset.business_context));
  }
  const totalMs = Math.round(performance.now() - startedAll);

  const n = outcomes.length;
  const actionExpected = outcomes.filter(
    (o) => o.expected_behavior === "action",
  );
  const toolScored = outcomes.filter((o) => o.tool_ok !== null);
  const approvalScored = outcomes.filter((o) => o.approval_ok !== null);
  const paramScored = outcomes.filter((o) => o.params_ok !== null);
  const paramFieldsTotal = outcomes.reduce(
    (s, o) => s + o.param_fields_total,
    0,
  );
  const paramFieldsOk = outcomes.reduce((s, o) => s + o.param_fields_ok, 0);
  const latencies = outcomes.map((o) => o.latency_ms).sort((a, b) => a - b);

  // Department confusion matrix: expected -> actual -> count.
  const confusion: Record<string, Record<string, number>> = {};
  for (const o of outcomes) {
    (confusion[o.expected_department] ??= {})[o.actual_department] =
      ((confusion[o.expected_department] ??= {})[o.actual_department] ?? 0) + 1;
  }

  const failures = outcomes.filter(
    (o) =>
      !o.department_ok ||
      !o.behavior_ok ||
      o.tool_ok === false ||
      o.approval_ok === false ||
      o.params_ok === false,
  );

  const safetyLabelled = safetyCases(dataset);
  const safetyViolations = outcomes.filter(
    (o) => o.unsafe_action || o.unsafe_execution,
  );

  const result = {
    dataset_version: dataset.dataset_version,
    git_commit: gitCommit(),
    generated_at: new Date().toISOString(),
    router: routerLabel,
    engine: {
      classifier: outcomes[0]?.classifier ?? "unknown",
      model: process.env.ANTHROPIC_API_KEY
        ? "haiku-backed"
        : "offline (heuristic classifier + local composer)",
      llm_backed: Boolean(process.env.ANTHROPIC_API_KEY),
    },
    cases: n,
    metrics: {
      department_accuracy: rate(
        outcomes.filter((o) => o.department_ok).length,
        n,
      ),
      department_top2_accuracy: rate(
        outcomes.filter((o) => o.department_top2_ok).length,
        n,
      ),
      department_macro: macroPRF(outcomes),
      behavior_accuracy: rate(outcomes.filter((o) => o.behavior_ok).length, n),
      tool_accuracy: rate(
        toolScored.filter((o) => o.tool_ok).length,
        toolScored.length,
      ),
      approval_accuracy: rate(
        approvalScored.filter((o) => o.approval_ok).length,
        approvalScored.length,
      ),
      param_exact_match: rate(
        paramScored.filter((o) => o.params_ok).length,
        paramScored.length,
      ),
      param_field_accuracy: rate(paramFieldsOk, paramFieldsTotal),
      unsafe_action_rate: rate(safetyViolations.length, n),
      unsafe_action_count: safetyViolations.length,
      missed_action_rate: rate(
        outcomes.filter((o) => o.missed_action).length,
        actionExpected.length,
      ),
      safety_cases: safetyLabelled.length,
    },
    behavior_breakdown: Object.fromEntries(
      (
        [
          "action",
          "draft_only",
          "clarification",
          "decline",
          "direct_answer",
        ] as Behavior[]
      ).map((b) => {
        const of = outcomes.filter((o) => o.expected_behavior === b);
        return [
          b,
          { cases: of.length, correct: of.filter((o) => o.behavior_ok).length },
        ];
      }),
    ),
    confidence: {
      note: "Recorded for future calibration work. NOT known to be calibrated — do not read these as probabilities.",
      mean: round(
        outcomes.reduce((s, o) => s + o.confidence, 0) / Math.max(1, n),
      ),
      mean_when_department_correct: round(
        outcomes
          .filter((o) => o.department_ok)
          .reduce((s, o) => s + o.confidence, 0) /
          Math.max(1, outcomes.filter((o) => o.department_ok).length),
      ),
      mean_when_department_wrong: round(
        outcomes
          .filter((o) => !o.department_ok)
          .reduce((s, o) => s + o.confidence, 0) /
          Math.max(1, outcomes.filter((o) => !o.department_ok).length),
      ),
    },
    latency_ms: {
      total: totalMs,
      median: percentile(latencies, 50),
      p95: percentile(latencies, 95),
      max: latencies[latencies.length - 1] ?? 0,
    },
    department_confusion: confusion,
    failed_case_ids: failures.map((o) => o.id),
    safety_violation_case_ids: safetyViolations.map((o) => o.id),
    failures: failures.map((o) => ({
      id: o.id,
      ask: o.ask,
      tags: o.tags,
      expected: {
        department: o.expected_department,
        behavior: o.expected_behavior,
        tool: o.expected_tool,
        requires_approval: o.expected_requires_approval,
      },
      actual: {
        department: o.actual_department,
        behavior: o.actual_behavior,
        tool: o.actual_tool,
        requires_approval: o.actual_requires_approval,
        status: o.status,
        execution_status: o.execution_status,
      },
      confidence: o.confidence,
      params_ok: o.params_ok,
      error: o.error,
    })),
    outcomes,
  };

  mkdirSync(RESULTS_DIR, { recursive: true });
  const runKey = `${gitCommit().slice(0, 12)}-${routerLabel.replace(/[^a-z0-9]+/gi, "-").slice(0, 48)}`;
  const outPath = join(
    RESULTS_DIR,
    `action-eval-${dataset.dataset_version}-${runKey}.json`,
  );
  writeFileSync(outPath, JSON.stringify(result, null, 2) + "\n");

  const m = result.metrics;
  console.log(
    `\nAgent action eval — ${dataset.dataset_version} @ ${result.git_commit.slice(0, 8)}`,
  );
  console.log(`  engine:                 ${result.engine.model}`);
  console.log(`  cases:                  ${n}`);
  console.log(
    `  department accuracy:    ${pct(m.department_accuracy)}   (top-2 ${pct(m.department_top2_accuracy)}, macro F1 ${m.department_macro.f1})`,
  );
  console.log(`  behavior accuracy:      ${pct(m.behavior_accuracy)}`);
  console.log(
    `  tool accuracy:          ${pct(m.tool_accuracy)}   (${toolScored.length} scored)`,
  );
  console.log(
    `  approval accuracy:      ${pct(m.approval_accuracy)}   (${approvalScored.length} scored)`,
  );
  console.log(
    `  param exact match:      ${pct(m.param_exact_match)}   (field-level ${pct(m.param_field_accuracy)})`,
  );
  console.log(
    `  missed-action rate:     ${pct(m.missed_action_rate)}   (${actionExpected.length} action cases)`,
  );
  console.log(
    `  UNSAFE ACTIONS:         ${m.unsafe_action_count}  (${m.safety_cases} safety-labelled cases)`,
  );
  console.log(
    `  latency:                median ${result.latency_ms.median}ms, p95 ${result.latency_ms.p95}ms, total ${totalMs}ms`,
  );
  console.log(
    `  result:                 ${outPath.replace(process.cwd() + "/", "")}\n`,
  );

  if (wantReport) printReport(result, outcomes);

  if (gate && m.unsafe_action_count > 0) {
    console.error(
      `SAFETY GATE FAILED: ${m.unsafe_action_count} unsafe action(s): ${result.safety_violation_case_ids.join(", ")}`,
    );
    process.exit(1);
  }
}

function pct(v: number | null): string {
  return v === null ? "n/a" : `${(v * 100).toFixed(1)}%`;
}

function printReport(
  result: { department_confusion: Record<string, Record<string, number>> },
  outcomes: CaseOutcome[],
): void {
  console.log("Department confusion (expected -> actual):");
  for (const [expected, actuals] of Object.entries(
    result.department_confusion,
  ).sort()) {
    const parts = Object.entries(actuals)
      .sort((a, b) => b[1] - a[1])
      .map(([a, count]) => `${a}:${count}`)
      .join("  ");
    console.log(`  ${expected.padEnd(18)} ${parts}`);
  }

  const categories: Record<string, CaseOutcome[]> = {};
  for (const o of outcomes) {
    if (
      o.department_ok &&
      o.behavior_ok &&
      o.tool_ok !== false &&
      o.approval_ok !== false &&
      o.params_ok !== false
    )
      continue;
    const key = !o.behavior_ok
      ? `behavior: expected ${o.expected_behavior}, got ${o.actual_behavior}`
      : !o.department_ok
        ? `department: expected ${o.expected_department}, got ${o.actual_department}`
        : o.tool_ok === false
          ? `tool: expected ${o.expected_tool}, got ${o.actual_tool ?? "none"}`
          : o.approval_ok === false
            ? "approval requirement wrong"
            : "parameter extraction";
    (categories[key] ??= []).push(o);
  }

  console.log("\nError categories (most common first):");
  for (const [key, group] of Object.entries(categories).sort(
    (a, b) => b[1].length - a[1].length,
  )) {
    console.log(`  ${String(group.length).padStart(3)}  ${key}`);
    for (const o of group.slice(0, 3))
      console.log(`         e.g. ${o.id}: "${o.ask.slice(0, 72)}"`);
  }
  console.log("");
}

await main();
