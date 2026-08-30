/**
 * cancel_calendar_event — Milestone 8. Customer-facing cancel → level 2.
 * Never cancels on ambiguous language — caller must supply a concrete event_id.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION, ToolExecutionError } from "../types.ts";

const Input = z.object({
  event_id: z.string().min(1),
  reason: z.string().max(1000).optional(),
  send_invitations: z.boolean().optional(),
});

const Output = z.object({
  eventId: z.string(),
  status: z.literal("cancelled"),
  title: z.string(),
  provider: z.string(),
  durable: z.boolean(),
});

export type CancelCalendarEventInput = z.infer<typeof Input>;
export type CancelCalendarEventOutput = z.infer<typeof Output>;

export const cancelCalendarEvent = defineTool({
  id: "cancel_calendar_event",
  displayName: "Cancel calendar event",
  description:
    "Cancels an existing appointment by id. Customer-facing cancellation requires owner approval. Does not cancel from ambiguous language alone.",
  department: "admin_records",
  requiredConnectors: ["google_calendar"],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<CancelCalendarEventOutput> {
    const port = context.ports.calendar;
    const existing = await port.getEvent({
      accountId: context.accountId,
      eventId: input.event_id,
    });
    if (!existing) {
      throw new ToolExecutionError(
        "event_not_found",
        `no event with id "${input.event_id}" on this business's calendar`,
      );
    }

    const record = await port.cancelEvent({
      accountId: context.accountId,
      eventId: input.event_id,
      reason: input.reason,
      sendInvitations: input.send_invitations,
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      eventId: record.id,
      status: "cancelled",
      title: record.title,
      provider: record.provider,
      durable: port.durable,
    };
  },

  async verify({ output, context }) {
    const fetched = await context.ports.calendar.getEvent({
      accountId: context.accountId,
      eventId: output.eventId,
    });
    if (!fetched) {
      return {
        verified: false,
        detail: `cancelled event ${output.eventId} disappeared on read-back`,
      };
    }
    if (fetched.status !== "cancelled") {
      return {
        verified: false,
        detail: `event ${output.eventId} still status=${fetched.status} after cancel`,
      };
    }
    return {
      verified: true,
      detail: `event ${output.eventId} cancellation confirmed`,
      evidence: { status: fetched.status },
    };
  },
});
