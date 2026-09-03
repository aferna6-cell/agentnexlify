/**
 * Test helpers for the action layer: a clean store + ports per test, a minimal
 * SharedContext, and small fixture tools at each risk level.
 *
 * Fixture tools live here rather than in the registry on purpose: the shipped
 * registry must only contain tools that genuinely work, so the level-2 and
 * level-3 cases — which have no real integration yet — are exercised with
 * test-only doubles instead of fake "send email" tools.
 */

import { z } from "zod";
import { defineTool } from "./define-tool.ts";
import {
  InMemoryCalendarPort,
  InMemoryCrmPort,
  InMemoryCustomerNotesPort,
  InMemoryInvoicePort,
  setToolPorts,
  type ToolPorts,
} from "./ports.ts";
import { InMemoryActionStore, setActionStore } from "./store.ts";
import { ToolRegistry } from "./registry.ts";
import { resetToolPolicyProvider } from "./policy.ts";
import { getBusinessProfile } from "./tools/get_business_profile.ts";
import { addCustomerNote } from "./tools/add_customer_note.ts";
import { getCalendarAvailability } from "./tools/get_calendar_availability.ts";
import { createCalendarEvent } from "./tools/create_calendar_event.ts";
import { rescheduleCalendarEvent } from "./tools/reschedule_calendar_event.ts";
import { cancelCalendarEvent } from "./tools/cancel_calendar_event.ts";
import { getCustomer } from "./tools/get_customer.ts";
import { searchCustomers } from "./tools/search_customers.ts";
import { updateCustomer } from "./tools/update_customer.ts";
import { createCustomer } from "./tools/create_customer.ts";
import { updateLeadStage } from "./tools/update_lead_stage.ts";
import { listOverdueInvoices } from "./tools/list_overdue_invoices.ts";
import { getInvoice } from "./tools/get_invoice.ts";
import { createInvoiceDraft } from "./tools/create_invoice_draft.ts";
import { sendInvoice } from "./tools/send_invoice.ts";
import { sendInvoiceReminder } from "./tools/send_invoice_reminder.ts";
import type { SharedContext } from "../types/agent.ts";

export interface Harness {
  store: InMemoryActionStore;
  ports: ToolPorts;
  notes: InMemoryCustomerNotesPort;
  calendar: InMemoryCalendarPort;
  crm: InMemoryCrmPort;
  invoices: InMemoryInvoicePort;
  registry: ToolRegistry;
  context: SharedContext;
  /** How many times each fixture tool body actually ran. */
  calls: Record<string, number>;
}

export function sampleContext(
  overrides: Partial<SharedContext> = {},
): SharedContext {
  return {
    businessProfile: {
      businessName: "Sunset Auto Care",
      ownerName: "Maya",
      city: "Phoenix",
      state: "AZ",
      phone: "(602) 555-0148",
      timezone: "America/Phoenix",
    },
    widgetHistory: [],
    pipelineLeads: [
      {
        id: "lead_1",
        name: "Sarah Chen",
        status: "quoted",
        subject: "brake job",
        quoteAmount: 640,
        email: "sarah@example.com",
      },
      {
        id: "lead_2",
        name: "Mike Johnson",
        status: "new",
        subject: "tire rotation",
        phone: "(602) 555-0199",
      },
      {
        id: "lead_3",
        name: "Mike Rivera",
        status: "contacted",
        subject: "oil change",
      },
    ],
    pipelineStages: [
      "new",
      "contacted",
      "appointment_booked",
      "closed",
      "lost",
      "quoted",
    ],
    appointments: [],
    invoices: [],
    agentRunHistory: [],
    kb: [],
    ...overrides,
  };
}

