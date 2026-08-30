/**
 * Operations — Calendar tool path (Milestone 8).
 *
 * Departments propose Calendar actions through the Action Executor. They never
 * call Google (or any provider) directly. When CALENDAR_ACTIONS_ENABLED is off
 * (the production default), this resolver returns undefined so behaviour matches
 * pre-M8: draft via the booking skill.
 *
 * Conservative rules:
 *  - Ambiguous customers → clarify (never first-row).
 *  - "Find a time / don't book" → availability read only.
 *  - Cancel/reschedule without a concrete event id → clarify.
 *  - Book without an explicit ISO start/end → clarify (do not invent times).
 *  - Invite/email language → create with attendees (L2 approval via policy).
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import { calendarActionsEnabled } from "../actions/flags.ts";
import type { SharedContext } from "../types/agent.ts";

const AVAILABILITY_RE =
  /\b(free|available|availability|openings?|when (am|are) (i|we)|find a time|what times?)\b/i;
const DRAFT_ONLY_RE =
  /\b(don'?t book|do not book|don'?t schedule|just (look|check|find)|could offer|might offer|suggest a time)\b/i;
const CANCEL_RE = /\b(cancel|cancels|cancelling|call off)\b/i;
const RESCHEDULE_RE = /\b(reschedule|move|push (back|to)|change the time)\b/i;
const INVITE_RE =
  /\b(invite|invitation|email (her|him|them|the )?(invite|calendar)|send (an? )?invite)\b/i;
const ISO_RANGE_RE = /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)/g;

function defaultSearchWindow(timezone: string): { start: string; end: string } {
  // Deterministic next-UTC-day afternoon window — honest placeholder until the
  // data plane supplies business_hours-derived bounds. Tools still refuse to
  // invent busy/free inside that window.
  const start = new Date();
  start.setUTCDate(start.getUTCDate() + 1);
  start.setUTCHours(14, 0, 0, 0);
  const end = new Date(start);
  end.setUTCHours(22, 0, 0, 0);
  void timezone;
  return { start: start.toISOString(), end: end.toISOString() };
}

export function resolveCalendarAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  if (!calendarActionsEnabled()) return undefined;

  const { ownerAsk, params, context, intent } = args;
  const tz = context.businessProfile.timezone?.trim() || "America/New_York";

  // Availability / draft-time suggestion — read only.
  if (
    intent.intent === "retrieve" ||
    DRAFT_ONLY_RE.test(ownerAsk) ||
    (AVAILABILITY_RE.test(ownerAsk) && intent.authorization === "draft_only")
  ) {
    if (AVAILABILITY_RE.test(ownerAsk) || DRAFT_ONLY_RE.test(ownerAsk)) {
      const window = defaultSearchWindow(tz);
      return {
        toolId: "get_calendar_availability",
        input: {
          start: window.start,
          end: window.end,
          duration_minutes: 60,
          timezone: tz,
        },
        describe: (result) => {
          const out = result as { available_slots?: { start: string }[] };
          const n = out.available_slots?.length ?? 0;
          return n
            ? `I found ${n} open slot(s) in that window (timezone ${tz}).`
            : `No open slots in that window (timezone ${tz}) — I did not invent any.`;
        },
      };
    }
  }

  if (intent.intent !== "schedule") return undefined;

  // Cancel / reschedule without a concrete event id must clarify.
  if (CANCEL_RE.test(ownerAsk)) {
    const eventId =
      typeof params.event_id === "string" ? params.event_id.trim() : "";
    if (!eventId) {
      return {
        clarify:
          "I can cancel an appointment, but I need the specific event id (or a uniquely identified booking). I won't cancel from ambiguous language alone.",
      };
    }
    if (intent.authorization === "draft_only") return undefined;
    return {
      toolId: "cancel_calendar_event",
      input: { event_id: eventId },
      describe: () =>
        `Cancellation for ${eventId} is queued for your approval.`,
    };
  }

  if (RESCHEDULE_RE.test(ownerAsk)) {
    const eventId =
      typeof params.event_id === "string" ? params.event_id.trim() : "";
    const matches = ownerAsk.match(ISO_RANGE_RE) ?? [];
    if (!eventId || matches.length < 2) {
      return {
        clarify:
          "To reschedule I need the event id and the new start/end times (ISO-8601). I won't guess a new slot.",
      };
    }
    if (intent.authorization === "draft_only") return undefined;
    return {
      toolId: "reschedule_calendar_event",
      input: {
        event_id: eventId,
        start: matches[0],
        end: matches[1],
        timezone: tz,
      },
      describe: () => `Reschedule of ${eventId} is queued for your approval.`,
    };
  }

  // Draft-only schedule asks → availability, not create.
  // Schedule imperatives ("book/schedule") often land as authorization
  // "ambiguous" because EXECUTE_MARKERS are communication-centric — treat
  // anything that is not explicitly draft_only as eligible to propose a tool
  // (policy still gates L2 approval and feature flags).
  if (intent.authorization === "draft_only" || DRAFT_ONLY_RE.test(ownerAsk)) {
    if (AVAILABILITY_RE.test(ownerAsk) || DRAFT_ONLY_RE.test(ownerAsk)) {
      const window = defaultSearchWindow(tz);
      return {
        toolId: "get_calendar_availability",
        input: {
          start: window.start,
          end: window.end,
          duration_minutes: 60,
          timezone: tz,
        },
      };
    }
    return undefined;
  }

  const customerName =
    typeof params.customer_name === "string" ? params.customer_name.trim() : "";
  if (!customerName) {
    return {
      clarify:
        "Who should I schedule? Tell me the customer name and the start/end time.",
    };
  }

  const resolution = resolveCustomerAnywhere(context, customerName);
  if (resolution.kind === "multiple") {
    const names = describeAmbiguity(resolution.matches, (m) => m.name);
    return {
      clarify: `I found more than one customer matching "${customerName}" — ${names}. Which one did you mean?`,
    };
  }
  if (resolution.kind === "none") {
    return {
      clarify: `I couldn't find a customer matching "${customerName}" in this business's records.`,
    };
  }

  const matches = ownerAsk.match(ISO_RANGE_RE) ?? [];
  if (matches.length < 2) {
    return {
      clarify: `I can book ${resolution.match.name}, but I need an explicit start and end time (ISO-8601). I won't invent a slot.`,
    };
  }

  const leadId = resolution.match.leadId;
  const wantInvite = INVITE_RE.test(ownerAsk);
  const input: Record<string, unknown> = {
    start: matches[0],
    end: matches[1],
    timezone: tz,
    title: `Appointment — ${resolution.match.name}`,
    customer_id: leadId,
    idempotency_key: `ops-${leadId ?? resolution.match.name}-${matches[0]}`,
  };
  if (wantInvite) {
    const lead = context.pipelineLeads.find((l) => l.id === leadId);
    if (!lead?.email) {
      return {
        clarify: `To send an invite for ${resolution.match.name} I need their email on file.`,
      };
    }
    input.attendees = [{ email: lead.email, display_name: lead.name }];
    input.send_invitations = true;
  }

  return {
    toolId: "create_calendar_event",
    input,
    describe: (result) => {
      const out = result as { eventId?: string; deduplicated?: boolean };
      if (out.deduplicated) {
        return `That appointment already existed (${out.eventId}) — I did not create a duplicate.`;
      }
      return out.eventId
        ? `Booked ${resolution.match.name} as event ${out.eventId}.`
        : `Appointment for ${resolution.match.name} is ready for your approval.`;
    },
  };
}
