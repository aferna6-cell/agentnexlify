/**
 * Request-scoped implementations of the action layer's seams.
 *
 * agent-service is pure compute: it never opens a database. So an action's audit
 * row and any note it writes are *collected* here and returned to FastAPI in the
 * same response, which persists them into `os_tool_executions` and the tenant's
 * CRM inside one tenant-scoped transaction. Same contract as
 * `RunRecordCollector` for runs, drafts and traces.
 *
 * Everything is per-request, so two tenants orchestrating concurrently can never
 * see each other's executions.
 */

import { randomUUID } from "node:crypto";
import type {
  ActionExecutionFilter,
  ActionStore,
} from "../agent-os/actions/store.ts";
import type { ActionExecutionRecord, ActionExecutionStatus } from "../agent-os/actions/types.ts";
import type {
  AppendCustomerNoteInput,
  CustomerNoteRecord,
  CustomerNotesPort,
} from "../agent-os/actions/ports.ts";

/** Collects execution rows for the data plane to persist. */
export class CollectingActionStore implements ActionStore {
  private readonly rows = new Map<string, ActionExecutionRecord>();

  /** Seed a row that already exists in the database (the approval path). */
  seed(record: ActionExecutionRecord): void {
    this.rows.set(record.id, { ...record });
  }

  async create(record: ActionExecutionRecord): Promise<ActionExecutionRecord> {
    if (this.rows.has(record.id)) throw new Error(`duplicate action execution id "${record.id}"`);
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
    // No await between read and write: two concurrent callers cannot both win.
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
      .map((r) => ({ ...r }));
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

  /** Every execution this request touched, for the data plane to persist. */
  toBundle(): ActionExecutionRecord[] {
    return [...this.rows.values()].map((r) => ({ ...r }));
  }
}

/**
 * Notes port for the orchestration path.
 *
 * Writes are held for the response and applied by the data plane (which appends
 * them to the customer's record) in the same request, so `durable` is true — but
 * the tool's own verifier still reads back through this port, which is what
 * makes "it landed" a check rather than an assumption. Reads see notes already
 * on the customer's record (passed in by the data plane) plus anything written
 * during this request.
 */
export class CollectingCustomerNotesPort implements CustomerNotesPort {
  readonly name = "agent_service_bundle";
  readonly durable = true;
  private readonly written: CustomerNoteRecord[] = [];
  private readonly existing: CustomerNoteRecord[];

  constructor(existing: CustomerNoteRecord[] = []) {
    this.existing = existing;
  }

  async append(input: AppendCustomerNoteInput): Promise<CustomerNoteRecord> {
    const record: CustomerNoteRecord = {
      id: randomUUID(),
      customerId: input.customerId,
      customerName: input.customerName,
      note: input.note,
      source: input.source,
      createdAt: new Date().toISOString(),
    };
    this.written.push(record);
    return { ...record };
  }

  async list(input: { accountId: string; customerId: string }): Promise<CustomerNoteRecord[]> {
    return [...this.existing, ...this.written]
      .filter((n) => n.customerId === input.customerId)
      .map((n) => ({ ...n }));
  }

  /** Notes written this request, for the data plane to apply. */
  toBundle(): CustomerNoteRecord[] {
    return this.written.map((n) => ({ ...n }));
  }
}
