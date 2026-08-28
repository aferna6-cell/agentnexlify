/**
 * ActionStore — the persistence seam for action executions.
 *
 * Mirrors `lib/providers/run-store.ts`: the executor writes every execution
 * through this interface and the host decides where the rows live. In
 * agent-service the implementation collects rows for FastAPI to persist into
 * `os_tool_executions`; in tests it is in-memory.
 *
 * `transition()` is the important method. Approve-then-execute must run the tool
 * exactly once even if the approval endpoint is called twice, so the executor
 * never does read-then-write: it asks the store for a conditional transition and
 * only proceeds if it won. An in-memory store satisfies that with a synchronous
 * compare-and-set; a SQL store satisfies it with
 * `UPDATE ... WHERE id = $1 AND status = ANY($2) RETURNING *`.
 */

import type { ActionExecutionRecord, ActionExecutionStatus } from "./types.ts";

export interface ActionExecutionFilter {
  accountId: string;
  runId?: string;
  status?: ActionExecutionStatus;
  toolId?: string;
}

export interface ActionStore {
  /** Insert a new execution row. */
  create(record: ActionExecutionRecord): Promise<ActionExecutionRecord>;
  /** Fetch one row, or null. */
  get(id: string): Promise<ActionExecutionRecord | null>;
  /** Patch a row that is already in the expected state. */
  update(id: string, patch: Partial<ActionExecutionRecord>): Promise<ActionExecutionRecord>;
  /**
   * Conditionally move a row from one of `from` to `to`, applying `patch`.
   * Returns null when the row is not in an expected state — the caller then
   * knows another actor already moved it and must not execute.
   */
  transition(
    id: string,
    from: ActionExecutionStatus[],
    to: ActionExecutionStatus,
    patch?: Partial<ActionExecutionRecord>,
  ): Promise<ActionExecutionRecord | null>;
  /** Audit read. */
  list(filter: ActionExecutionFilter): Promise<ActionExecutionRecord[]>;
  /** Idempotency lookup; hosts without idempotency support may return null. */
  findByIdempotencyKey(accountId: string, toolId: string, key: string): Promise<ActionExecutionRecord | null>;
}

/** In-memory store: complete semantics, no durability. Tests and demos. */
export class InMemoryActionStore implements ActionStore {
  private readonly rows = new Map<string, ActionExecutionRecord>();

  async create(record: ActionExecutionRecord): Promise<ActionExecutionRecord> {
    if (this.rows.has(record.id)) {
      throw new Error(`duplicate action execution id "${record.id}"`);
    }
    this.rows.set(record.id, { ...record });
    return { ...record };
  }

  async get(id: string): Promise<ActionExecutionRecord | null> {
    const row = this.rows.get(id);
    return row ? { ...row } : null;
  }

  async update(id: string, patch: Partial<ActionExecutionRecord>): Promise<ActionExecutionRecord> {
    const row = this.rows.get(id);
    if (!row) throw new Error(`unknown action execution "${id}"`);
    const next = { ...row, ...patch, id: row.id };
    this.rows.set(id, next);
    return { ...next };
  }

  async transition(
    id: string,
    from: ActionExecutionStatus[],
    to: ActionExecutionStatus,
    patch: Partial<ActionExecutionRecord> = {},
  ): Promise<ActionExecutionRecord | null> {
    // Synchronous compare-and-set: no await between the read and the write, so
    // two concurrent callers cannot both win.
    const row = this.rows.get(id);
    if (!row || !from.includes(row.status)) return null;
    const next = { ...row, ...patch, status: to, id: row.id };
    this.rows.set(id, next);
    return { ...next };
  }

  async list(filter: ActionExecutionFilter): Promise<ActionExecutionRecord[]> {
    return [...this.rows.values()]
      .filter((r) => r.accountId === filter.accountId)
      .filter((r) => (filter.runId ? r.runId === filter.runId : true))
      .filter((r) => (filter.status ? r.status === filter.status : true))
      .filter((r) => (filter.toolId ? r.toolId === filter.toolId : true))
      .map((r) => ({ ...r }))
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }

  async findByIdempotencyKey(
    accountId: string,
    toolId: string,
    key: string,
  ): Promise<ActionExecutionRecord | null> {
    const hit = [...this.rows.values()].find(
      (r) => r.accountId === accountId && r.toolId === toolId && r.idempotencyKey === key,
    );
    return hit ? { ...hit } : null;
  }
}

let store: ActionStore | null = null;

/** Hosts call this once at startup. */
export function setActionStore(s: ActionStore): void {
  store = s;
}

export function getActionStore(): ActionStore {
  if (!store) {
    throw new Error(
      "No ActionStore registered. agent-service registers a request-scoped store " +
        "in src/agent-os-runtime/bootstrap.ts; tests register an InMemoryActionStore. " +
        "See docs/agent-os-action-layer.md.",
    );
  }
  return store;
}

export function hasActionStore(): boolean {
  return store !== null;
}

/** Test/diagnostic hook. */
export function resetActionStore(): void {
  store = null;
}
