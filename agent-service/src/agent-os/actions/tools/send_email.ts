/**
 * send_email — capability-gated external send (level 2), data-plane execute.
 *
 * The engine declares this tool: id, schema, department, risk, approval.
 * It does not send mail. After the owner approves, FastAPI claims the
 * os_tool_executions row and the Python data plane talks to Gmail.
 *
 * SEND_EMAIL_ENABLED defaults off. Policy denies the tool when the flag is off
 * or the proposing department lacks the explicit email capability.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION, ToolExecutionError } from "../types.ts";
import { SEND_EMAIL_TOOL_ID } from "../flags.ts";

const Input = z.object({
  to: z
    .string()
    .min(3)
    .max(254)
    .email("recipient must be a valid email address"),
  subject: z.string().min(1).max(200),
  body: z.string().min(1).max(20000),
  thread_id: z.string().min(1).max(200).optional(),
  in_reply_to: z.string().min(1).max(500).optional(),
});

const Output = z.object({
  provider: z.literal("gmail"),
  messageId: z.string(),
  threadId: z.string().optional(),
  to: z.string(),
  subject: z.string(),
  rfc822MsgId: z.string(),
  deduplicated: z.boolean(),
  detail: z.string(),
});

export type SendEmailInput = z.infer<typeof Input>;
export type SendEmailOutput = z.infer<typeof Output>;

export const sendEmail = defineTool({
  id: SEND_EMAIL_TOOL_ID,
  displayName: "Send email",
  description:
    "Sends a single-recipient email from the business's own connected Gmail mailbox. Only explicitly capable departments may propose it, and the owner must approve every send.",
  requiredConnectors: ["gmail"],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute(): Promise<SendEmailOutput> {
    throw new ToolExecutionError(
      "data_plane_only",
      "send_email runs in the data plane after owner approval; the engine does not send mail",
    );
  },
});
