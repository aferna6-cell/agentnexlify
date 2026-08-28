/**
 * Runtime tests for the action layer inside agent-service.
 *
 * agent-service is pure compute, so the properties that matter here are: an
 * action's audit row and its writes come back in the bundle for the data plane
 * to persist; the tenant's policy is honoured; an approval executes the parked
 * action through the same executor; and concurrent tenants never mix.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { runOrchestration } from "./orchestrate.ts";
import { runApprovedAction } from "./approve-action.ts";
import type { SharedContext } from "../agent-os/types/agent.ts";

const NOTE_ASK = "Add a note to Sarah Chen's record saying she prefers texts after 5pm.";

function ctxFor(businessName: string, leadName = "Sarah Chen", leadId = "lead_1"): SharedContext {
  return {
    businessProfile: { businessName, ownerName: "Owner", businessType: "auto_shop" },
    widgetHistory: [],
    pipelineLeads: [{ id: leadId, name: leadName, status: "quoted", subject: "brake job" }],
    appointments: [],
    invoices: [],
    agentRunHistory: [],
    kb: [],
  };
}

test("an action run through the engine comes back for the data plane to persist", async () => {
  const out = await runOrchestration({
    accountId: "tenantA",
    ask: NOTE_ASK,
    context: ctxFor("Acme Auto"),
    forceAgentId: "admin_records",
  });

  assert.equal(out.record.toolExecutions.length, 1);
  const execution = out.record.toolExecutions[0]!;
  assert.equal(execution.toolId, "add_customer_note");
  assert.equal(execution.accountId, "tenantA");
  assert.equal(execution.status, "succeeded");
  assert.equal(execution.verificationState, "passed");
  assert.equal(execution.riskLevel, 1);
  assert.equal(execution.runId, out.record.runs[0]?.id);

  assert.equal(out.record.customerNotes.length, 1);
  assert.equal(out.record.customerNotes[0]?.customerId, "lead_1");
  assert.match(out.record.customerNotes[0]?.note ?? "", /prefers texts after 5pm/);

  // The owner is told what happened and gets no draft to approve.
  assert.equal(out.record.drafts.length, 0);
  assert.match(out.result.orchestratorNotes.join(" "), /Added a note to Sarah Chen's record/);
});

test("the tenant's tool policy is honoured, and the action parks instead", async () => {
  const out = await runOrchestration({
    accountId: "tenantA",
    ask: NOTE_ASK,
    context: ctxFor("Acme Auto"),
    forceAgentId: "admin_records",
    toolPolicy: { approvalThreshold: 1 },
  });

  const execution = out.record.toolExecutions[0]!;
  assert.equal(execution.status, "pending_approval");
  assert.equal(execution.approvalState, "pending");
  assert.equal(out.record.customerNotes.length, 0, "nothing is written before approval");
});

test("approving a parked action executes it and returns the write to persist", async () => {
  const parked = (
    await runOrchestration({
      accountId: "tenantA",
      ask: NOTE_ASK,
      context: ctxFor("Acme Auto"),
      forceAgentId: "admin_records",
      toolPolicy: { approvalThreshold: 1 },
    })
  ).record.toolExecutions[0]!;

  const approved = await runApprovedAction({
    accountId: "tenantA",
    execution: {
      id: parked.id,
      accountId: parked.accountId,
      toolId: parked.toolId,
      input: parked.input,
      riskLevel: parked.riskLevel,
      mutating: parked.mutating,
      requiresApproval: parked.requiresApproval,
      runId: parked.runId,
      agentId: parked.agentId,
      policyReason: parked.policyReason,
      createdAt: parked.createdAt,
    },
    context: ctxFor("Acme Auto"),
    approvedBy: "owner@acme.test",
  });

  assert.equal(approved.execution.id, parked.id);
  assert.equal(approved.execution.status, "succeeded");
  assert.equal(approved.execution.approvalState, "approved");
  assert.equal(approved.execution.approvedBy, "owner@acme.test");
  assert.equal(approved.execution.attempts, 1);
  assert.equal(approved.customerNotes.length, 1);
});

test("an approval whose stored input no longer validates fails instead of running", async () => {
  const approved = await runApprovedAction({
    accountId: "tenantA",
    execution: {
      id: "exec_1",
      accountId: "tenantA",
      toolId: "add_customer_note",
      input: { customer_id: "lead_1" }, // note text missing
      riskLevel: 1,
      mutating: true,
      requiresApproval: true,
    },
    context: ctxFor("Acme Auto"),
    approvedBy: "owner@acme.test",
  });

  assert.equal(approved.execution.status, "failed");
  assert.equal(approved.execution.error?.code, "invalid_input");
  assert.equal(approved.customerNotes.length, 0);
});

test("an execution from another account is refused", async () => {
  await assert.rejects(
    () =>
      runApprovedAction({
        accountId: "tenantB",
        execution: {
          id: "exec_1",
          accountId: "tenantA",
          toolId: "add_customer_note",
          input: { customer_id: "lead_1", note: "hi" },
          riskLevel: 1,
          mutating: true,
          requiresApproval: true,
        },
        context: ctxFor("Bob Plumbing"),
        approvedBy: "attacker@example.test",
      }),
    /isolation breach/,
  );
});

test("concurrent tenants never see each other's actions", async () => {
  const [a, b] = await Promise.all([
    runOrchestration({
      accountId: "tenantA",
      ask: NOTE_ASK,
      context: ctxFor("Acme Auto"),
      forceAgentId: "admin_records",
    }),
    runOrchestration({
      accountId: "tenantB",
      ask: "Add a note to Bob Vance's record saying he pays by check.",
      context: ctxFor("Bob Plumbing", "Bob Vance", "lead_9"),
      forceAgentId: "admin_records",
    }),
  ]);

  assert.equal(a.record.toolExecutions.length, 1);
  assert.equal(b.record.toolExecutions.length, 1);
  assert.equal(a.record.toolExecutions[0]?.accountId, "tenantA");
  assert.equal(b.record.toolExecutions[0]?.accountId, "tenantB");
  assert.equal(a.record.customerNotes[0]?.customerId, "lead_1");
  assert.equal(b.record.customerNotes[0]?.customerId, "lead_9");
});
