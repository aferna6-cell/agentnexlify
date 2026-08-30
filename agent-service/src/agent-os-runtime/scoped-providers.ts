/**
 * Scoped provider implementations registered once at startup.
 *
 * Each reads the current AsyncLocalStorage request scope (request-scope.ts), so
 * one global instance safely serves concurrent tenants: the SharedContext and
 * the run-record collector both come from the in-flight request, never shared
 * mutable state.
 */

import type { SharedContextProvider } from "../agent-os/lib/providers/shared-context.ts";
import type {
  RunStore,
  RoutingDecisionCreate,
  AgentRunCreate,
  AgentRunStatus,
  DraftCreate,
  TraceStepCreate,
  ModelCallCreate,
} from "../agent-os/lib/providers/run-store.ts";
import type { OwnerActions } from "../agent-os/lib/providers/owner-actions.ts";
import type { SharedContext } from "../agent-os/types/agent.ts";
import type {
  ActionExecutionFilter,
  ActionStore,
} from "../agent-os/actions/store.ts";
import type {
  ActionExecutionRecord,
  ActionExecutionStatus,
} from "../agent-os/actions/types.ts";
import type {
  AppendCustomerNoteInput,
  CalendarAvailabilityQuery,
  CalendarAvailabilityResult,
  CalendarEventRecord,
  CalendarPort,
  CancelCalendarEventInput,
  CreateCalendarEventInput,
  CreateCustomerInput,
  CrmPort,
  CustomerNoteRecord,
  CustomerNotesPort,
  CustomerRecord,
  RescheduleCalendarEventInput,
  ToolPorts,
  UpdateCustomerInput,
  UpdateLeadStageInput,
} from "../agent-os/actions/ports.ts";
import type {
  TenantToolPolicy,
  ToolPolicyProvider,
} from "../agent-os/actions/policy.ts";
import { currentScope } from "./request-scope.ts";

/** Returns the context FastAPI pre-loaded for this request's tenant. */
export class ScopedSharedContextProvider implements SharedContextProvider {
  async load(userId: string): Promise<SharedContext> {
    const scope = currentScope();
    if (userId !== scope.accountId) {
      // Defense in depth: the orchestrator was asked for a tenant other than
      // the one this request is scoped to. Never serve cross-tenant data.
      throw new Error(
        `isolation breach: context requested for ${userId} but request scoped to ${scope.accountId}`,
      );
    }
    return scope.context;
  }
}

/** Delegates every write to the current request's collector. */
export class ScopedRunStore implements RunStore {
  createRoutingDecision(input: RoutingDecisionCreate): Promise<{ id: string }> {
    return currentScope().record.createRoutingDecision(input);
  }
  markRoutingDecisionOverridden(
    decisionId: string,
    changedTo: string,
  ): Promise<void> {
    return currentScope().record.markRoutingDecisionOverridden(
      decisionId,
      changedTo,
    );
  }
  createRun(input: AgentRunCreate): Promise<{ id: string }> {
    return currentScope().record.createRun(input);
  }
  setRunStatus(runId: string, status: AgentRunStatus): Promise<void> {
    return currentScope().record.setRunStatus(runId, status);
  }
  createDraft(input: DraftCreate): Promise<{ id: string }> {
    return currentScope().record.createDraft(input);
  }
  captureWishlist(input: {
    userId: string;
    request: string;
    consideredAgents: string;
  }): Promise<void> {
    return currentScope().record.captureWishlist(input);
  }
  recordTraceStep(input: TraceStepCreate): Promise<void> {
    return currentScope().record.recordTraceStep(input);
  }
  logModelCall(input: ModelCallCreate): Promise<void> {
    return currentScope().record.logModelCall(input);
  }
}

/**
 * No-op for the orchestrate path. The only agent that calls this is the
 * marketing ai_visibility_stub; production wires a real OwnerActions when that
 * agent ships. Returning true keeps the contract (best-effort, never throws).
 */
export class ScopedOwnerActions implements OwnerActions {
  async tagAiVisibilityInterest(_userId: string): Promise<boolean> {
    return true;
  }
}

