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
import { currentScope } from "./request-scope.ts";

/** Returns the context FastAPI pre-loaded for this request's tenant. */
export class ScopedSharedContextProvider implements SharedContextProvider {
  async load(userId: string): Promise<SharedContext> {
    const scope = currentScope();
    if (userId !== scope.accountId) {
      // Defense in depth: the orchestrator was asked for a tenant other than
      // the one this request is scoped to. Never serve cross-tenant data.
      throw new Error(`isolation breach: context requested for ${userId} but request scoped to ${scope.accountId}`);
    }
    return scope.context;
  }
}

/** Delegates every write to the current request's collector. */
export class ScopedRunStore implements RunStore {
  createRoutingDecision(input: RoutingDecisionCreate): Promise<{ id: string }> {
    return currentScope().record.createRoutingDecision(input);
  }
  markRoutingDecisionOverridden(decisionId: string, changedTo: string): Promise<void> {
    return currentScope().record.markRoutingDecisionOverridden(decisionId, changedTo);
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
  captureWishlist(input: { userId: string; request: string; consideredAgents: string }): Promise<void> {
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
