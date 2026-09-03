/**
 * get_invoice — Billing Automation v1 level-0 read.
 *
 * Tenant-scoped by invoice id. Payment confirmation is the stored
 * Stripe/webhook status on the row — the tool never guesses "paid".
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY, ToolExecutionError } from "../types.ts";
import { GET_INVOICE_TOOL_ID, INVOICING_DEPARTMENT } from "../flags.ts";

const LineItem = z.object({
  description: z.string(),
  quantity: z.number(),
  unit_price: z.number(),
});

const Input = z.object({
  invoice_id: z.string().min(1),
});

const Output = z.object({
  invoiceId: z.string(),
  invoiceNumber: z.string(),
  customerId: z.string(),
  customerName: z.string().optional(),
  items: z.array(LineItem),
  subtotal: z.number(),
  taxRate: z.number(),
  taxAmount: z.number(),
  total: z.number(),
  status: z.string(),
  dueDate: z.string().optional(),
  notes: z.string().optional(),
  paymentLink: z.string().optional(),
  paidAt: z.string().optional(),
  paymentConfirmed: z.boolean(),
});

export type GetInvoiceInput = z.infer<typeof Input>;
export type GetInvoiceOutput = z.infer<typeof Output>;

export const getInvoice = defineTool({
  id: GET_INVOICE_TOOL_ID,
  displayName: "Get invoice",
  description:
    "Reads one invoice for this business by id. Read-only. Never returns another tenant's invoice. Paid is Stripe/webhook state, not an LLM guess.",
  department: INVOICING_DEPARTMENT,
  requiredConnectors: [],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<GetInvoiceOutput> {
    const inv = await context.ports.invoices.getInvoice({
      accountId: context.accountId,
      invoiceId: input.invoice_id,
    });
    if (!inv) {
      throw new ToolExecutionError(
        "invoice_not_found",
        `no invoice with id "${input.invoice_id}" in this business`,
      );
    }
    return {
      invoiceId: inv.id,
      invoiceNumber: inv.invoiceNumber,
      customerId: inv.customerId,
      customerName: inv.customerName,
      items: inv.items.map((i) => ({
        description: i.description,
        quantity: i.quantity,
        unit_price: i.unitPrice,
      })),
      subtotal: inv.subtotal,
      taxRate: inv.taxRate,
      taxAmount: inv.taxAmount,
      total: inv.total,
      status: inv.status,
      dueDate: inv.dueDate,
      notes: inv.notes,
      paymentLink: inv.paymentLink,
      paidAt: inv.paidAt,
      paymentConfirmed: inv.status === "paid",
    };
  },
});
