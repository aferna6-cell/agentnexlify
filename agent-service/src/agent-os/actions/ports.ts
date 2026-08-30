/**
 * Capability ports — the seam every tool reaches the outside world through.
 *
 * A tool never opens a database handle, an HTTP client, or a credential store
 * itself. It asks a *port*. That is what keeps this layer honest and portable:
 *  - the engine stays datasource-agnostic (the same rule the RunStore and
 *    SharedContext seams already enforce — see tests/no-direct-db guards),
 *  - a port declares whether its writes are `durable`, so nothing can claim a
 *    side effect outlived the process when it did not,
 *  - and future capabilities (Gmail, Google Calendar, a CRM, an MCP server, a
 *    browser/computer-use driver) arrive as new ports without the executor,
 *    policy, registry or audit trail changing at all.
 *
 * Production registers its implementations once at startup, exactly like
 * `setRunStore()` / `setSharedContextProvider()`.
 */

export interface CustomerNoteRecord {
  id: string;
  /** The customer/lead this note is attached to. */
  customerId: string;
  customerName?: string;
  note: string;
  /** What created the note, e.g. "agent:admin_records". */
  source: string;
  createdAt: string;
}

export interface AppendCustomerNoteInput {
  accountId: string;
  customerId: string;
  customerName?: string;
  note: string;
  source: string;
}

/** Internal notes attached to a customer record. Level-1 (reversible) writes. */
export interface CustomerNotesPort {
  /** Identifies the implementation in the audit trail. */
  readonly name: string;
  /** True only when the write survives the process. */
  readonly durable: boolean;
  append(input: AppendCustomerNoteInput): Promise<CustomerNoteRecord>;
  list(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerNoteRecord[]>;
}

// --- Calendar (Milestone 8) ---------------------------------------------------

export interface BusyInterval {
  start: string;
  end: string;
}

export interface AvailableSlot {
  start: string;
  end: string;
}

export interface CalendarAvailabilityQuery {
  accountId: string;
  start: string;
  end: string;
  durationMinutes: number;
  timezone: string;
  calendarId?: string;
}

export interface CalendarAvailabilityResult {
  availableSlots: AvailableSlot[];
  busyIntervals: BusyInterval[];
  provider: string;
  timezone: string;
  verifiedAt: string;
}

export interface CalendarAttendee {
  email: string;
  displayName?: string;
}

export interface CreateCalendarEventInput {
  accountId: string;
  start: string;
  end: string;
  timezone: string;
  title: string;
  description?: string;
  location?: string;
  attendees?: CalendarAttendee[];
  customerId?: string;
  sendInvitations?: boolean;
  /** Deterministic fingerprint for search-before-create / retry dedupe. */
  idempotencyKey?: string;
  calendarId?: string;
}

export interface CalendarEventRecord {
  id: string;
  accountId: string;
  start: string;
  end: string;
  timezone: string;
  title: string;
  description?: string;
  location?: string;
  attendees: CalendarAttendee[];
  customerId?: string;
  sendInvitations: boolean;
  status: "confirmed" | "cancelled";
  provider: string;
  providerEventId?: string;
  createdAt: string;
  updatedAt: string;
  idempotencyKey?: string;
}

export interface RescheduleCalendarEventInput {
  accountId: string;
  eventId: string;
  start: string;
  end: string;
  timezone: string;
  sendInvitations?: boolean;
}

export interface CancelCalendarEventInput {
  accountId: string;
  eventId: string;
  reason?: string;
  sendInvitations?: boolean;
}

/**
 * Calendar capability port. Tools never call Google / M365 HTTP themselves.
 * Availability must never be invented: empty or error is honest.
 */
export interface CalendarPort {
  readonly name: string;
  readonly durable: boolean;
  getAvailability(
    query: CalendarAvailabilityQuery,
  ): Promise<CalendarAvailabilityResult>;
  createEvent(input: CreateCalendarEventInput): Promise<CalendarEventRecord>;
  getEvent(input: {
    accountId: string;
    eventId: string;
  }): Promise<CalendarEventRecord | null>;
  /**
   * Find an existing event matching a fingerprint (tenant + window + title +
   * customer). Used for search-before-create when the provider has no native
   * idempotency token. Best-effort — documented as such.
   */
  findByFingerprint(input: {
    accountId: string;
    start: string;
    end: string;
    title: string;
    customerId?: string;
    idempotencyKey?: string;
  }): Promise<CalendarEventRecord | null>;
  rescheduleEvent(
    input: RescheduleCalendarEventInput,
  ): Promise<CalendarEventRecord>;
  cancelEvent(input: CancelCalendarEventInput): Promise<CalendarEventRecord>;
}

// --- CRM (Milestone 8) — canonical store is `leads` ---------------------------

export interface CustomerRecord {
  id: string;
  accountId: string;
  name: string;
  status: string;
  email?: string;
  phone?: string;
  address?: string;
  subject?: string;
  metadata?: Record<string, string>;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateCustomerInput {
  accountId: string;
  customerId: string;
  /** Only listed fields are written; omitted fields are preserved. */
  fields: {
    phone?: string;
    email?: string;
    address?: string;
    name?: string;
    subject?: string;
    metadata?: Record<string, string>;
  };
}

export interface CreateCustomerInput {
  accountId: string;
  /** When set (e.g. hydrating a known pipeline lead id), use this id. */
  id?: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  status?: string;
  subject?: string;
}

export interface UpdateLeadStageInput {
  accountId: string;
  customerId: string;
  status: string;
}

/** CRM / leads capability port. Tenant-scoped; never cross-tenant. */
export interface CrmPort {
  readonly name: string;
  readonly durable: boolean;
  getCustomer(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerRecord | null>;
  listCustomers(input: { accountId: string }): Promise<CustomerRecord[]>;
  updateCustomer(input: UpdateCustomerInput): Promise<CustomerRecord>;
  createCustomer(input: CreateCustomerInput): Promise<CustomerRecord>;
  updateLeadStage(input: UpdateLeadStageInput): Promise<CustomerRecord>;
}

/** The full port surface handed to tools. New capabilities extend this. */
export interface ToolPorts {
  customerNotes: CustomerNotesPort;
  calendar: CalendarPort;
  crm: CrmPort;
}

/**
 * Process-local notes port. Real writes and real read-backs (the verifier
 * genuinely re-reads what was written) — but not durable, and it says so.
 * Used by tests and by any host that has not registered a durable port.
 */
export class InMemoryCustomerNotesPort implements CustomerNotesPort {
  readonly name = "in_memory";
  readonly durable = false;
  private readonly notes = new Map<string, CustomerNoteRecord[]>();
  private seq = 0;

