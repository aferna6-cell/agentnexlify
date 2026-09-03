/**
 * create_invoice_draft — Billing Automation v1 level-1 internal write.
 *
 * Creates a draft invoice. Customer must already exist in this tenant —
 * never guessed. Amounts and line items are preserved exactly. Search-before-
 * create + independent GET verify.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";
import {
  CREATE_INVOICE_DRAFT_TOOL_ID,
  INVOICING_DEPARTMENT,
} from "../flags.ts";

const LineItem = z.object({
  description: z.string().min(1).max(500),
  quantity: z.number().positive(),
  unit_price: z.number().min(0),
});

const Input = z.object({
  customer_id: z.string().min(1),
  items: z.array(LineItem).min(1).max(100),
  tax_rate: z.number().min(0).max(100).optional(),
  due_date: z.string().min(1).optional(),
  due_in_days: z.number().int().min(1).max(365).optional(),
  notes: z.string().max(5000).optional(),
  idempotency_key: z.string().min(1).max(200).optional(),
});

const Output = z.object({
  invoiceId: z.string(),
  invoiceNumber: z.string(),
  customerId: z.string(),
  items: z.array(LineItem),
  subtotal: z.number(),
  taxRate: z.number(),
  taxAmount: z.number(),
  total: z.number(),
  dueDate: z.string().optional(),
  status: z.literal("draft"),
  deduplicated: z.boolean(),
  durable: z.boolean(),
});

export type CreateInvoiceDraftInput = z.infer<typeof Input>;
export type CreateInvoiceDraftOutput = z.infer<typeof Output>;

function resolveDueDate(input: CreateInvoiceDraftInput): string | undefined {
  if (input.due_date?.trim()) return input.due_date.trim();
  if (input.due_in_days == null) return undefined;
  const due = new Date();
  due.setUTCDate(due.getUTCDate() + input.due_in_days);
  return due.toISOString().slice(0, 10);
}

function itemsEqual(
  a: { description: string; quantity: number; unit_price: number }[],
  b: { description: string; quantity: number; unitPrice: number }[],
): boolean {
  if (a.length !== b.length) return false;
  return a.every(
    (item, i) =>
      item.description === b[i]!.description &&
      item.quantity === b[i]!.quantity &&
      item.unit_price === b[i]!.unitPrice,
  );
}

export const createInvoiceDraft = defineTool({
  id: CREATE_INVOICE_DRAFT_TOOL_ID,
  displayName: "Create invoice draft",
  description:
    "Creates a draft invoice for a known customer of this business. Line items and amounts are preserved exactly. Does not send. Does not mark paid.",
  department: INVOICING_DEPARTMENT,
  requiredConnectors: [],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<CreateInvoiceDraftOutput> {
    const inPipeline = context.sharedContext.pipelineLeads.some(
      (l) => l.id === input.customer_id,
    );
    const fromCrm = await context.ports.crm.getCustomer({
      accountId: context.accountId,
      customerId: input.customer_id,
    });
    if (!inPipeline && !fromCrm) {
      throw new ToolExecutionError(
        "customer_not_found",
        `no customer with id "${input.customer_id}" in this business — ask which customer, never guess`,
      );
    }
    const customerName =
      fromCrm?.name ||
      context.sharedContext.pipelineLeads.find(
        (l) => l.id === input.customer_id,
      )?.name;

    const port = context.ports.invoices;
    const items = input.items.map((i) => ({
      description: i.description,
      quantity: i.quantity,
      unitPrice: i.unit_price,
    }));
    const dueDate = resolveDueDate(input);
    const taxRate = input.tax_rate ?? 0;
    const fingerprint = {
      accountId: context.accountId,
      customerId: input.customer_id,
      items,
      dueDate,
      total: 0,
      idempotencyKey: input.idempotency_key,
    };
    const existing = await port.findByFingerprint({
      ...fingerprint,
      total:
        Math.round(
          items.reduce((s, i) => s + i.quantity * i.unitPrice, 0) *
            (1 + taxRate / 100) *
            100,
        ) / 100,
    });
    if (existing) {
      context.declareEffect({ port: port.name, durable: port.durable });
      return {
        invoiceId: existing.id,
        invoiceNumber: existing.invoiceNumber,
        customerId: existing.customerId,
        items: existing.items.map((i) => ({
          description: i.description,
          quantity: i.quantity,
          unit_price: i.unitPrice,
        })),
        subtotal: existing.subtotal,
        taxRate: existing.taxRate,
        taxAmount: existing.taxAmount,
        total: existing.total,
        dueDate: existing.dueDate,
        status: "draft",
        deduplicated: true,
        durable: port.durable,
      };
    }

    const record = await port.createDraft({
      accountId: context.accountId,
      customerId: input.customer_id,
      customerName,
      items,
      taxRate,
      dueDate,
      notes: input.notes,
      idempotencyKey: input.idempotency_key,
    });
    context.declareEffect({ port: port.name, durable: port.durable });
    return {
      invoiceId: record.id,
      invoiceNumber: record.invoiceNumber,
      customerId: record.customerId,
      items: record.items.map((i) => ({
        description: i.description,
        quantity: i.quantity,
        unit_price: i.unitPrice,
      })),
      subtotal: record.subtotal,
      taxRate: record.taxRate,
      taxAmount: record.taxAmount,
      total: record.total,
      dueDate: record.dueDate,
      status: "draft",
      deduplicated: false,
      durable: port.durable,
    };
  },

  async verify({ input, output, context }) {
    const fetched = await context.ports.invoices.getInvoice({
      accountId: context.accountId,
      invoiceId: output.invoiceId,
    });
    if (!fetched) {
      return {
        verified: false,
        detail: `invoice ${output.invoiceId} was not found when read back`,
      };
    }
    if (fetched.accountId && fetched.customerId !== output.customerId) {
      return {
        verified: false,
        detail: `invoice ${output.invoiceId} customer mismatch on read-back`,
      };
    }
    if (
      fetched.total !== output.total ||
      fetched.subtotal !== output.subtotal
    ) {
      return {
        verified: false,
        detail: `invoice ${output.invoiceId} amount mismatch on read-back`,
        evidence: {
          expected: { total: output.total, subtotal: output.subtotal },
          actual: { total: fetched.total, subtotal: fetched.subtotal },
        },
      };
    }
    if (!itemsEqual(output.items, fetched.items)) {
      return {
        verified: false,
        detail: `invoice ${output.invoiceId} line items mismatch on read-back`,
      };
    }
    if (fetched.status === "paid") {
      return {
        verified: false,
        detail: `invoice ${output.invoiceId} read back as paid — drafts never mark paid`,
      };
    }
    if (input.customer_id !== output.customerId) {
      return {
        verified: false,
        detail: "customer_id was not preserved",
      };
    }
    return {
      verified: true,
      detail: `invoice ${output.invoiceNumber} confirmed as draft (${context.ports.invoices.name})`,
      evidence: {
        invoiceId: fetched.id,
        total: fetched.total,
        verifiedAt: new Date().toISOString(),
      },
    };
  },
});
