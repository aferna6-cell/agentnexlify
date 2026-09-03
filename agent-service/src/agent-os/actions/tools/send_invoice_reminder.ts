/**
 * send_invoice_reminder — Billing Automation v1 level-2 reminder.
 *
 * Engine declares the tool; the data plane sends after owner approval.
 * Paid invoices must never receive a reminder. Spam is blocked by a
 * per-invoice-per-day activity tag. INVOICE_ACTIONS_ENABLED defaults off.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION, ToolExecutionError } from "../types.ts";
import {
  INVOICING_DEPARTMENT,
  SEND_INVOICE_REMINDER_TOOL_ID,
} from "../flags.ts";

const Input = z.object({
  invoice_id: z.string().min(1),
  method: z.enum(["email", "sms", "both"]).default("email"),
});

const Output = z.object({
  invoiceId: z.string(),
  invoiceNumber: z.string(),
  emailSent: z.boolean(),
  smsSent: z.boolean(),
  paymentLink: z.string().optional(),
  daysOverdue: z.number().optional(),
  deduplicated: z.boolean(),
  detail: z.string(),
});

export type SendInvoiceReminderInput = z.infer<typeof Input>;
export type SendInvoiceReminderOutput = z.infer<typeof Output>;

export const sendInvoiceReminder = defineTool({
  id: SEND_INVOICE_REMINDER_TOOL_ID,
  displayName: "Send invoice reminder",
  description:
    "Sends a payment reminder for an overdue unpaid invoice. Owner approval required. Never reminds a paid invoice. Does not mark paid.",
  department: INVOICING_DEPARTMENT,
  requiredConnectors: ["stripe"],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute(): Promise<SendInvoiceReminderOutput> {
    throw new ToolExecutionError(
      "data_plane_only",
      "send_invoice_reminder runs in the data plane after owner approval; the engine does not send reminders",
    );
  },
});
