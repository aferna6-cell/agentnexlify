/**
 * Seed Collecting calendar/CRM ports from SharedContext so L0 reads and
 * entity resolution see tenant data — never another account's rows.
 */

import type { SharedContext } from "../agent-os/types/agent.ts";
import type {
  CollectingCalendarPort,
  CollectingCrmPort,
} from "./action-collector.ts";

export function seedActionPortsFromContext(
  accountId: string,
  context: SharedContext,
  calendar: CollectingCalendarPort,
  crm: CollectingCrmPort,
): void {
  const busy = [...(context.calendarBusy ?? [])];
  for (const a of context.appointments ?? []) {
    const start = a.scheduledFor;
    const end = a.scheduledEnd;
    if (start && end && (a.status || "").toLowerCase() !== "cancelled") {
      busy.push({ start, end });
      calendar.seedExistingEvent({
        id: a.id,
        accountId,
        start,
        end,
        timezone: context.businessProfile?.timezone || "America/New_York",
        title: a.service || `Appointment with ${a.customerName}`,
        attendees: [],
        sendInvitations: false,
        status: "confirmed",
        provider: "shared_context",
        providerEventId: a.googleEventId,
        createdAt: start,
        updatedAt: start,
      });
    }
  }

  if (context.calendarAvailabilityError) {
    calendar.markAvailabilityError(context.calendarAvailabilityError);
  } else {
    calendar.seedBusyForAccount(accountId, busy);
  }

  const now = new Date().toISOString();
  for (const lead of context.pipelineLeads ?? []) {
    crm.seedCustomer({
      id: lead.id,
      accountId,
      name: lead.name,
      status: lead.status,
      email: lead.email,
      phone: lead.phone,
      address: lead.address,
      subject: lead.subject,
      createdAt: lead.lastContactDate || now,
      updatedAt: lead.lastContactDate || now,
    });
  }
}