  private key(accountId: string, customerId: string): string {
    return `${accountId}::${customerId}`;
  }

  async append(input: AppendCustomerNoteInput): Promise<CustomerNoteRecord> {
    const record: CustomerNoteRecord = {
      id: `note_${++this.seq}`,
      customerId: input.customerId,
      customerName: input.customerName,
      note: input.note,
      source: input.source,
      createdAt: new Date().toISOString(),
    };
    const k = this.key(input.accountId, input.customerId);
    this.notes.set(k, [...(this.notes.get(k) ?? []), record]);
    return record;
  }

  async list(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerNoteRecord[]> {
    return [
      ...(this.notes.get(this.key(input.accountId, input.customerId)) ?? []),
    ];
  }
}

/** In-memory calendar for tests — honest availability from configured busy blocks. */
export class InMemoryCalendarPort implements CalendarPort {
  readonly name = "in_memory_calendar";
  readonly durable = false;
  private readonly events = new Map<string, CalendarEventRecord>();
  private readonly busyByAccount = new Map<string, BusyInterval[]>();
  private seq = 0;
  /** When set, getAvailability throws — surfaces provider errors honestly. */
  failAvailabilityWith: string | null = null;

  seedBusy(accountId: string, intervals: BusyInterval[]): void {
    this.busyByAccount.set(accountId, [...intervals]);
  }

  seedEvent(event: CalendarEventRecord): void {
    this.events.set(event.id, { ...event });
  }

