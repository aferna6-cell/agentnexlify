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
  UpdateCustomerInput,
  UpdateLeadStageInput,
} from "../agent-os/actions/ports.ts";
import {
  InMemoryCalendarPort,
  InMemoryCrmPort,
} from "../agent-os/actions/ports.ts";

/** Collects execution rows for the data plane to persist. */
export class CollectingActionStore implements ActionStore {
  private readonly rows = new Map<string, ActionExecutionRecord>();

  /** Seed a row that already exists in the database (the approval path). */
  seed(record: ActionExecutionRecord): void {
    this.rows.set(record.id, { ...record });
  }

  async create(record: ActionExecutionRecord): Promise<ActionExecutionRecord> {
    if (this.rows.has(record.id))
      throw new Error(`duplicate action execution id "${record.id}"`);
    this.rows.set(record.id, { ...record });
    return { ...record };
  }

  async get(id: string): Promise<ActionExecutionRecord | null> {
    const row = this.rows.get(id);
    return row ? { ...row } : null;
  }

  async update(
    id: string,
    patch: Partial<ActionExecutionRecord>,
  ): Promise<ActionExecutionRecord> {
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
      (r) =>
        r.accountId === accountId &&
        r.toolId === toolId &&
        r.idempotencyKey === key,
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

  async list(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerNoteRecord[]> {
    return [...this.existing, ...this.written]
      .filter((n) => n.customerId === input.customerId)
      .map((n) => ({ ...n }));
  }

  /** Notes written this request, for the data plane to apply. */
  toBundle(): CustomerNoteRecord[] {
    return this.written.map((n) => ({ ...n }));
  }
}

/**
 * Calendar port for the orchestration path. Mutations are held for FastAPI to
 * apply via google_calendar / appointments; verify() still reads back here.
 *
 * Availability is fail-closed until FastAPI seeds busy intervals (or an
 * explicit provider error). Empty unseeded busy must never invent "all free".
 */
export class CollectingCalendarPort implements CalendarPort {
  readonly name = "agent_service_calendar_bundle";
  readonly durable = true;
  private readonly inner = new InMemoryCalendarPort();
  private readonly mutatedIds = new Set<string>();
  private availabilitySeeded = false;
  private availabilityError: string | null = null;

  /** Expose inner for tests that need to seed busy intervals. */
  get memory(): InMemoryCalendarPort {
    return this.inner;
  }

  seedBusyForAccount(
    accountId: string,
    busy: { start: string; end: string }[],
  ): void {
    this.availabilitySeeded = true;
    this.inner.seedBusy(accountId, busy);
  }

  markAvailabilityError(message: string): void {
    this.availabilitySeeded = true;
    this.availabilityError = message;
  }

  seedExistingEvent(event: CalendarEventRecord): void {
    this.inner.seedEvent(event);
  }

  getAvailability(
    query: CalendarAvailabilityQuery,
  ): Promise<CalendarAvailabilityResult> {
    if (this.availabilityError) {
      return Promise.reject(new Error(this.availabilityError));
    }
    if (!this.availabilitySeeded) {
      return Promise.reject(
        new Error(
          "calendar availability could not be verified: no provider snapshot",
        ),
      );
    }
    return this.inner.getAvailability(query);
  }
  async createEvent(
    input: CreateCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    const record = await this.inner.createEvent(input);
    this.mutatedIds.add(record.id);
    return record;
  }
  getEvent(input: {
    accountId: string;
    eventId: string;
  }): Promise<CalendarEventRecord | null> {
    return this.inner.getEvent(input);
  }
  findByFingerprint(input: {
    accountId: string;
    start: string;
    end: string;
    title: string;
    customerId?: string;
    idempotencyKey?: string;
  }): Promise<CalendarEventRecord | null> {
    return this.inner.findByFingerprint(input);
  }
  async rescheduleEvent(
    input: RescheduleCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    const record = await this.inner.rescheduleEvent(input);
    this.mutatedIds.add(record.id);
    return record;
  }
  async cancelEvent(
    input: CancelCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    const record = await this.inner.cancelEvent(input);
    this.mutatedIds.add(record.id);
    return record;
  }

  /** Events created/updated/cancelled this request — not seeded history. */
  toBundle(): CalendarEventRecord[] {
    const byId = new Map(this.inner.allEvents().map((e) => [e.id, e]));
    return [...this.mutatedIds]
      .map((id) => byId.get(id))
      .filter((e): e is CalendarEventRecord => Boolean(e))
      .map((e) => ({ ...e }));
  }
}

export type CrmMutationBundle = CustomerRecord & {
  _op: "create" | "update" | "stage";
  fields?: UpdateCustomerInput["fields"];
};

/** CRM port for the orchestration path — collects mutations for FastAPI. */
export class CollectingCrmPort implements CrmPort {
  readonly name = "agent_service_crm_bundle";
  readonly durable = true;
  private readonly inner = new InMemoryCrmPort();
  private readonly mutations = new Map<
    string,
    {
      op: "create" | "update" | "stage";
      fields?: UpdateCustomerInput["fields"];
    }
  >();

  get memory(): InMemoryCrmPort {
    return this.inner;
  }

  seedCustomer(customer: CustomerRecord): void {
    this.inner.seed(customer);
  }

  getCustomer(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerRecord | null> {
    return this.inner.getCustomer(input);
  }
  listCustomers(input: { accountId: string }): Promise<CustomerRecord[]> {
    return this.inner.listCustomers(input);
  }
  async updateCustomer(input: UpdateCustomerInput): Promise<CustomerRecord> {
    const record = await this.inner.updateCustomer(input);
    this.mutations.set(record.id, {
      op: "update",
      fields: { ...input.fields },
    });
    return record;
  }
  async createCustomer(input: CreateCustomerInput): Promise<CustomerRecord> {
    const before = input.id
      ? await this.inner.getCustomer({
          accountId: input.accountId,
          customerId: input.id,
        })
      : null;
    const record = await this.inner.createCustomer(input);
    // Hydrating an already-seeded lead is not a data-plane create.
    if (!before) {
      this.mutations.set(record.id, { op: "create" });
    }
    return record;
  }
  async updateLeadStage(input: UpdateLeadStageInput): Promise<CustomerRecord> {
    const record = await this.inner.updateLeadStage(input);
    this.mutations.set(record.id, { op: "stage" });
    return record;
  }

  /** Customers created or updated this request, for the data plane. */
  toBundle(): CrmMutationBundle[] {
    const byId = new Map(this.inner.allCustomers().map((c) => [c.id, c]));
    const out: CrmMutationBundle[] = [];
    for (const [id, meta] of this.mutations) {
      const c = byId.get(id);
      if (!c) continue;
      out.push({
        ...c,
        _op: meta.op,
        ...(meta.fields ? { fields: meta.fields } : {}),
      });
    }
    return out;
  }
}
