/**
 * RunRecordCollector — captures everything the engine would have persisted.
 *
 * agent-service is pure compute: it never writes a database. Instead this
 * collector implements the engine's RunStore by recording each write into a
 * serializable bundle that /orchestrate returns to FastAPI, which persists it
 * into the `os_*` tables in one tenant-scoped transaction. IDs are minted here
 * (uuid) so the engine has the run/draft ids it needs mid-run; FastAPI maps
 * them to its own rows.
 */

import { randomUUID } from "node:crypto";
import type {
  RunStore,
  RoutingDecisionCreate,
  AgentRunCreate,
  AgentRunStatus,
  DraftCreate,
  TraceStepCreate,
  ModelCallCreate,
} from "../agent-os/lib/providers/run-store.ts";
import type { ActionExecutionRecord } from "../agent-os/actions/types.ts";
import type { CustomerNoteRecord } from "../agent-os/actions/ports.ts";

export interface CollectedDecision extends RoutingDecisionCreate {
  id: string;
  accepted?: boolean;
  changedTo?: string;
}
export interface CollectedRun extends AgentRunCreate {
  id: string;
  status: AgentRunStatus;
}
export interface CollectedDraft extends DraftCreate {
  id: string;
}
export interface RunRecordBundle {
  decisions: CollectedDecision[];
  runs: CollectedRun[];
  drafts: CollectedDraft[];
  traceSteps: TraceStepCreate[];
  modelCalls: ModelCallCreate[];
  wishlist: { userId: string; request: string; consideredAgents: string }[];
  /**
   * Tool executions the engine performed or parked this turn (the action-layer
   * audit trail). FastAPI persists them into `os_tool_executions`.
   */
  toolExecutions: ActionExecutionRecord[];
  /**
   * Internal customer notes a tool wrote this turn. FastAPI applies them to the
   * tenant's customer records.
   */
  customerNotes: CustomerNoteRecord[];
}

export class RunRecordCollector implements RunStore {
  private readonly bundle: RunRecordBundle = {
    decisions: [],
    runs: [],
    drafts: [],
    traceSteps: [],
    modelCalls: [],
    wishlist: [],
    toolExecutions: [],
    customerNotes: [],
  };

  async createRoutingDecision(input: RoutingDecisionCreate): Promise<{ id: string }> {
    const id = randomUUID();
    this.bundle.decisions.push({ ...input, id });
    return { id };
  }

  async markRoutingDecisionOverridden(decisionId: string, changedTo: string): Promise<void> {
    const d = this.bundle.decisions.find((x) => x.id === decisionId);
    if (d) {
      d.accepted = false;
      d.changedTo = changedTo;
    }
  }

  async createRun(input: AgentRunCreate): Promise<{ id: string }> {
    const id = randomUUID();
    this.bundle.runs.push({ ...input, id, status: "running" });
    return { id };
  }

  async setRunStatus(runId: string, status: AgentRunStatus): Promise<void> {
    const r = this.bundle.runs.find((x) => x.id === runId);
    if (r) r.status = status;
  }

  async createDraft(input: DraftCreate): Promise<{ id: string }> {
    const id = randomUUID();
    this.bundle.drafts.push({ ...input, id });
    return { id };
  }

  async captureWishlist(input: { userId: string; request: string; consideredAgents: string }): Promise<void> {
    this.bundle.wishlist.push({ ...input });
  }

  async recordTraceStep(input: TraceStepCreate): Promise<void> {
    this.bundle.traceSteps.push({ ...input });
  }

  async logModelCall(input: ModelCallCreate): Promise<void> {
    this.bundle.modelCalls.push({ ...input });
  }

  /**
   * The run bundle. The action layer keeps its own collectors (they implement
   * different seams), so orchestrate.ts folds those in via `withActions`.
   */
  toBundle(): RunRecordBundle {
    return this.bundle;
  }

  /** Return the bundle with this request's action-layer output attached. */
  withActions(
    toolExecutions: ActionExecutionRecord[],
    customerNotes: CustomerNoteRecord[],
  ): RunRecordBundle {
    return { ...this.bundle, toolExecutions, customerNotes };
  }
}