  async getAvailability(
    query: CalendarAvailabilityQuery,
  ): Promise<CalendarAvailabilityResult> {
    if (this.failAvailabilityWith) {
      throw new Error(this.failAvailabilityWith);
    }
    const busy = (this.busyByAccount.get(query.accountId) ?? []).filter(
      (b) => b.end > query.start && b.start < query.end,
    );
    // Also treat confirmed events as busy.
    for (const e of this.events.values()) {
      if (
        e.accountId === query.accountId &&
        e.status === "confirmed" &&
        e.end > query.start &&
        e.start < query.end
      ) {
        busy.push({ start: e.start, end: e.end });
      }
    }
    const durationMs = query.durationMinutes * 60_000;
    const availableSlots: AvailableSlot[] = [];
    const windowStart = Date.parse(query.start);
    const windowEnd = Date.parse(query.end);
    if (
      !Number.isFinite(windowStart) ||
      !Number.isFinite(windowEnd) ||
      windowEnd <= windowStart
    ) {
      return {
        availableSlots: [],
        busyIntervals: busy,
        provider: this.name,
        timezone: query.timezone,
        verifiedAt: new Date().toISOString(),
      };
    }
    // Simple slot scan: 30-minute steps; skip any overlap with busy.
    for (let t = windowStart; t + durationMs <= windowEnd; t += 30 * 60_000) {
      const slotStart = new Date(t).toISOString();
      const slotEnd = new Date(t + durationMs).toISOString();
      const overlaps = busy.some((b) => b.end > slotStart && b.start < slotEnd);
      if (!overlaps) availableSlots.push({ start: slotStart, end: slotEnd });
    }
    return {
      availableSlots,
      busyIntervals: busy,
      provider: this.name,
      timezone: query.timezone,
      verifiedAt: new Date().toISOString(),
    };
  }

  async createEvent(
    input: CreateCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    if (input.idempotencyKey) {
      const existing = await this.findByFingerprint({
        accountId: input.accountId,
        start: input.start,
        end: input.end,
        title: input.title,
        customerId: input.customerId,
        idempotencyKey: input.idempotencyKey,
      });
      if (existing) return existing;
    }
    const now = new Date().toISOString();
    const id = `evt_${++this.seq}`;
    const record: CalendarEventRecord = {
      id,
      accountId: input.accountId,
      start: input.start,
      end: input.end,
      timezone: input.timezone,
      title: input.title,
      description: input.description,
      location: input.location,
      attendees: input.attendees ? [...input.attendees] : [],
      customerId: input.customerId,
      sendInvitations: Boolean(input.sendInvitations),
      status: "confirmed",
      provider: this.name,
      providerEventId: `prov_${id}`,
      createdAt: now,
      updatedAt: now,
      idempotencyKey: input.idempotencyKey,
    };
    this.events.set(id, record);
    return { ...record };
  }

  async getEvent(input: {
    accountId: string;
    eventId: string;
  }): Promise<CalendarEventRecord | null> {
    const e = this.events.get(input.eventId);
    if (!e || e.accountId !== input.accountId) return null;
    return { ...e };
  }

  async findByFingerprint(input: {
    accountId: string;
    start: string;
    end: string;
    title: string;
    customerId?: string;
    idempotencyKey?: string;
  }): Promise<CalendarEventRecord | null> {
    for (const e of this.events.values()) {
      if (e.accountId !== input.accountId || e.status !== "confirmed") continue;
      if (input.idempotencyKey && e.idempotencyKey === input.idempotencyKey)
        return { ...e };
      if (
        e.start === input.start &&
        e.end === input.end &&
        e.title === input.title &&
        (e.customerId ?? "") === (input.customerId ?? "")
      ) {
        return { ...e };
      }
    }
    return null;
  }

  async rescheduleEvent(
    input: RescheduleCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    const e = this.events.get(input.eventId);
    if (!e || e.accountId !== input.accountId) {
      throw new Error(`event not found: ${input.eventId}`);
    }
    if (e.status === "cancelled")
      throw new Error(`event already cancelled: ${input.eventId}`);
    const next: CalendarEventRecord = {
      ...e,
      start: input.start,
      end: input.end,
      timezone: input.timezone,
      sendInvitations: input.sendInvitations ?? e.sendInvitations,
      updatedAt: new Date().toISOString(),
    };
    this.events.set(e.id, next);
    return { ...next };
  }

  async cancelEvent(
    input: CancelCalendarEventInput,
  ): Promise<CalendarEventRecord> {
    const e = this.events.get(input.eventId);
    if (!e || e.accountId !== input.accountId) {
      throw new Error(`event not found: ${input.eventId}`);
    }
    const next: CalendarEventRecord = {
      ...e,
      status: "cancelled",
      sendInvitations: input.sendInvitations ?? e.sendInvitations,
      updatedAt: new Date().toISOString(),
    };
    this.events.set(e.id, next);
    return { ...next };
  }

  /** Test helper. */
  allEvents(): CalendarEventRecord[] {
    return [...this.events.values()].map((e) => ({ ...e }));
  }
}

/** Canonical lead statuses when tenant pipeline_stages is empty. */
export const CANONICAL_LEAD_STATUSES = [
  "new",
  "contacted",
  "appointment_booked",
  "closed",
  "lost",
] as const;

/** In-memory CRM / leads for tests. */
export class InMemoryCrmPort implements CrmPort {
  readonly name = "in_memory_crm";
  readonly durable = false;
  private readonly customers = new Map<string, CustomerRecord>();
  private seq = 0;

