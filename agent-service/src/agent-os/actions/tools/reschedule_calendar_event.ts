/**
 * reschedule_calendar_event — Milestone 8. Customer-facing → level 2 approval.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_EXTERNAL_COMMUNICATION, ToolExecutionError } from "../types.ts";

const Input = z.object({
  event_id: z.string().min(1),
  start: z.string().min(1),
  end: z.string().min(1),
  timezone: z.string().min(1).optional(),
  send_invitations: z.boolean().optional(),
});

const Output = z.object({
  eventId: z.string(),
  start: z.string(),
  end: z.string(),
  timezone: z.string(),
  title: z.string(),
  provider: z.string(),
  durable: z.boolean(),
});

export type RescheduleCalendarEventInput = z.infer<typeof Input>;
export type RescheduleCalendarEventOutput = z.infer<typeof Output>;

export const rescheduleCalendarEvent = defineTool({
  id: "reschedule_calendar_event",
  displayName: "Reschedule calendar event",
  description:
    "Moves an existing appointment. Alters an external commitment — owner approval required.",
  department: "admin_records",
  requiredConnectors: ["google_calendar"],
  riskLevel: RISK_EXTERNAL_COMMUNICATION,
  mutating: true,
  requiresApproval: true,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<RescheduleCalendarEventOutput> {
    const timezone =
      input.timezone?.trim() ||
      context.sharedContext.businessProfile.timezone?.trim() ||
      "America/New_York";
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

    const record = await port.rescheduleEvent({
      accountId: context.accountId,
      eventId: input.event_id,
      start: input.start,
      end: input.end,
      timezone,
      sendInvitations: input.send_invitations,
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      eventId: record.id,
      start: record.start,
      end: record.end,
      timezone: record.timezone,
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
        detail: `rescheduled event ${output.eventId} was not found on read-back`,
      };
    }
    if (fetched.start !== output.start || fetched.end !== output.end) {
      return {
        verified: false,
        detail: `rescheduled event ${output.eventId} time mismatch on read-back`,
      };
    }
    return {
      verified: true,
      detail: `event ${output.eventId} reschedule confirmed`,
      evidence: { start: fetched.start, end: fetched.end },
    };
  },
});
