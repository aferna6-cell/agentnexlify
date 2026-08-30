/**
 * runApprovedAction — execute an action the owner has approved.
 *
 * The engine is stateless, so a parked action lives in the data plane's
 * `os_tool_executions` table between the turn that created it and the moment the
 * owner approves. On approval FastAPI sends the stored row back here together
 * with a freshly assembled SharedContext; this rebuilds the execution inside a
 * request scope and drives it through the SAME executor the agent used, so
 * policy, verification and audit behave identically on both paths.
 *
 * At-most-once is enforced in two places, deliberately:
 *  - the data plane moves the row out of `pending_approval` with a conditional
 *    UPDATE to `running` before it calls here, so a double-clicked approval
 *    never reaches the engine twice;
 *  - the executor's own pending_approval -> running transition (approval_state
 *    becomes `approved`) stops a repeat inside a request.
 */

import { z } from "zod";
import { approveAction } from "../agent-os/actions/executor.ts";
import { requestScope } from "./request-scope.ts";
import { RunRecordCollector } from "./run-record-collector.ts";
import { registerAgentOsProviders } from "./bootstrap.ts";
import {
  CollectingActionStore,
  CollectingCalendarPort,
  CollectingCrmPort,
  CollectingCustomerNotesPort,
} from "./action-collector.ts";
import type {
  ActionExecutionRecord,
  RiskLevel,
} from "../agent-os/actions/types.ts";
import type { CustomerNoteRecord } from "../agent-os/actions/ports.ts";
import type { TenantToolPolicy } from "../agent-os/actions/policy.ts";
import type { SharedContext } from "../agent-os/types/agent.ts";

registerAgentOsProviders();

/** The stored execution, as the data plane holds it. */
export const PendingExecutionSchema = z.object({
  id: z.string().min(1),
  accountId: z.string().min(1),
  toolId: z.string().min(1),
  input: z.record(z.string(), z.unknown()),
  riskLevel: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
  mutating: z.boolean(),
  requiresApproval: z.boolean(),
  runId: z.string().min(1).optional(),
  agentId: z.string().min(1).optional(),
  policyReason: z.string().optional(),
  createdAt: z.string().optional(),
  attempts: z.number().int().min(0).optional(),
});

export type PendingExecution = z.infer<typeof PendingExecutionSchema>;

export interface ApproveActionInput {
  accountId: string;
  execution: PendingExecution;
  context: SharedContext;
  approvedBy: string;
  toolPolicy?: TenantToolPolicy;
  /** Notes already on the customer's record, so a verifier reads the real set. */
  existingNotes?: CustomerNoteRecord[];
}

export interface ApproveActionOutput {
  execution: ActionExecutionRecord;
  customerNotes: CustomerNoteRecord[];
}

export async function runApprovedAction(
  input: ApproveActionInput,
): Promise<ApproveActionOutput> {
  if (input.execution.accountId !== input.accountId) {
    throw new Error("isolation breach: execution belongs to another account");
  }

  const store = new CollectingActionStore();
  const notes = new CollectingCustomerNotesPort(input.existingNotes ?? []);
  const calendar = new CollectingCalendarPort();
  const crm = new CollectingCrmPort();

  // Rebuild the row the executor expects. Only the fields the data plane is
  // authoritative for are carried over; status is always `pending_approval`
  // here because the executor owns pending_approval -> running -> terminal
  // (approval_state becomes `approved`) and the data plane has already
  // decided this call is the one that runs.
  const seeded: ActionExecutionRecord = {
    id: input.execution.id,
    accountId: input.execution.accountId,
    runId: input.execution.runId,
    agentId: input.execution.agentId,
    toolId: input.execution.toolId,
    riskLevel: input.execution.riskLevel as RiskLevel,
    mutating: input.execution.mutating,
    requiresApproval: input.execution.requiresApproval,
    approvalState: "pending",
    status: "pending_approval",
    input: input.execution.input,
    verificationState: "not_applicable",
    policyReason: input.execution.policyReason ?? "approved by the owner",
    attempts: input.execution.attempts ?? 0,
    createdAt: input.execution.createdAt ?? new Date().toISOString(),
  };
  store.seed(seeded);

  const scope = {
    accountId: input.accountId,
    context: input.context,
    record: new RunRecordCollector(),
    actions: { store, notes, calendar, crm, policy: input.toolPolicy ?? {} },
  };

  return requestScope.run(scope, async () => {
    const outcome = await approveAction({
      accountId: input.accountId,
      executionId: seeded.id,
      approvedBy: input.approvedBy,
      sharedContext: input.context,
    });
    return { execution: outcome.record, customerNotes: notes.toBundle() };
  });
}
