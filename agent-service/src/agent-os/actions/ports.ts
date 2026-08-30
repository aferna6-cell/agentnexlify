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

/** Outbound mail. Eval injects FakeGmailPort; production does not register this. */
export interface GmailPort {
  readonly name: string;
  readonly durable: boolean;
  send(input: {
    to: string;
    subject?: string;
    body?: string;
  }): Promise<{ messageId: string; delivered: boolean }>;
}

/** The full port surface handed to tools. New capabilities extend this. */
export interface ToolPorts {
  customerNotes: CustomerNotesPort;
  /**
   * Eval-only send seam. Optional so production `scopedToolPorts` is unchanged.
   * This runner never leaves it `None` and never enables SEND_EMAIL_ENABLED
   * (that flag + a missing port is the live Gmail attach path).
   */
  gmail?: GmailPort;
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
