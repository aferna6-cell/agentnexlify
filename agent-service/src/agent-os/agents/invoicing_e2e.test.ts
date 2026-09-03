/**
 * Billing Automation PR3 — Agent OS invoicing routing E2E.
 *
 * Runs the Invoicing department the way the orchestrator does (resolveAction
 * → executeAction). Proves create preserves the exact payload, send parks
 * with no pre-approval effect, overdue reminders queue, paid/non-overdue
 * reminder asks propose neither send_invoice_reminder nor send_invoice, and
 * tenant isolation holds on the invoice port.
 */

import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

import { executeAction } from "../actions/executor.ts";
import { INVOICE_ACTIONS_FLAG } from "../actions/flags.ts";
import { harness, type Harness } from "../actions/_testkit.ts";
import { invoicing } from "./departments.ts";
import { extractParams } from "./_extract.ts";
import { fakeEmitter } from "./_testkit.ts";
import type { SharedContext, InvoiceData } from "../types/agent.ts";

let h: Harness;
const prevFlag = process.env[INVOICE_ACTIONS_FLAG];

const STEVE_LEAD = {
  id: "lead_steve",
  name: "Steve",
  status: "new" as const,
  email: "steve@example.com",
};

const CREATE_ASK = "Bill Steve $850 for termite treatment, due in 14 days.";
const SEND_ASK = "Send the invoice to Steve.";
const REMIND_ASK = "Send Steve an overdue invoice reminder.";

beforeEach(() => {
  h = harness();
  process.env[INVOICE_ACTIONS_FLAG] = "1";
  h.crm.seed({
    id: STEVE_LEAD.id,
    accountId: "tenantA",
    name: STEVE_LEAD.name,
    status: STEVE_LEAD.status,
    email: STEVE_LEAD.email,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });
});

afterEach(() => {
  if (prevFlag === undefined) delete process.env[INVOICE_ACTIONS_FLAG];
  else process.env[INVOICE_ACTIONS_FLAG] = prevFlag;
});

function context(invoices: InvoiceData[] = []): SharedContext {
  return {
    ...h.context,
    pipelineLeads: [STEVE_LEAD, ...h.context.pipelineLeads],
    invoices,
  };
}

async function runInvoicing(ownerAsk: string, ctx: SharedContext) {
  const { emitter } = fakeEmitter();
  return invoicing.run({
    input: extractParams(ownerAsk),
    context: ctx,
    emitTrace: emitter,
    ownerAsk,
    runId: "run_invoice_e2e",
    userId: "tenantA",
  });
}

function countInvoiceTools(
  rows: { toolId: string; input: Record<string, unknown> }[],
  toolId: string,
  invoiceId: string,
): number {
  return rows.filter(
    (r) => r.toolId === toolId && r.input.invoice_id === invoiceId,
  ).length;
}

function dueIn14Days(): string {
  const due = new Date();
  due.setUTCDate(due.getUTCDate() + 14);
  return due.toISOString().slice(0, 10);
}

test("department create → exact payload → send parks with no pre-approval effect", async () => {
  const created = await runInvoicing(CREATE_ASK, context());
  assert.equal(created.needsClarification, undefined);
  assert.match(created.orchestratorNotes?.[0] ?? "", /draft invoice/i);

  const drafts = h.invoices.allInvoices();
  assert.equal(drafts.length, 1);
  const draft = drafts[0]!;
  assert.equal(draft.customerId, STEVE_LEAD.id);
  assert.equal(draft.total, 850);
  assert.equal(draft.items[0]?.description, "termite treatment");
  assert.equal(draft.items[0]?.quantity, 1);
  assert.equal(draft.items[0]?.unitPrice, 850);
  assert.equal(draft.status, "draft");
  assert.equal(draft.dueDate, dueIn14Days());
  assert.equal(draft.paymentLink, undefined);

  const createRows = await h.store.list({ accountId: "tenantA" });
  assert.equal(createRows.length, 1);
  assert.equal(createRows[0]?.toolId, "create_invoice_draft");
  assert.equal(createRows[0]?.status, "succeeded");
  assert.deepEqual(createRows[0]?.input, {
    customer_id: STEVE_LEAD.id,
    items: [{ description: "termite treatment", quantity: 1, unit_price: 850 }],
    tax_rate: 0,
    due_in_days: 14,
  });

  const sendTurn = await runInvoicing(
    SEND_ASK,
    context([
      {
        id: draft.id,
        customerName: "Steve",
        number: draft.invoiceNumber,
        amount: draft.total,
        issuedAt: draft.createdAt.slice(0, 10),
        dueAt: draft.dueDate ?? "",
        status: "draft",
      },
    ]),
  );
  assert.match(sendTurn.orchestratorNotes?.[0] ?? "", /approve/i);

  const afterPark = h.invoices.allInvoices();
  assert.equal(afterPark.length, 1);
  assert.equal(afterPark[0]?.status, "draft");
  assert.equal(afterPark[0]?.paymentLink, undefined);

  const rows = await h.store.list({ accountId: "tenantA" });
  const parked = rows.find((r) => r.toolId === "send_invoice");
  assert.ok(parked);
  assert.equal(parked.status, "pending_approval");
  assert.equal(parked.approvalState, "pending");
  assert.deepEqual(parked.input, { invoice_id: draft.id, method: "email" });
});

