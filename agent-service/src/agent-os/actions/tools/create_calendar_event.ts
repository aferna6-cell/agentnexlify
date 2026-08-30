/**
 * create_calendar_event — Milestone 8 create appointment/event.
 *
 * Baseline risk is level 1 (internal-only). Policy escalates to level 2 when
 * attendees or send_invitations are present. Search-before-create + verify
 * via independent GET after write.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";

const Attendee = z.object({
  email: z.string().email(),
  display_name: z.string().min(1).optional(),
});

const Input = z.object({
  start: z.string().min(1),
  end: z.string().min(1),
  timezone: z.string().min(1).optional(),
  title: z.string().min(1).max(500),
  description: z.string().max(5000).optional(),
  location: z.string().max(500).optional(),
  attendees: z.array(Attendee).max(50).optional(),
  customer_id: z.string().min(1).optional(),
  send_invitations: z.boolean().optional(),
  calendar_id: z.string().min(1).optional(),
  idempotency_key: z.string().min(1).max(200).optional(),
});

const Output = z.object({
  eventId: z.string(),
  providerEventId: z.string().optional(),
  start: z.string(),
  end: z.string(),
  timezone: z.string(),
  title: z.string(),
  attendees: z.array(Attendee),
  customerId: z.string().optional(),
  sendInvitations: z.boolean(),
  provider: z.string(),
  deduplicated: z.boolean(),
  durable: z.boolean(),
});

export type CreateCalendarEventInput = z.infer<typeof Input>;
export type CreateCalendarEventOutput = z.infer<typeof Output>;

export const createCalendarEvent = defineTool({
  id: "create_calendar_event",
  displayName: "Create calendar event",
  description:
    "Creates an appointment on the business calendar. Internal-only events run as level 1; events with external attendees or invitations require owner approval.",
  department: "admin_records",
  requiredConnectors: ["google_calendar"],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<CreateCalendarEventOutput> {
    const timezone =
      input.timezone?.trim() ||
      context.sharedContext.businessProfile.timezone?.trim() ||
      "America/New_York";
    const port = context.ports.calendar;
    const attendees = (input.attendees ?? []).map((a) => ({
      email: a.email,
      displayName: a.display_name,
    }));

    // Cross-tenant customer guard: if a customer_id is supplied it must be in
    // this tenant's pipeline (or CRM port). Never trust an unverified id.
    if (input.customer_id) {
      const inPipeline = context.sharedContext.pipelineLeads.some(
        (l) => l.id === input.customer_id,
      );
      const fromCrm = await context.ports.crm.getCustomer({
        accountId: context.accountId,
        customerId: input.customer_id,
      });
      if (!inPipeline && !fromCrm) {
        throw new ToolExecutionError(
          "customer_not_found",
          `no customer with id "${input.customer_id}" in this business`,
        );
      }
    }

    const fingerprint = {
      accountId: context.accountId,
      start: input.start,
      end: input.end,
      title: input.title,
      customerId: input.customer_id,
      idempotencyKey: input.idempotency_key,
    };
    const existing = await port.findByFingerprint(fingerprint);
    if (existing) {
      context.declareEffect({ port: port.name, durable: port.durable });
      return {
        eventId: existing.id,
        providerEventId: existing.providerEventId,
        start: existing.start,
        end: existing.end,
        timezone: existing.timezone,
        title: existing.title,
        attendees: existing.attendees.map((a) => ({
          email: a.email,
          display_name: a.displayName,
        })),
        customerId: existing.customerId,
        sendInvitations: existing.sendInvitations,
        provider: existing.provider,
        deduplicated: true,
        durable: port.durable,
      };
    }

    const record = await port.createEvent({
      accountId: context.accountId,
      start: input.start,
      end: input.end,
      timezone,
      title: input.title,
      description: input.description,
      location: input.location,
      attendees,
      customerId: input.customer_id,
      sendInvitations: Boolean(input.send_invitations),
      idempotencyKey: input.idempotency_key,
      calendarId: input.calendar_id,
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      eventId: record.id,
      providerEventId: record.providerEventId,
      start: record.start,
      end: record.end,
      timezone: record.timezone,
      title: record.title,
      attendees: record.attendees.map((a) => ({
        email: a.email,
        display_name: a.displayName,
      })),
      customerId: record.customerId,
      sendInvitations: record.sendInvitations,
      provider: record.provider,
      deduplicated: false,
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
        detail: `event ${output.eventId} was not found when read back from the calendar provider`,
      };
    }
    if (fetched.status !== "confirmed") {
      return {
        verified: false,
        detail: `event ${output.eventId} read back with status ${fetched.status}`,
      };
    }
    if (fetched.start !== output.start || fetched.end !== output.end) {
      return {
        verified: false,
        detail: `event ${output.eventId} time mismatch on read-back`,
        evidence: {
          expected: { start: output.start, end: output.end },
          actual: { start: fetched.start, end: fetched.end },
        },
      };
    }
    if (fetched.title !== output.title) {
      return {
        verified: false,
        detail: `event ${output.eventId} title mismatch on read-back`,
      };
    }
    const expectedEmails = new Set(
      output.attendees.map((a) => a.email.toLowerCase()),
    );
    const actualEmails = new Set(
      fetched.attendees.map((a) => a.email.toLowerCase()),
    );
    if (
      expectedEmails.size !== actualEmails.size ||
      [...expectedEmails].some((e) => !actualEmails.has(e))
    ) {
      return {
        verified: false,
        detail: `event ${output.eventId} attendee mismatch on read-back`,
      };
    }
    return {
      verified: true,
      detail: `event ${output.eventId} confirmed on calendar (${context.ports.calendar.name})`,
      evidence: {
        eventId: fetched.id,
        providerEventId: fetched.providerEventId,
        verifiedAt: new Date().toISOString(),
      },
    };
  },
});
