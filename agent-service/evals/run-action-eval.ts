/**
 * Production action-evaluation runner.
 *
 * Measures the real decision path:
 *   request → classifier → department → intent → action resolution
 *   → tool proposal → policy → approval behavior → execution state
 *
 * Offline by default (goOffline). No real Gmail. SEND_EMAIL_ENABLED is never
 * set. Frozen 215 labels are not modified.
 *
 * Usage:
 *   npm run eval:actions
 *   npm run eval:actions -- --dataset evals/datasets/validation/validation-v3.json --routing-only
 *   npm run eval:actions:gate
 */

import { goOffline } from "./lib/offline.ts";
goOffline();

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  assertFrozenBlob,
  isActionDataset,
  loadDataset,
  FROZEN_PATH,
  type Dataset,
  type EvalCase,
} from "./lib/dataset.ts";
import {
  dispositionOf,
  macroPRF,
  observedBehavior,
  paramScore,
  percentile,
  rate,
} from "./lib/scoring.ts";
import { safetyVerdict } from "./lib/safety.ts";

const here = dirname(fileURLToPath(import.meta.url));

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function hasFlag(name: string): boolean {
  return process.argv.includes(name);
}

async function main(): Promise<void> {
  if (process.env.SEND_EMAIL_ENABLED) {
    console.error(
      "SEND_EMAIL_ENABLED is set — this eval runner never enables live send",
    );
    process.exit(2);
  }

  const datasetPath = resolve(arg("--dataset", FROZEN_PATH)!);
  const routingOnly = hasFlag("--routing-only");
  const gate = hasFlag("--gate");
  const report = hasFlag("--report");

  if (datasetPath.endsWith("action-eval-v1.json")) assertFrozenBlob();

  const dataset = loadDataset(datasetPath);
  if (
    dataset.not_for_model_selection &&
    report &&
    !hasFlag("--acknowledge-not-for-selection")
  ) {
    console.error(
      "This split is marked not_for_model_selection. Pass --acknowledge-not-for-selection to report.",
    );
    process.exit(2);
  }

  if (!routingOnly && !isActionDataset(dataset)) {
    console.error(
      "Dataset has no SharedContext business_context. Use --routing-only.",
    );
    process.exit(2);
  }

  const { runOrchestration } =
    await import("../src/agent-os-runtime/orchestrate.ts");
  const { classifyHeuristic } =
    await import("../src/agent-os/agents/_classifier.ts");

  const accountId = "eval-tenant";
  const outcomes = [];
  const latencies: number[] = [];
  let modelCost = 0;
  let modelCalls = 0;

  for (const c of dataset.cases) {
    const t0 = Date.now();
    let status = "declined";
    let department = "none";
    let alternates: string[] = [];
    let hasDraft = false;
    let params: Record<string, unknown> = {};
    let executions: import("../src/agent-os/actions/types.ts").ActionExecutionRecord[] =
      [];
    let noEvidence = false;
    let classifier = "heuristic";

    if (routingOnly) {
      const cls = classifyHeuristic(c.ask);
      classifier = cls.classifier;
      noEvidence = cls.candidates.length === 0;
      department = cls.candidates[0]?.agentId ?? "none";
      alternates = cls.candidates.slice(1, 2).map((x) => x.agentId);
      params = cls.params;
      status = noEvidence ? "wishlist_fallback" : "routed";
    } else {
      const context = (
        dataset as Dataset & {
          business_context: import("../src/agent-os/types/agent.ts").SharedContext;
        }
      ).business_context;
      const out = await runOrchestration({ accountId, ask: c.ask, context });
      status = out.result.status;
      department = out.result.agentId ?? "none";
      alternates = (out.result.alternates ?? [])
        .slice(0, 1)
        .map((a) => a.agentId);
      hasDraft = Boolean(out.result.draft);
      params = out.result.params ?? {};
      executions = out.record.toolExecutions ?? [];
      classifier = out.result.classifier;
      noEvidence = classifyHeuristic(c.ask).candidates.length === 0;
      for (const call of out.record.modelCalls ?? []) {
        modelCalls += 1;
        modelCost += call.costUsd ?? 0;
      }
    }

    const latency = Date.now() - t0;
    latencies.push(latency);

    const okDepts = new Set([
      c.expected_department,
      ...(c.acceptable_departments ?? []),
    ]);
    const okBehaviors = new Set([
      c.expected_behavior,
      ...(c.acceptable_behaviors ?? []),
    ]);
    const behavior = observedBehavior(status, hasDraft, executions);
    const acted = executions.find((e) => {
      const d = dispositionOf(e);
      return d === "parked" || d === "executed";
    });
    const actualTool =
      acted?.toolId ??
      (c.expected_tool === null && executions.length === 0
        ? null
        : (acted?.toolId ?? null));
    const verdict = safetyVerdict(executions, {
      mustNotExecute: Boolean(c.must_not_execute),
      mustNotExecuteWithoutApproval: Boolean(
        c.must_not_execute_without_approval,
      ),
      actionAllowed: okBehaviors.has("action"),
      expectedAccountId: accountId,
    });
    const paramsHit = paramScore(
      acted?.input ?? params,
      c.required_params,
      c.required_params_contains,
    );

    outcomes.push({
      id: c.id,
      ask: c.ask,
      expected_department: c.expected_department,
      actual_department: department,
      department_ok: okDepts.has(department),
      top2_ok: okDepts.has(department) || okDepts.has(alternates[0] ?? ""),
      expected_behavior: c.expected_behavior,
      actual_behavior: behavior,
      behavior_ok: okBehaviors.has(behavior),
      expected_tool: c.expected_tool,
      actual_tool: actualTool,
      tool_ok:
        c.expected_tool === null
          ? actualTool === null
          : actualTool === c.expected_tool,
      approval_ok:
        acted && c.expected_requires_approval !== undefined
          ? acted.requiresApproval === c.expected_requires_approval
          : null,
      param_exact: paramsHit.total === 0 ? null : paramsHit.exact,
      missed_action:
        c.expected_behavior === "action" && !okBehaviors.has(behavior),
      status,
      classifier,
      no_evidence: noEvidence,
      clarification: status === "needs_clarification",
      policy_blocked: executions.some((e) => dispositionOf(e) === "denied"),
      latency_ms: latency,
      findings: verdict.findings,
      unsafeAction: verdict.unsafeAction,
      unsafeExecution: verdict.unsafeExecution,
    });
  }

  const n = outcomes.length;
  const toolScored = outcomes.filter((o) => o.expected_tool !== null);
  const approvalScored = outcomes.filter((o) => o.approval_ok !== null);
  const paramScored = outcomes.filter((o) => o.param_exact !== null);
  const actionExpected = outcomes.filter(
    (o) => o.expected_behavior === "action",
  );
  const unsafeAction = outcomes.filter((o) => o.unsafeAction);
  const unsafeExecution = outcomes.filter((o) => o.unsafeExecution);
  const deptPairs = outcomes.map((o) => ({
    expected: o.expected_department,
    actual: o.actual_department,
  }));

  const metrics = {
    n,
    dataset: dataset.dataset_version,
    frozen: dataset.frozen,
    routing_only: routingOnly,
    department_accuracy: rate(
      outcomes.filter((o) => o.department_ok).length,
      n,
    ),
    department_top2_accuracy: rate(outcomes.filter((o) => o.top2_ok).length, n),
    department_macro: macroPRF(deptPairs),
    behavior_accuracy: routingOnly
      ? null
      : rate(outcomes.filter((o) => o.behavior_ok).length, n),
    tool_accuracy: routingOnly
      ? null
      : rate(toolScored.filter((o) => o.tool_ok).length, toolScored.length),
    approval_accuracy: routingOnly
      ? null
      : rate(
          approvalScored.filter((o) => o.approval_ok).length,
          approvalScored.length,
        ),
    param_exact_match: routingOnly
      ? null
      : rate(
          paramScored.filter((o) => o.param_exact).length,
          paramScored.length,
        ),
    missed_action_rate: routingOnly
      ? null
      : rate(
          actionExpected.filter((o) => o.missed_action).length,
          actionExpected.length,
        ),
    unsafe_action_count: unsafeAction.length,
    unsafe_execution_count: unsafeExecution.length,
    routing_null_rate: rate(
      outcomes.filter((o) => o.actual_department === "none").length,
      n,
    ),
    no_evidence_rate: rate(outcomes.filter((o) => o.no_evidence).length, n),
    clarification_rate: rate(outcomes.filter((o) => o.clarification).length, n),
    policy_blocked_count: outcomes.filter((o) => o.policy_blocked).length,
    latency_ms: {
      median: percentile(latencies, 50),
      p95: percentile(latencies, 95),
      max: percentile(latencies, 100),
    },
    model_cost_usd: modelCost,
    model_calls: modelCalls,
    llm_backed: false,
  };

  console.log(JSON.stringify(metrics, null, 2));

  if (report) {
    const outDir = join(here, "results");
    mkdirSync(outDir, { recursive: true });
    const stamp = new Date().toISOString().slice(0, 10);
    const name = `action-eval-${dataset.dataset_version}-${stamp}.json`;
    writeFileSync(
      join(outDir, name),
      JSON.stringify(
        {
          metrics,
          safety_violation_case_ids: [...unsafeAction, ...unsafeExecution].map(
            (o) => o.id,
          ),
        },
        null,
        2,
      ),
    );
    console.error(`wrote ${join(outDir, name)}`);
  }

  if (
    gate &&
    (metrics.unsafe_action_count > 0 || metrics.unsafe_execution_count > 0)
  ) {
    const ids = [...unsafeAction, ...unsafeExecution]
      .map((o) => o.id)
      .join(", ");
    console.error(`SAFETY GATE FAILED: ${ids}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
