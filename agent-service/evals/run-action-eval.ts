/**
 * Agent action evaluation harness — reporting runner.
 *
 * Usage:
 *   npm run eval:actions
 *   npm run eval:actions -- --report
 *   npm run eval:actions -- --gate
 *   npm run eval:actions -- --limit 20
 *   npm run eval:actions -- --dataset <path>
 *
 * Never sends mail. Never approves. Frozen labels are not modified.
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
  let routerLabel = "production (heuristic offline / haiku when keyed)";
  if (routerArg >= 0) {
    const path = args[routerArg + 1]!;
    const n = useRouterPredictions(path);
    routerLabel = `substituted from ${path} (${n} asks)`;
    console.log(`router: ${routerLabel}`);
  }

  const cases = limit ? dataset.cases.slice(0, limit) : dataset.cases;
  const startedAll = performance.now();
  const outcomes: CaseOutcome[] = [];
  for (const c of cases)
    outcomes.push(await runCase(c, dataset.business_context));
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
  const routedNull = outcomes.filter(
    (o) => o.actual_department === "none" || o.status === "needs_clarification",
  );
  const safetyViolations = outcomes.filter(
    (o) => o.unsafe_action || o.unsafe_execution || o.incomplete_audit,
  );
  const failures = outcomes.filter(
    (o) =>
      !o.department_ok ||
      !o.behavior_ok ||
      o.tool_ok === false ||
      o.approval_ok === false ||
      o.params_ok === false,
  );

  const confusion: Record<string, Record<string, number>> = {};
  for (const o of outcomes) {
    (confusion[o.expected_department] ??= {})[o.actual_department] =
      ((confusion[o.expected_department] ??= {})[o.actual_department] ?? 0) + 1;
  }

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
      routing_null_or_clarification_rate: rate(routedNull.length, n),
      safety_cases: safetyCases(dataset).length,
      estimated_cost_usd: outcomes.reduce(
        (s, o) => s + o.estimated_cost_usd,
        0,
      ),
      estimated_cost_per_1000_usd:
        n === 0
          ? 0
          : (outcomes.reduce((s, o) => s + o.estimated_cost_usd, 0) / n) * 1000,
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
    latency_ms: {
      total: totalMs,
      median: percentile(latencies, 50),
      p95: percentile(latencies, 95),
      max: latencies[latencies.length - 1] ?? 0,
    },
    department_confusion: confusion,
    failed_case_ids: failures.map((o) => o.id),
    safety_violation_case_ids: safetyViolations.map((o) => o.id),
    outcomes,
  };

  mkdirSync(RESULTS_DIR, { recursive: true });
  const stamp = new Date().toISOString().slice(0, 10);
  const outPath = join(
    RESULTS_DIR,
    `action-eval-${dataset.dataset_version}-${stamp}.json`,
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
  console.log(`  param exact match:      ${pct(m.param_exact_match)}`);
  console.log(`  missed-action rate:     ${pct(m.missed_action_rate)}`);
  console.log(
    `  routing null/clarify:   ${pct(m.routing_null_or_clarification_rate)}`,
  );
  console.log(`  UNSAFE ACTIONS:         ${m.unsafe_action_count}`);
  console.log(
    `  latency:                median ${result.latency_ms.median}ms, p95 ${result.latency_ms.p95}ms, total ${totalMs}ms`,
  );
  console.log(`  cost:                   $${m.estimated_cost_usd} (offline=0)`);
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
}

await main();
