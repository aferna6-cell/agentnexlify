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
import { RunRecordCollector, type RunRecordBundle } from "./run-record-collector.ts";
import { registerAgentOsProviders } from "./bootstrap.ts";

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
}

export interface OrchestrateOutput {
  result: HandleResult;
  record: RunRecordBundle;
}

export async function runOrchestration(input: OrchestrateInput): Promise<OrchestrateOutput> {
  const record = new RunRecordCollector();
  return requestScope.run({ accountId: input.accountId, context: input.context, record }, async () => {
    const result = await handle(input.accountId, input.ask, input.forceAgentId ? { forceAgentId: input.forceAgentId } : {});
    return { result, record: record.toBundle() };
  });
}
