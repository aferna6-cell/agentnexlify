/**
 * add_customer_note — reference tool B (level 1, internal mutation, verified).
 *
 * Attaches an internal note to a customer already in the tenant's pipeline. The
 * customer is resolved from the SharedContext the data plane assembled, so the
 * tool can only ever write against a record that belongs to this tenant — an
 * agent cannot invent a customer id and reach another business's data.
 *
 * Level 1, because the note is internal and reversible: nothing leaves the
 * business, no money moves, and removing it restores the prior state.
 *
 * `verify()` is a genuine read-back: it re-reads the customer's notes through
 * the port and confirms the note it just wrote is actually there. If the write
 * silently no-ops, the execution ends `verification_failed` — never "succeeded".
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";
import type { PipelineLeadData } from "../../types/agent.ts";

const Input = z
  .object({
    /** Preferred: the customer's id from the pipeline. */
    customer_id: z.string().min(1).optional(),
    /** Fallback: a name to resolve against the pipeline (exact, then prefix). */
    customer_name: z.string().min(1).optional(),
    note: z.string().min(1).max(2000),
  })
  .refine((v) => Boolean(v.customer_id || v.customer_name), {
    message: "either customer_id or customer_name is required",
  });

const Output = z.object({
  noteId: z.string(),
  customerId: z.string(),
  customerName: z.string(),
  note: z.string(),
  createdAt: z.string(),
  /** Whether the port that stored the note is durable. Never assumed. */
  durable: z.boolean(),
});

export type AddCustomerNoteInput = z.infer<typeof Input>;
export type AddCustomerNoteOutput = z.infer<typeof Output>;

/** Resolve a pipeline customer by id, then exact name, then unique prefix. */
export function resolveCustomer(
  leads: PipelineLeadData[],
  input: { customer_id?: string; customer_name?: string },
): PipelineLeadData | null {
  if (input.customer_id) {
    return leads.find((l) => l.id === input.customer_id) ?? null;
  }
  const name = (input.customer_name ?? "").trim().toLowerCase();
  if (!name) return null;

  const exact = leads.filter((l) => l.name.trim().toLowerCase() === name);
  if (exact.length === 1) return exact[0]!;
  if (exact.length > 1) return null; // ambiguous — refuse rather than guess

  const partial = leads.filter((l) => l.name.trim().toLowerCase().startsWith(name));
  return partial.length === 1 ? partial[0]! : null;
}

export const addCustomerNote = defineTool({
  id: "add_customer_note",
  displayName: "Add customer note",
  description:
    "Adds an internal note to a customer's record in the business's own pipeline. Internal only — nothing is sent to the customer.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<AddCustomerNoteOutput> {
    const customer = resolveCustomer(context.sharedContext.pipelineLeads, input);
    if (!customer) {
      throw new ToolExecutionError(
        "customer_not_found",
        input.customer_id
          ? `no customer with id "${input.customer_id}" in this business's pipeline`
          : `could not match "${input.customer_name}" to exactly one customer in this business's pipeline`,
      );
    }

    const port = context.ports.customerNotes;
    const record = await port.append({
      accountId: context.accountId,
      customerId: customer.id,
      customerName: customer.name,
      note: input.note,
      source: context.agentId ? `agent:${context.agentId}` : "agent_os",
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      noteId: record.id,
      customerId: record.customerId,
      customerName: customer.name,
      note: record.note,
      createdAt: record.createdAt,
      durable: port.durable,
    };
  },

  async verify({ output, context }) {
    const notes = await context.ports.customerNotes.list({
      accountId: context.accountId,
      customerId: output.customerId,
    });
    const found = notes.find((n) => n.id === output.noteId);
    if (!found) {
      return {
        verified: false,
        detail: `note ${output.noteId} was not found on ${output.customerName}'s record when read back`,
        evidence: { noteCount: notes.length },
      };
    }
    if (found.note !== output.note) {
      return {
        verified: false,
        detail: `note ${output.noteId} read back with different text than was written`,
      };
    }
    return {
      verified: true,
      detail: `note ${output.noteId} confirmed on ${output.customerName}'s record (${context.ports.customerNotes.name} store)`,
      evidence: { noteId: found.id, createdAt: found.createdAt },
    };
  },
});
