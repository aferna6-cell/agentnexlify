/**
 * send_email — the first real external action (level 2, data plane).
 *
 * The engine declares this tool: its id, its typed input, its risk level and
 * its approval requirement. It never runs it. The body lives in
 * `backend/services/os_tools/send_email.py`, where the tenant's Gmail
 * credentials are — see `implementation: "data_plane"` in types.ts for why the
 * split exists.
 *
 * What the engine guarantees before the data plane ever sees this:
 *  - the input parsed against the schema below,
 *  - policy classified it level 2, so it parked at `pending_approval`,
 *  - a durable execution row exists to approve.
 *
 * What the owner sees before approving is exactly what is validated here:
 * recipient, subject, body, and which agent asked. Nothing is sent until they
 * say so, and rejecting it means it can never be sent.
 *
 * The schema is mirrored by `SendEmailInput` in the Python module, and a
 * parity test asserts the two agree on id, risk level and approval — the
 * engine's classification is never the data plane's only line of defence.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION } from "../types.ts";

/**
 * Deliberately conservative: one recipient. An owner can actually read one
 * address in an approval prompt, and a mistaken approval reaches one person.
 */
const Input = z.object({
  to: z.string().min(3).max(254).email("recipient must be a valid email address"),
  subject: z.string().min(1).max(200),
  body: z.string().min(1).max(20000),
  /** Continue an existing Gmail conversation, when the agent has one. */
  thread_id: z.string().min(1).max(200).optional(),
  in_reply_to: z.string().min(1).max(500).optional(),
});

const Output = z.object({
  provider: z.literal("gmail"),
  messageId: z.string(),
  threadId: z.string().optional(),
  to: z.string(),
  subject: z.string(),
  /** The Message-ID header the send carried — the idempotency fingerprint. */
  rfc822MsgId: z.string(),
  /** True when a message with that fingerprint already existed and was adopted. */
  deduplicated: z.boolean(),
  detail: z.string(),
});

export type SendEmailInput = z.infer<typeof Input>;
export type SendEmailOutput = z.infer<typeof Output>;

export const sendEmail = defineTool({
  id: "send_email",
  displayName: "Send email",
  description:
    "Sends an email from the business's own connected Gmail mailbox. External communication — the owner must approve every send.",
  department: "sales",
  requiredConnectors: ["gmail"],
  implementation: "data_plane",
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,
});
