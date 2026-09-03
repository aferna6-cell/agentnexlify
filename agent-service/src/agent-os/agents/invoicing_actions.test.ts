import { test } from "node:test";
import assert from "node:assert/strict";

import { resolveInvoicingAction } from "./invoicing_actions.ts";
import { extractParams } from "./_extract.ts";
import { readAskIntent } from "./_intent.ts";
import type { SharedContext } from "../types/agent.ts";

const contextBase: SharedContext = {
  businessProfile: { businessName: "Sunset Auto Care" },
  widgetHistory: [],
  pipelineLeads: [],
  pipelineStages: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

function runResolve(ownerAsk: string, ctxOverrides: Partial<SharedContext>) {
  const intent = readAskIntent(ownerAsk);
  const params = extractParams(ownerAsk);
  const context: SharedContext = { ...contextBase, ...ctxOverrides };

  return resolveInvoicingAction({
    ownerAsk,
    params,
    context,
    intent,
  });
}

test("create_invoice_draft: parses “Bill Steve $850 for termite treatment, due in 14 days”", () => {
  const out = runResolve(
    "Bill Steve $850 for termite treatment, due in 14 days.",
    {
      pipelineLeads: [{ id: "lead_steve", name: "Steve", status: "new" }],
      invoices: [],
    },
  );

  assert.ok(out);
  if (!out || !("toolId" in out)) throw new Error("expected tool request");
  assert.equal(out.toolId, "create_invoice_draft");
  assert.equal(out.input.customer_id, "lead_steve");
  assert.deepEqual(out.input.items, [
    { description: "termite treatment", quantity: 1, unit_price: 850 },
  ]);
  assert.equal(out.input.due_in_days, 14);
});

test("send_invoice: matches a single invoice by customer name", () => {
  const out = runResolve("Send the invoice to Steve.", {
    pipelineLeads: [{ id: "lead_steve", name: "Steve", status: "new" }],
    invoices: [
      {
        id: "inv_1",
        customerName: "Steve",
        number: "INV-0001-001",
        amount: 850,
        issuedAt: "2026-08-20",
        dueAt: "2026-09-03",
        status: "sent",
      },
    ],
  });

  assert.ok(out);
  if (!out || !("toolId" in out)) throw new Error("expected tool request");
  assert.equal(out.toolId, "send_invoice");
  assert.deepEqual(out.input, { invoice_id: "inv_1", method: "email" });
});

test("send_invoice_reminder: overdue invoice queues reminder (no guesses)", () => {
  const out = runResolve("Send Steve an overdue invoice reminder.", {
    invoices: [
      {
        id: "inv_2",
        customerName: "Steve",
        number: "INV-0001-009",
        amount: 1200,
        issuedAt: "2026-08-01",
        dueAt: "2026-08-15",
        status: "overdue",
      },
    ],
  });

  assert.ok(out);
  if (!out || !("toolId" in out)) throw new Error("expected tool request");
  assert.equal(out.toolId, "send_invoice_reminder");
  assert.deepEqual(out.input, { invoice_id: "inv_2", method: "email" });
});

test("send_invoice_reminder: paid invoice is no action + clarification, never send_invoice", () => {
  const out = runResolve("Send Steve an overdue invoice reminder.", {
    invoices: [
      {
        id: "inv_paid",
        customerName: "Steve",
        number: "INV-0001-010",
        amount: 850,
        issuedAt: "2026-08-01",
        dueAt: "2026-08-15",
        status: "paid",
      },
    ],
  });

  assert.ok(out);
  if (!out || !("clarify" in out)) throw new Error("expected clarification");
  assert.equal("toolId" in out, false);
  assert.match(out.clarify, /already paid/i);
  assert.doesNotMatch(out.clarify, /queued the invoice send/i);
});

test("send_invoice_reminder: non-overdue invoice is no action + clarification, never send_invoice", () => {
  const out = runResolve("Send Steve an overdue invoice reminder.", {
    invoices: [
      {
        id: "inv_sent",
        customerName: "Steve",
        number: "INV-0001-011",
        amount: 850,
        issuedAt: "2026-09-01",
        dueAt: "2099-01-01",
        status: "sent",
      },
    ],
  });

  assert.ok(out);
  if (!out || !("clarify" in out)) throw new Error("expected clarification");
  assert.equal("toolId" in out, false);
  assert.match(out.clarify, /isn't overdue/i);
  assert.doesNotMatch(out.clarify, /queued the invoice send/i);
});

test("send_invoice: clarification when multiple invoices match by customer+amount", () => {
  const out = runResolve("Send the invoice to Steve for $850.", {
    invoices: [
      {
        id: "inv_a",
        customerName: "Steve",
        number: "INV-0001-010",
        amount: 850,
        issuedAt: "2026-08-01",
        dueAt: "2026-08-10",
        status: "draft",
      },
      {
        id: "inv_b",
        customerName: "Steve",
        number: "INV-0001-011",
        amount: 850,
        issuedAt: "2026-08-02",
        dueAt: "2026-08-11",
        status: "draft",
      },
    ],
  });

  assert.ok(out);
  if (!out || !("clarify" in out)) throw new Error("expected clarification");
  assert.match(out.clarify, /more than one matching/i);
});

test("send_invoice: clarification when no matching invoice exists", () => {
  const out = runResolve("Send the invoice to Steve.", {
    invoices: [],
  });

  assert.ok(out);
  if (!out || !("clarify" in out)) throw new Error("expected clarification");
  assert.match(out.clarify, /couldn't find an invoice/i);
});

test("create_invoice_draft: clarification when line item text is missing", () => {
  const out = runResolve("Bill Steve $850 due in 14 days.", {
    pipelineLeads: [{ id: "lead_steve", name: "Steve", status: "new" }],
    invoices: [],
  });

  assert.ok(out);
  if (!out || !("clarify" in out)) throw new Error("expected clarification");
  assert.match(out.clarify, /service\/line item|itemize/i);
});
