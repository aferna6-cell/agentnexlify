/**
 * runOrchestration — the agent-service entry point for one tenant turn.
 *
 * FastAPI calls this (via POST /orchestrate) with the tenant's pre-assembled
 * SharedContext. It runs the vendored orchestrator inside an AsyncLocalStorage
 * scope and returns the routing/draft result plus a RunRecordBundle for FastAPI
 * to persist into the `os_*` tables. agent-service touches no database.
 */

import { handle, type HandleResult } from "../agent-os/agents/_orchestrator.ts";
import type { SharedContext } from "../agent-os/types/agent.ts";
import { requestScope } from "./request-scope.ts";
import {
  RunRecordCollector,
  type RunRecordBundle,
} from "./run-record-collector.ts";
import { registerAgentOsProviders } from "./bootstrap.ts";
import {
  CollectingActionStore,
  CollectingCustomerNotesPort,
} from "./action-collector.ts";
import type { TenantToolPolicy } from "../agent-os/actions/policy.ts";
import { applyRagToContext } from "../agent-os/rag/attach.ts";

registerAgentOsProviders();

export interface OrchestrateInput {
  /** FastAPI-verified tenant id (client_id). */
  accountId: string;
  /** The owner's ask. */
  ask: string;
  /** Context FastAPI assembled from Supabase for this tenant. */
  context: SharedContext;
  /** Owner override: force routing to this agent. */
  forceAgentId?: string;
  /**
   * The tenant's tool policy (which tools are enabled, what needs approval).
   * Omitted means the safe defaults: reads and internal writes run, external
   * communication and high-impact actions need approval.
   */
  toolPolicy?: TenantToolPolicy;
}

export interface OrchestrateOutput {
  result: HandleResult;
  record: RunRecordBundle;
}

export async function runOrchestration(
  input: OrchestrateInput,
): Promise<OrchestrateOutput> {
  const record = new RunRecordCollector();
  const actions = {
    store: new CollectingActionStore(),
    notes: new CollectingCustomerNotesPort(),
    policy: input.toolPolicy ?? {},
  };
  const context = applyRagToContext(input.accountId, input.ask, input.context);
  return requestScope.run(
    { accountId: input.accountId, context, record, actions },
    async () => {
      const result = await handle(
        input.accountId,
        input.ask,
        input.forceAgentId ? { forceAgentId: input.forceAgentId } : {},
      );
      return {
        result,
        record: record.withActions(
          actions.store.toBundle(),
          actions.notes.toBundle(),
        ),
      };
    },
  );
}

// Re-export for tests / callers that need the contract helper directly.
export { applyRagToContext };
