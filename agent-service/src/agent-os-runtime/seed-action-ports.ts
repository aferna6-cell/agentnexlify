/**
 * Seed Collecting calendar/CRM ports from SharedContext so L0 reads and
 * entity resolution see tenant data — never another account's rows.
 */

import type { SharedContext } from "../agent-os/types/agent.ts";
import type {
  CollectingCalendarPort,
  CollectingCrmPort,
  CollectingInvoicePort,
} from "./action-collector.ts";

export function seedActionPortsFromContext(
  accountId: string,
  context: SharedContext,
  calendar: CollectingCalendarPort,
  crm: CollectingCrmPort,
  invoices?: CollectingInvoicePort,
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

  if (!invoices) return;
  const leadByName = new Map(
    (context.pipelineLeads ?? []).map((l) => [l.name.trim().toLowerCase(), l]),
  );
  for (const inv of context.invoices ?? []) {
    const lead = leadByName.get((inv.customerName || "").trim().toLowerCase());
    invoices.seedInvoice({
      id: inv.id,
      accountId,
      customerId: lead?.id || "",
      customerName: inv.customerName,
      invoiceNumber: inv.number,
      items: [
        {
          description: inv.customerName ? `Invoice ${inv.number}` : "Invoice",
          quantity: 1,
          unitPrice: inv.amount,
        },
      ],
      subtotal: inv.amount,
      taxRate: 0,
      taxAmount: 0,
      total: inv.amount,
      status: (inv.status || "draft") as
        "draft" | "sent" | "viewed" | "paid" | "overdue" | "cancelled",
      dueDate: inv.dueAt,
      createdAt: inv.issuedAt || now,
      updatedAt: inv.issuedAt || now,
    });
  }
}