test("overdue reminder parks; paid and non-overdue reminder asks propose no action", async () => {
  const overdueCtx = context([
    {
      id: "inv_overdue",
      customerName: "Steve",
      number: "INV-0001-009",
      amount: 850,
      issuedAt: "2026-08-01",
      dueAt: "2026-08-15",
      status: "overdue",
    },
  ]);
  const reminder = await runInvoicing(REMIND_ASK, overdueCtx);
  assert.match(
    reminder.orchestratorNotes?.[0] ?? "",
    /overdue invoice reminder/i,
  );
  const parked = (await h.store.list({ accountId: "tenantA" })).find(
    (r) => r.toolId === "send_invoice_reminder",
  );
  assert.ok(parked);
  assert.equal(parked.status, "pending_approval");
  assert.deepEqual(parked.input, {
    invoice_id: "inv_overdue",
    method: "email",
  });

  const paid = await runInvoicing(
    REMIND_ASK,
    context([
      {
        id: "inv_paid",
        customerName: "Steve",
        number: "INV-0001-010",
        amount: 850,
        issuedAt: "2026-08-01",
        dueAt: "2026-08-15",
        status: "paid",
      },
    ]),
  );
  const paidRows = await h.store.list({ accountId: "tenantA" });
  assert.equal(
    countInvoiceTools(paidRows, "send_invoice_reminder", "inv_paid"),
    0,
  );
  assert.equal(countInvoiceTools(paidRows, "send_invoice", "inv_paid"), 0);
  assert.equal(paid.needsClarification, true);
  assert.match(paid.orchestratorNotes?.[0] ?? "", /already paid/i);
  assert.doesNotMatch(
    paid.orchestratorNotes?.[0] ?? "",
    /queued the invoice send/i,
  );

  const notDue = await runInvoicing(
    REMIND_ASK,
    context([
      {
        id: "inv_sent",
        customerName: "Steve",
        number: "INV-0001-011",
        amount: 850,
        issuedAt: "2026-09-01",
        dueAt: "2099-01-01",
        status: "sent",
      },
    ]),
  );
  const later = await h.store.list({ accountId: "tenantA" });
  assert.equal(
    countInvoiceTools(later, "send_invoice_reminder", "inv_sent"),
    0,
  );
  assert.equal(countInvoiceTools(later, "send_invoice", "inv_sent"), 0);
  assert.equal(notDue.needsClarification, true);
  assert.match(notDue.orchestratorNotes?.[0] ?? "", /isn't overdue/i);
  assert.doesNotMatch(
    notDue.orchestratorNotes?.[0] ?? "",
    /queued the invoice send/i,
  );
});

test("tenant isolation: other account cannot read or send this invoice", async () => {
  await runInvoicing(CREATE_ASK, context());
  const draft = h.invoices.allInvoices()[0]!;
  assert.equal(draft.accountId, "tenantA");

  const missing = await executeAction({
    accountId: "tenantB",
    agentId: "invoicing",
    runId: "run_other",
    toolId: "get_invoice",
    input: { invoice_id: draft.id },
    sharedContext: context(),
    registry: h.registry,
  });
  assert.equal(missing.status, "failed");
  assert.equal(missing.record.error?.code, "invoice_not_found");

  const send = await executeAction({
    accountId: "tenantB",
    agentId: "invoicing",
    runId: "run_other",
    toolId: "send_invoice",
    input: { invoice_id: draft.id, method: "email" },
    sharedContext: context(),
    registry: h.registry,
  });
  assert.equal(send.status, "pending_approval");
  assert.deepEqual(send.record.input, {
    invoice_id: draft.id,
    method: "email",
  });
  assert.equal(h.invoices.allInvoices()[0]?.status, "draft");
  assert.equal(h.invoices.allInvoices()[0]?.accountId, "tenantA");
});