/** Fresh store + ports + registry, registered globally for the test. */
export function harness(): Harness {
  const store = new InMemoryActionStore();
  const notes = new InMemoryCustomerNotesPort();
  const calendar = new InMemoryCalendarPort();
  const crm = new InMemoryCrmPort();
  const invoices = new InMemoryInvoicePort();
  // Seed CRM from sample pipeline so mutations have writable targets.
  for (const lead of sampleContext().pipelineLeads) {
    crm.seed({
      id: lead.id,
      accountId: "tenantA",
      name: lead.name,
      status: lead.status,
      email: lead.email,
      phone: lead.phone,
      subject: lead.subject,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }
  const ports: ToolPorts = { customerNotes: notes, calendar, crm, invoices };
  setActionStore(store);
  setToolPorts(ports);
  resetToolPolicyProvider();

  const calls: Record<string, number> = {};
  const registry = new ToolRegistry();
  registry.register(getBusinessProfile);
  registry.register(addCustomerNote);
  registry.register(getCalendarAvailability);
  registry.register(createCalendarEvent);
  registry.register(rescheduleCalendarEvent);
  registry.register(cancelCalendarEvent);
  registry.register(getCustomer);
  registry.register(searchCustomers);
  registry.register(updateCustomer);
  registry.register(createCustomer);
  registry.register(updateLeadStage);
  registry.register(listOverdueInvoices);
  registry.register(getInvoice);
  registry.register(createInvoiceDraft);
  registry.register(sendInvoice);
  registry.register(sendInvoiceReminder);
  for (const tool of fixtureTools(calls)) registry.register(tool);

  return {
    store,
    ports,
    notes,
    calendar,
    crm,
    invoices,
    registry,
    context: sampleContext(),
    calls,
  };
}

/** Test-only tools covering the paths the shipped registry has no real tool for. */
export function fixtureTools(calls: Record<string, number>) {
  const bump = (id: string) => {
    calls[id] = (calls[id] ?? 0) + 1;
  };

  /** Level 2: stands in for a future "send email" style action. */
  const externalMessage = defineTool({
    id: "fixture_external_message",
    displayName: "Fixture external message",
    description: "Test double for an external communication action.",
    riskLevel: 2,
    mutating: true,
    requiresApproval: true,
    inputSchema: z.object({ to: z.string().min(1), body: z.string().min(1) }),
    outputSchema: z.object({ deliveredTo: z.string() }),
    async execute({ input, context }) {
      bump("fixture_external_message");
      context.declareEffect({ port: "fixture", durable: false });
      return { deliveredTo: input.to };
    },
  });

  /** Level 3: stands in for a future refund/charge style action. */
  const highImpact = defineTool({
    id: "fixture_high_impact",
    displayName: "Fixture high impact",
    description: "Test double for a financial or destructive action.",
    riskLevel: 3,
    mutating: true,
    requiresApproval: true,
    inputSchema: z.object({ amount: z.number().positive() }),
    outputSchema: z.object({ amount: z.number() }),
    async execute({ input }) {
      bump("fixture_high_impact");
      return { amount: input.amount };
    },
  });

  /** Always throws — the failure-persistence path. */
  const alwaysFails = defineTool({
    id: "fixture_always_fails",
    displayName: "Fixture always fails",
    description: "Test double whose body always throws.",
    riskLevel: 1,
    mutating: true,
    requiresApproval: false,
    inputSchema: z.object({}),
    outputSchema: z.object({ ok: z.boolean() }),
    async execute() {
      bump("fixture_always_fails");
      throw new Error("upstream exploded");
    },
  });

  /** Runs fine, then fails verification — the "ran but did not land" path. */
  const failsVerification = defineTool({
    id: "fixture_fails_verification",
    displayName: "Fixture fails verification",
    description: "Test double that succeeds but cannot be verified.",
    riskLevel: 1,
    mutating: true,
    requiresApproval: false,
    inputSchema: z.object({}),
    outputSchema: z.object({ ok: z.boolean() }),
    async execute() {
      bump("fixture_fails_verification");
      return { ok: true };
    },
    async verify() {
      return {
        verified: false,
        detail: "the record was not found when read back",
      };
    },
  });

  /** Read-only, and takes a secret-looking field to prove redaction. */
  const readOnlyEcho = defineTool({
    id: "fixture_read_only",
    displayName: "Fixture read only",
    description: "Test double for a level-0 read.",
    riskLevel: 0,
    mutating: false,
    requiresApproval: false,
    inputSchema: z.object({
      query: z.string(),
      api_key: z.string().optional(),
    }),
    outputSchema: z.object({ query: z.string() }),
    async execute({ input }) {
      bump("fixture_read_only");
      return { query: input.query };
    },
  });

  return [
    externalMessage,
    highImpact,
    alwaysFails,
    failsVerification,
    readOnlyEcho,
  ];
}