/** Action executions go to the current request's collector, never a shared map. */
export class ScopedActionStore implements ActionStore {
  create(record: ActionExecutionRecord): Promise<ActionExecutionRecord> {
    return currentScope().actions.store.create(record);
  }
  get(id: string): Promise<ActionExecutionRecord | null> {
    return currentScope().actions.store.get(id);
  }
  update(
    id: string,
    patch: Partial<ActionExecutionRecord>,
  ): Promise<ActionExecutionRecord> {
    return currentScope().actions.store.update(id, patch);
  }
  transition(
    id: string,
    from: ActionExecutionStatus[],
    to: ActionExecutionStatus,
    patch?: Partial<ActionExecutionRecord>,
  ): Promise<ActionExecutionRecord | null> {
    return currentScope().actions.store.transition(id, from, to, patch);
  }
  list(filter: ActionExecutionFilter): Promise<ActionExecutionRecord[]> {
    return currentScope().actions.store.list(filter);
  }
  findByIdempotencyKey(
    accountId: string,
    toolId: string,
    key: string,
  ): Promise<ActionExecutionRecord | null> {
    return currentScope().actions.store.findByIdempotencyKey(
      accountId,
      toolId,
      key,
    );
  }
}

/** Note writes go to the current request's collector for the data plane to apply. */
export class ScopedCustomerNotesPort implements CustomerNotesPort {
  get name(): string {
    return currentScope().actions.notes.name;
  }
  get durable(): boolean {
    return currentScope().actions.notes.durable;
  }
  append(input: AppendCustomerNoteInput): Promise<CustomerNoteRecord> {
    return currentScope().actions.notes.append(input);
  }
  list(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerNoteRecord[]> {
    return currentScope().actions.notes.list(input);
  }
}

export class ScopedCalendarPort implements CalendarPort {
  get name(): string {
    return currentScope().actions.calendar.name;
  }
  get durable(): boolean {
    return currentScope().actions.calendar.durable;
  }
  getAvailability(
    query: CalendarAvailabilityQuery,
  ): Promise<CalendarAvailabilityResult> {
    return currentScope().actions.calendar.getAvailability(query);
  }
  createEvent(input: CreateCalendarEventInput): Promise<CalendarEventRecord> {
    return currentScope().actions.calendar.createEvent(input);
  }
  getEvent(input: {
    accountId: string;
    eventId: string;
  }): Promise<CalendarEventRecord | null> {
    return currentScope().actions.calendar.getEvent(input);
  }
  findByFingerprint(input: {
    accountId: string;
    start: string;
    end: string;
    title: string;
    customerId?: string;
    idempotencyKey?: string;
  }): Promise<CalendarEventRecord | null> {
    return currentScope().actions.calendar.findByFingerprint(input);
  }
  rescheduleEvent(
    input: RescheduleCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    return currentScope().actions.calendar.rescheduleEvent(input);
  }
  cancelEvent(input: CancelCalendarEventInput): Promise<CalendarEventRecord> {
    return currentScope().actions.calendar.cancelEvent(input);
  }
}

export class ScopedCrmPort implements CrmPort {
  get name(): string {
    return currentScope().actions.crm.name;
  }
  get durable(): boolean {
    return currentScope().actions.crm.durable;
  }
  getCustomer(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerRecord | null> {
    return currentScope().actions.crm.getCustomer(input);
  }
  listCustomers(input: { accountId: string }): Promise<CustomerRecord[]> {
    return currentScope().actions.crm.listCustomers(input);
  }
  updateCustomer(input: UpdateCustomerInput): Promise<CustomerRecord> {
    return currentScope().actions.crm.updateCustomer(input);
  }
  createCustomer(input: CreateCustomerInput): Promise<CustomerRecord> {
    return currentScope().actions.crm.createCustomer(input);
  }
  updateLeadStage(input: UpdateLeadStageInput): Promise<CustomerRecord> {
    return currentScope().actions.crm.updateLeadStage(input);
  }
}

/** The full port surface, all request-scoped. */
export const scopedToolPorts: ToolPorts = {
  customerNotes: new ScopedCustomerNotesPort(),
  calendar: new ScopedCalendarPort(),
  crm: new ScopedCrmPort(),
};

/** The tenant's tool policy, as supplied by the data plane for this request. */
export class ScopedToolPolicyProvider implements ToolPolicyProvider {
  async load(accountId: string): Promise<TenantToolPolicy> {
    const scope = currentScope();
    if (accountId !== scope.accountId) {
      throw new Error(
        `isolation breach: policy requested for ${accountId} but request scoped to ${scope.accountId}`,
      );
    }
    return scope.actions.policy;
  }
}
