/**
 * Eval-only send_email tool. Not registered on the production toolRegistry.
 *
 * execute() is the only send body this runner may enter. It requires
 * FakeGmailPort on context.ports.gmail — a missing port aborts instead of
 * attaching a live mailbox. L2 still parks at pending_approval, so the body
 * does not run on a normal proposal.
 */

import { z } from "zod";
import { defineTool } from "../../src/agent-os/actions/define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION } from "../../src/agent-os/actions/types.ts";
import { FakeGmailPort } from "./fake-gmail-port.ts";
import { LiveOsToolExecutionAbort } from "./live-db-lock.ts";
import { assertSendEmailEvalSafe } from "./eval-send-boundary.ts";

const Input = z.object({
  to: z.string().min(1),
  subject: z.string().optional(),
  body: z.string().optional(),
});

const Output = z.object({
  messageId: z.string(),
  delivered: z.literal(false),
  to: z.string(),
});

export const evalSendEmail = defineTool({
  id: "send_email",
  displayName: "Send email (eval-only)",
  description:
    "Eval-only Level-2 send. FakeGmailPort is the only allowed boundary; delivered is always false.",
  requiredConnectors: [],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }) {
    const port = context.ports.gmail;
    assertSendEmailEvalSafe(process.env, port);
    if (!(port instanceof FakeGmailPort) || port.durable !== false) {
      throw new LiveOsToolExecutionAbort(
        "send_email execute refused: FakeGmailPort is the only send boundary",
      );
    }
    const result = await port.send({
      to: input.to,
      subject: input.subject,
      body: input.body,
    });
    if (result.delivered !== false) {
      throw new LiveOsToolExecutionAbort(
        "FakeGmailPort claimed a live delivery",
      );
    }
    context.declareEffect({ port: port.name, durable: false });
    return {
      messageId: result.messageId,
      delivered: false as const,
      to: input.to,
    };
  },
});
