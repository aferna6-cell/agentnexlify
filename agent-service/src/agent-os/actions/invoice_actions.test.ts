/**
 * Billing Automation v1 — invoice Action Executor tools.
 * Flag defaults OFF. L0 reads, L1 draft, L2 send/reminder park for approval.
 * Engine never sends. Customer/amount preserved. Never guess. Never mark paid.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

import { executeAction, approveAction } from "./executor.ts";
import { evaluateActionPolicy } from "./policy.ts";
import { toolRegistry } from "./registry.ts";
import {
  INVOICE_ACTIONS_FLAG,
  invoiceActionsEnabled,
  isInvoiceToolId,
} from "./flags.ts";
import { sendInvoice } from "./tools/send_invoice.ts";
import { sendInvoiceReminder } from "./tools/send_invoice_reminder.ts";
import { harness, type Harness } from "./_testkit.ts";

let h: Harness;
const prevFlag = process.env[INVOICE_ACTIONS_FLAG];

beforeEach(() => {
  h = harness();
  process.env[INVOICE_ACTIONS_FLAG] = "1";
});

afterEach(() => {
  if (prevFlag === undefined) delete process.env[INVOICE_ACTIONS_FLAG];
  else process.env[INVOICE_ACTIONS_FLAG] = prevFlag;
});

function run(toolId: string, input: unknown, accountId = "tenantA") {
  return executeAction({
    accountId,
    agentId: "invoicing",
    runId: "run_inv",
    toolId,
    input,
    sharedContext: h.context,
    registry: h.registry,
  });
}

const termiteItems = [
  { description: "Termite treatment", quantity: 1, unit_price: 850 },
];

test("INVOICE_ACTIONS_ENABLED defaults off", () => {
  delete process.env[INVOICE_ACTIONS_FLAG];
  assert.equal(invoiceActionsEnabled(), false);
  process.env[INVOICE_ACTIONS_FLAG] = "0";
  assert.equal(invoiceActionsEnabled(), false);
  process.env[INVOICE_ACTIONS_FLAG] = "false";
  assert.equal(invoiceActionsEnabled(), false);
});

test("invoice tools are registered with expected risk", () => {
  assert.equal(toolRegistry.find("list_overdue_invoices")?.riskLevel, 0);
  assert.equal(toolRegistry.find("get_invoice")?.riskLevel, 0);
  assert.equal(toolRegistry.find("create_invoice_draft")?.riskLevel, 1);
  assert.equal(toolRegistry.find("send_invoice")?.riskLevel, 2);
  assert.equal(toolRegistry.find("send_invoice")?.requiresApproval, true);
  assert.equal(toolRegistry.find("send_invoice_reminder")?.riskLevel, 2);
  assert.equal(
    toolRegistry.find("send_invoice_reminder")?.requiresApproval,
    true,
  );
  assert.equal(toolRegistry.find("send_invoice")?.department, "invoicing");
  assert.equal(isInvoiceToolId("send_invoice"), true);
  assert.equal(isInvoiceToolId("send_email"), false);
  assert.equal(toolRegistry.find("mark_invoice_paid"), null);
});

test("flag off denies every invoice tool", async () => {
  delete process.env[INVOICE_ACTIONS_FLAG];
  const outcome = await run("list_overdue_invoices", {});
  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /INVOICE_ACTIONS_ENABLED/);
});

test("list_overdue_invoices is L0, tenant scoped, and excludes paid", async () => {
  const now = new Date().toISOString();
  h.invoices.seed({
    id: "inv_overdue",
    accountId: "tenantA",
    customerId: "lead_1",
    customerName: "Sarah Chen",
    invoiceNumber: "INV-104",
    items: [{ description: "Termite treatment", quantity: 1, unitPrice: 850 }],
    subtotal: 850,
    taxRate: 0,
    taxAmount: 0,
    total: 850,
    status: "overdue",
    dueDate: "2026-08-20",
    createdAt: now,
    updatedAt: now,
  });
  h.invoices.seed({
    id: "inv_paid",
    accountId: "tenantA",
    customerId: "lead_1",
    customerName: "Sarah Chen",
    invoiceNumber: "INV-105",
    items: [{ description: "Paid job", quantity: 1, unitPrice: 100 }],
    subtotal: 100,
    taxRate: 0,
    taxAmount: 0,
    total: 100,
    status: "paid",
    dueDate: "2026-08-01",
    paidAt: now,
    createdAt: now,
    updatedAt: now,
  });
  h.invoices.seed({
    id: "inv_other_tenant",
    accountId: "tenantB",
    customerId: "lead_x",
    invoiceNumber: "INV-999",
    items: [{ description: "Foreign", quantity: 1, unitPrice: 1 }],
    subtotal: 1,
    taxRate: 0,
    taxAmount: 0,
    total: 1,
    status: "overdue",
    dueDate: "2026-08-01",
    createdAt: now,
    updatedAt: now,
  });

  const outcome = await run("list_overdue_invoices", {});
  assert.equal(outcome.status, "succeeded");
  const out = outcome.output as {
    invoices: { invoiceId: string; total: number }[];
    count: number;
  };
  assert.equal(out.count, 1);
  assert.equal(out.invoices[0]?.invoiceId, "inv_overdue");
  assert.equal(out.invoices[0]?.total, 850);
});

test("get_invoice is tenant scoped and reports stored payment state", async () => {
  const now = new Date().toISOString();
  h.invoices.seed({
    id: "inv_104",
    accountId: "tenantA",
    customerId: "lead_1",
    customerName: "Sarah Chen",
    invoiceNumber: "INV-104",
    items: [{ description: "Termite treatment", quantity: 1, unitPrice: 850 }],
    subtotal: 850,
    taxRate: 0,
    taxAmount: 0,
    total: 850,
    status: "sent",
    dueDate: "2026-09-17",
    createdAt: now,
    updatedAt: now,
  });

  const ok = await run("get_invoice", { invoice_id: "inv_104" });
  assert.equal(ok.status, "succeeded");
  const out = ok.output as {
    total: number;
    paymentConfirmed: boolean;
    items: { description: string }[];
  };
  assert.equal(out.total, 850);
  assert.equal(out.paymentConfirmed, false);
  assert.equal(out.items[0]?.description, "Termite treatment");

  const missing = await run("get_invoice", { invoice_id: "inv_other" });
  assert.equal(missing.status, "failed");
  assert.equal(missing.record.error?.code, "invoice_not_found");

  const cross = await run("get_invoice", { invoice_id: "inv_104" }, "tenantB");
  assert.equal(cross.status, "failed");
  assert.equal(cross.record.error?.code, "invoice_not_found");
});

test("create_invoice_draft preserves customer, amount, line items and verifies", async () => {
  const outcome = await run("create_invoice_draft", {
    customer_id: "lead_1",
    items: termiteItems,
    due_in_days: 14,
    notes: "Termite treatment",
    idempotency_key: "steve-termite-850",
  });
  assert.equal(outcome.status, "succeeded");
  assert.equal(outcome.record.riskLevel, 1);
  assert.equal(outcome.record.verificationState, "passed");
  const out = outcome.output as {
    customerId: string;
    total: number;
    items: { description: string; unit_price: number }[];
    status: string;
    deduplicated: boolean;
  };
  assert.equal(out.customerId, "lead_1");
  assert.equal(out.total, 850);
  assert.equal(out.items[0]?.description, "Termite treatment");
  assert.equal(out.items[0]?.unit_price, 850);
  assert.equal(out.status, "draft");
  assert.equal(out.deduplicated, false);
});

test("create_invoice_draft is idempotent on the same fingerprint", async () => {
  const input = {
    customer_id: "lead_1",
    items: termiteItems,
    due_date: "2026-09-17",
    idempotency_key: "termite-sarah-once",
  };
  const first = await run("create_invoice_draft", input);
  const second = await run("create_invoice_draft", input);
  assert.equal(first.status, "succeeded");
  assert.equal(second.status, "succeeded");
  const a = first.output as { invoiceId: string; deduplicated: boolean };
  const b = second.output as { invoiceId: string; deduplicated: boolean };
  assert.equal(a.invoiceId, b.invoiceId);
  assert.equal(b.deduplicated, true);
  assert.equal(h.invoices.allInvoices().length, 1);
});

test("create_invoice_draft never guesses a missing customer", async () => {
  const outcome = await run("create_invoice_draft", {
    customer_id: "lead_unknown",
    items: termiteItems,
  });
  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "customer_not_found");
  assert.equal(h.invoices.allInvoices().length, 0);
});

test("create_invoice_draft never uses a cross-tenant customer", async () => {
  h.crm.seed({
    id: "lead_foreign",
    accountId: "tenantB",
    name: "Steve",
    status: "new",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });
  const outcome = await run("create_invoice_draft", {
    customer_id: "lead_foreign",
    items: termiteItems,
  });
  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "customer_not_found");
});

test("flag on: send_invoice parks at pending_approval and engine does not send", async () => {
  const evaluation = evaluateActionPolicy(
    sendInvoice,
    { invoice_id: "inv_1" },
    {
      accountId: "tenantA",
      agentId: "invoicing",
    },
  );
  assert.equal(evaluation.decision, "requires_approval");
  assert.equal(evaluation.riskLevel, 2);

  const outcome = await run("send_invoice", {
    invoice_id: "inv_1",
    method: "email",
  });
  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.approvalState, "pending");
  await assert.rejects(
    () =>
      sendInvoice.execute({
        input: { invoice_id: "inv_1", method: "email" },
        context: {} as never,
      }),
    (err: Error & { code?: string }) => {
      assert.equal(err.code, "data_plane_only");
      return true;
    },
  );
});

test("flag on: send_invoice_reminder requires approval and is data-plane only", async () => {
  const outcome = await run("send_invoice_reminder", { invoice_id: "inv_104" });
  assert.equal(outcome.status, "pending_approval");
  await assert.rejects(
    () =>
      sendInvoiceReminder.execute({
        input: { invoice_id: "inv_104", method: "email" },
        context: {} as never,
      }),
    (err: Error & { code?: string }) => {
      assert.equal(err.code, "data_plane_only");
      return true;
    },
  );
});

test("second approval of the same send_invoice row does not re-execute", async () => {
  const parked = await run("send_invoice", {
    invoice_id: "inv_1",
    method: "email",
  });
  assert.equal(parked.status, "pending_approval");
  const first = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(first.status, "failed");
  assert.equal(first.record.error?.code, "data_plane_only");

  const again = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.notEqual(again.status, "succeeded");
});
