/**
 * list_overdue_invoices — Billing Automation v1 level-0 read.
 *
 * Tenant-scoped. Paid invoices never appear here. Payment status comes from
 * stored Stripe/webhook state on the invoice row — never guessed.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY } from "../types.ts";
import {
  INVOICING_DEPARTMENT,
  LIST_OVERDUE_INVOICES_TOOL_ID,
} from "../flags.ts";

const InvoiceSummary = z.object({
  invoiceId: z.string(),
  invoiceNumber: z.string(),
  customerId: z.string(),
  customerName: z.string().optional(),
  total: z.number(),
  dueDate: z.string().optional(),
  status: z.string(),
  daysOverdue: z.number().optional(),
  paymentLink: z.string().optional(),
});

const Input = z.object({
  limit: z.number().int().min(1).max(100).optional(),
});

const Output = z.object({
  invoices: z.array(InvoiceSummary),
  count: z.number(),
});

export type ListOverdueInvoicesInput = z.infer<typeof Input>;
export type ListOverdueInvoicesOutput = z.infer<typeof Output>;

function daysOverdue(dueDate: string | undefined): number | undefined {
  if (!dueDate) return undefined;
  const due = Date.parse(`${dueDate}T00:00:00.000Z`);
  if (!Number.isFinite(due)) return undefined;
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);
  const delta = Math.floor((today.getTime() - due) / 86_400_000);
  return delta > 0 ? delta : 0;
}

export const listOverdueInvoices = defineTool({
  id: LIST_OVERDUE_INVOICES_TOOL_ID,
  displayName: "List overdue invoices",
  description:
    "Lists overdue, unpaid invoices for this business. Read-only. Never invents payment status or includes another tenant's invoices.",
  department: INVOICING_DEPARTMENT,
  requiredConnectors: [],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<ListOverdueInvoicesOutput> {
    const rows = await context.ports.invoices.listInvoices({
      accountId: context.accountId,
      overdueOnly: true,
    });
    const limit = input.limit ?? 50;
    const invoices = rows.slice(0, limit).map((inv) => ({
      invoiceId: inv.id,
      invoiceNumber: inv.invoiceNumber,
      customerId: inv.customerId,
      customerName: inv.customerName,
      total: inv.total,
      dueDate: inv.dueDate,
      status: inv.status,
      daysOverdue: daysOverdue(inv.dueDate),
      paymentLink: inv.paymentLink,
    }));
    return { invoices, count: invoices.length };
  },
});
