/**
 * get_calendar_availability — Milestone 8 level-0 read.
 *
 * Returns real available windows from the CalendarPort. Never invents slots:
 * empty list or a provider error is an honest outcome.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY, ToolExecutionError } from "../types.ts";

const Input = z.object({
  start: z.string().min(1),
  end: z.string().min(1),
  duration_minutes: z
    .number()
    .int()
    .positive()
    .max(24 * 60),
  timezone: z.string().min(1).optional(),
  calendar_id: z.string().min(1).optional(),
});

const Output = z.object({
  available_slots: z.array(z.object({ start: z.string(), end: z.string() })),
  busy_intervals: z.array(z.object({ start: z.string(), end: z.string() })),
  provider: z.string(),
  timezone: z.string(),
  verified_at: z.string(),
});

export type GetCalendarAvailabilityInput = z.infer<typeof Input>;
export type GetCalendarAvailabilityOutput = z.infer<typeof Output>;

export const getCalendarAvailability = defineTool({
  id: "get_calendar_availability",
  displayName: "Get calendar availability",
  description:
    "Reads available time windows on the business calendar for a search range and duration. Read-only — never invents availability.",
  department: "admin_records",
  requiredConnectors: ["google_calendar"],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<GetCalendarAvailabilityOutput> {
    const timezone =
      input.timezone?.trim() ||
      context.sharedContext.businessProfile.timezone?.trim() ||
      "America/New_York";

    try {
      const result = await context.ports.calendar.getAvailability({
        accountId: context.accountId,
        start: input.start,
        end: input.end,
        durationMinutes: input.duration_minutes,
        timezone,
        calendarId: input.calendar_id,
      });
      return {
        available_slots: result.availableSlots,
        busy_intervals: result.busyIntervals,
        provider: result.provider,
        timezone: result.timezone,
        verified_at: result.verifiedAt,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new ToolExecutionError(
        "calendar_provider_error",
        `calendar availability could not be verified: ${message}`,
      );
    }
  },
});
