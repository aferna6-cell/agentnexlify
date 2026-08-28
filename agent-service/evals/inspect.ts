/**
 * eval:inspect — look at what the Agent OS would decide for a single ask.
 *
 * A read-only debugging window onto the same path the benchmark measures. It
 * prints the department, the behaviour, any proposed action, its risk level and
 * whether policy would park it for approval.
 *
 * What it deliberately cannot do:
 *  - It cannot send mail. `send_email` is a `data_plane` tool with no engine
 *    body, and this process holds no Gmail credential.
 *  - It cannot approve anything. It never calls `approveAction`, and a parked
 *    action here lives in a per-request in-memory store that is discarded when
 *    the process exits.
 *  - It has no `--yes`, `--send` or `--approve` flag, and must never grow one.
 *    Approval is an act the owner performs in the dashboard against a durable
 *    execution row. A developer command that could stand in for that would make
 *    the whole approval gate a formality.
 *
 * Usage:
 *   npm run eval:inspect -- "Email sarah.chen@example.com about the brake quote"
 *   npm run eval:inspect -- --case act_email_001
 */

import { loadDataset, observedBehavior } from "./lib/eval-core.ts";
import { runOrchestration } from "../src/agent-os-runtime/orchestrate.ts";

const args = process.argv.slice(2);
const caseFlag = args.indexOf("--case");
const dataset = loadDataset();

let ask: string;
let expected: string | null = null;

if (caseFlag >= 0) {
  const id = args[caseFlag + 1];
  const found = dataset.cases.find((c) => c.id === id);
  if (!found) {
    console.error(`no case "${id}" in ${dataset.dataset_version}`);
    process.exit(2);
  }
  ask = found.ask;
  expected = `${found.expected_department} / ${found.expected_behavior} / ${found.expected_tool ?? "no tool"}`;
} else {
  ask = args.filter((a) => !a.startsWith("--")).join(" ").trim();
}

if (!ask) {
  console.error('usage: npm run eval:inspect -- "<ask>"   |   npm run eval:inspect -- --case <id>');
  process.exit(2);
}

const out = await runOrchestration({
  accountId: "inspect-tenant",
  ask,
  context: dataset.business_context,
});

const result = out.result;
const executions = out.record.toolExecutions;
const behavior = observedBehavior(result.status, Boolean(result.draft), executions);

console.log(`\nask:        ${ask}`);
if (expected) console.log(`expected:   ${expected}`);
console.log(`department: ${result.agentId ?? "none"}  (confidence ${result.confidence}, classifier ${result.classifier})`);
if (result.alternates.length) {
  console.log(`alternates: ${result.alternates.map((a) => `${a.agentId}:${a.confidence}`).join("  ")}`);
}
console.log(`status:     ${result.status}`);
console.log(`behavior:   ${behavior}`);
if (result.draft) console.log(`draft:      "${result.draft.title}" (${result.draft.body.length} chars)`);
if (result.noDraftReason) console.log(`no draft:   ${result.noDraftReason}`);

if (executions.length === 0) {
  console.log("actions:    none proposed\n");
} else {
  console.log("actions:");
  for (const e of executions) {
    console.log(`  ${e.toolId}  risk=${e.riskLevel}  mutating=${e.mutating}  requiresApproval=${e.requiresApproval}`);
    console.log(`    status:  ${e.status}${e.approvalState ? ` (approval: ${e.approvalState})` : ""}`);
    // Already redacted by the executor before it reached the record.
    console.log(`    input:   ${JSON.stringify(e.input)}`);
    if (e.error) console.log(`    error:   ${e.error.code}: ${e.error.message}`);
  }
  console.log(
    "\n  Nothing above was sent. A level-2 action rests at pending_approval until\n" +
      "  the owner approves it in the dashboard; this command cannot do that.\n",
  );
}
