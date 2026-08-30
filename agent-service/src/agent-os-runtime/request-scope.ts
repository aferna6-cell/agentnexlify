/**
 * Per-request scope for the agent-service orchestration runtime.
 *
 * The vendored engine reads through a single global SharedContextProvider and
 * writes through a single global RunStore (set once at startup). To serve many
 * tenants concurrently on one Node process without those globals racing, each
 * /orchestrate call runs inside an AsyncLocalStorage scope carrying that
 * request's pre-loaded context and a fresh run-record collector. The scoped
 * providers (scoped-providers.ts) read the current scope on every call, so
 * concurrent orchestrations never see each other's data.
 */

import { AsyncLocalStorage } from "node:async_hooks";
import type { SharedContext } from "../agent-os/types/agent.ts";
import type { RunRecordCollector } from "./run-record-collector.ts";
import type {
  CollectingActionStore,
  CollectingCalendarPort,
  CollectingCrmPort,
  CollectingCustomerNotesPort,
} from "./action-collector.ts";
import type { TenantToolPolicy } from "../agent-os/actions/policy.ts";

/** The action layer's per-request state: audit rows, note writes, tenant policy. */
export interface RequestActionScope {
  store: CollectingActionStore;
  notes: CollectingCustomerNotesPort;
  calendar: CollectingCalendarPort;
  crm: CollectingCrmPort;
  policy: TenantToolPolicy;
}

export interface RequestScope {
  /** The tenant this orchestration is scoped to (FastAPI-verified client_id). */
  accountId: string;
  /** Context FastAPI assembled from Supabase for this tenant. */
  context: SharedContext;
  /** Collects the run's writes for FastAPI to persist. */
  record: RunRecordCollector;
  /** Collects tool executions + note writes, and carries the tenant's policy. */
  actions: RequestActionScope;
}

export const requestScope = new AsyncLocalStorage<RequestScope>();

export function currentScope(): RequestScope {
  const s = requestScope.getStore();
  if (!s) {
    throw new Error(
      "no request scope: the agent engine ran outside runOrchestration(). " +
        "Every orchestration must go through src/agent-os-runtime/orchestrate.ts.",
    );
  }
  return s;
}
