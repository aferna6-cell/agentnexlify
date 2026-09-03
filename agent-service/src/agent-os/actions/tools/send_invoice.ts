/**
 * send_invoice — Billing Automation v1 level-2 send.
 *
 * The engine declares this tool. It does not send mail, SMS, or create a
 * Stripe Payment Link. After the owner approves, FastAPI claims the
 * os_tool_executions row and the Python data plane talks to the existing
 * invoice send + Stripe helpers.
 *
 * INVOICE_ACTIONS_ENABLED defaults off. No mark-paid. No auto-send-all.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION, ToolExecutionError } from "../types.ts";
import { INVOICING_DEPARTMENT, SEND_INVOICE_TOOL_ID } from "../flags.ts";

const Input = z.object({
  invoice_id: z.string().min(1),
  method: z.enum(["email", "sms", "both"]).default("email"),
});

const Output = z.object({
  invoiceId: z.string(),
  invoiceNumber: z.string(),
  status: z.string(),
  emailSent: z.boolean(),
  smsSent: z.boolean(),
  paymentLink: z.string().optional(),
  deduplicated: z.boolean(),
  detail: z.string(),
});

export type SendInvoiceInput = z.infer<typeof Input>;
export type SendInvoiceOutput = z.infer<typeof Output>;

export const sendInvoice = defineTool({
  id: SEND_INVOICE_TOOL_ID,
  displayName: "Send invoice",
  description:
    "Sends a prepared invoice to the customer with a payment link. External communication — the owner must approve every send. Does not mark the invoice paid.",
  department: INVOICING_DEPARTMENT,
  requiredConnectors: ["stripe"],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute(): Promise<SendInvoiceOutput> {
    throw new ToolExecutionError(
      "data_plane_only",
      "send_invoice runs in the data plane after owner approval; the engine does not send invoices",
    );
  },
});