  seed(customer: CustomerRecord): void {
    this.customers.set(customer.id, { ...customer });
  }

  async getCustomer(input: {
    accountId: string;
    customerId: string;
  }): Promise<CustomerRecord | null> {
    const c = this.customers.get(input.customerId);
    if (!c || c.accountId !== input.accountId) return null;
    return { ...c };
  }

  async listCustomers(input: { accountId: string }): Promise<CustomerRecord[]> {
    return [...this.customers.values()]
      .filter((c) => c.accountId === input.accountId)
      .map((c) => ({ ...c }));
  }

  async updateCustomer(input: UpdateCustomerInput): Promise<CustomerRecord> {
    const c = this.customers.get(input.customerId);
    if (!c || c.accountId !== input.accountId) {
      throw new Error(`customer not found: ${input.customerId}`);
    }
    const next: CustomerRecord = {
      ...c,
      phone: input.fields.phone !== undefined ? input.fields.phone : c.phone,
      email: input.fields.email !== undefined ? input.fields.email : c.email,
      address:
        input.fields.address !== undefined ? input.fields.address : c.address,
      name: input.fields.name !== undefined ? input.fields.name : c.name,
      subject:
        input.fields.subject !== undefined ? input.fields.subject : c.subject,
      metadata:
        input.fields.metadata !== undefined
          ? { ...(c.metadata ?? {}), ...input.fields.metadata }
          : c.metadata,
      updatedAt: new Date().toISOString(),
    };
    this.customers.set(c.id, next);
    return { ...next };
  }

  async createCustomer(input: CreateCustomerInput): Promise<CustomerRecord> {
    // Duplicate-aware: email then phone.
    const existing = [...this.customers.values()].filter(
      (c) => c.accountId === input.accountId,
    );
    if (input.email) {
      const byEmail = existing.find(
        (c) =>
          c.email &&
          c.email.trim().toLowerCase() === input.email!.trim().toLowerCase(),
      );
      if (byEmail) return { ...byEmail };
    }
    if (input.phone) {
      const norm = input.phone.replace(/\D/g, "");
      const byPhone = existing.find(
        (c) =>
          c.phone && c.phone.replace(/\D/g, "") === norm && norm.length > 0,
      );
      if (byPhone) return { ...byPhone };
    }
    const now = new Date().toISOString();
    let id = input.id;
    if (!id) {
      do {
        id = `lead_${++this.seq}`;
      } while (this.customers.has(id));
    } else if (this.customers.has(id)) {
      const existingById = this.customers.get(id)!;
      if (existingById.accountId === input.accountId)
        return { ...existingById };
    }
    const record: CustomerRecord = {
      id,
      accountId: input.accountId,
      name: input.name,
      status: input.status ?? "new",
      email: input.email,
      phone: input.phone,
      address: input.address,
      subject: input.subject,
      createdAt: now,
      updatedAt: now,
    };
    this.customers.set(id, record);
    return { ...record };
  }

  async updateLeadStage(input: UpdateLeadStageInput): Promise<CustomerRecord> {
    const c = this.customers.get(input.customerId);
    if (!c || c.accountId !== input.accountId) {
      throw new Error(`customer not found: ${input.customerId}`);
    }
    const next: CustomerRecord = {
      ...c,
      status: input.status,
      updatedAt: new Date().toISOString(),
    };
    this.customers.set(c.id, next);
    return { ...next };
  }

  /** Test / collector helper. */
  allCustomers(): CustomerRecord[] {
    return [...this.customers.values()].map((c) => ({ ...c }));
  }
}

let ports: ToolPorts | null = null;

/** Hosts call this once at startup with their real capability implementations. */
export function setToolPorts(p: ToolPorts): void {
  ports = p;
}

export function getToolPorts(): ToolPorts {
  if (!ports) {
    throw new Error(
      "No ToolPorts registered. Call setToolPorts() at startup (agent-service " +
        "does this in src/agent-os-runtime/bootstrap.ts); tests can register " +
        "in-memory ports. See docs/agent-os-action-layer.md.",
    );
  }
  return ports;
}

export function hasToolPorts(): boolean {
  return ports !== null;
}

/** Test/diagnostic hook: drop the registration so a suite can re-register. */
export function resetToolPorts(): void {
  ports = null;
}
