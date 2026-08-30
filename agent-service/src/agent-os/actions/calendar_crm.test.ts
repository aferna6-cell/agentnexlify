/**
 * Milestone 8 — Calendar + CRM tools through the Action Executor.
 * Flags default OFF; mutations verify via independent read-back; tenant isolation.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

import { executeAction, approveAction } from "./executor.ts";
import {
  CALENDAR_ACTIONS_FLAG,
  CRM_ACTIONS_FLAG,
  calendarActionsEnabled,
  crmActionsEnabled,
} from "./flags.ts";
import { evaluateActionPolicy, hasExternalCalendarInvite } from "./policy.ts";
import { createCalendarEvent } from "./tools/create_calendar_event.ts";
import { harness, type Harness } from "./_testkit.ts";

let h: Harness;
const prevCal = process.env[CALENDAR_ACTIONS_FLAG];
const prevCrm = process.env[CRM_ACTIONS_FLAG];

beforeEach(() => {
  h = harness();
  process.env[CALENDAR_ACTIONS_FLAG] = "1";
  process.env[CRM_ACTIONS_FLAG] = "1";
});

afterEach(() => {
  if (prevCal === undefined) delete process.env[CALENDAR_ACTIONS_FLAG];
  else process.env[CALENDAR_ACTIONS_FLAG] = prevCal;
  if (prevCrm === undefined) delete process.env[CRM_ACTIONS_FLAG];
  else process.env[CRM_ACTIONS_FLAG] = prevCrm;
});

function run(toolId: string, input: unknown, accountId = "tenantA") {
  return executeAction({
    accountId,
    agentId: "admin_records",
    runId: "run_m8",
    toolId,
    input,
    sharedContext: h.context,
    registry: h.registry,
  });
}

test("CALENDAR_ACTIONS_ENABLED and CRM_ACTIONS_ENABLED default off", () => {
  delete process.env[CALENDAR_ACTIONS_FLAG];
  delete process.env[CRM_ACTIONS_FLAG];
  assert.equal(calendarActionsEnabled(), false);
  assert.equal(crmActionsEnabled(), false);
});

test("flag off denies calendar tools", async () => {
  delete process.env[CALENDAR_ACTIONS_FLAG];
  const outcome = await run("get_calendar_availability", {
    start: "2026-09-01T14:00:00.000Z",
    end: "2026-09-01T20:00:00.000Z",
    duration_minutes: 60,
  });
  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /CALENDAR_ACTIONS_ENABLED/);
});

test("flag off denies CRM tools", async () => {
  delete process.env[CRM_ACTIONS_FLAG];
  const outcome = await run("get_customer", { customer_id: "lead_1" });
  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /CRM_ACTIONS_ENABLED/);
});

test("get_calendar_availability returns real slots and never invents when empty", async () => {
  h.calendar.seedBusy("tenantA", [
    { start: "2026-09-01T14:00:00.000Z", end: "2026-09-01T20:00:00.000Z" },
  ]);
  const outcome = await run("get_calendar_availability", {
    start: "2026-09-01T14:00:00.000Z",
    end: "2026-09-01T20:00:00.000Z",
    duration_minutes: 60,
    timezone: "America/Phoenix",
  });
  assert.equal(outcome.status, "succeeded");
  const out = outcome.output as {
    available_slots: unknown[];
    busy_intervals: unknown[];
  };
  assert.equal(out.available_slots.length, 0);
  assert.ok(out.busy_intervals.length >= 1);
});

test("get_calendar_availability surfaces provider errors honestly", async () => {
  h.calendar.failAvailabilityWith = "freebusy unavailable";
  const outcome = await run("get_calendar_availability", {
    start: "2026-09-01T14:00:00.000Z",
    end: "2026-09-01T18:00:00.000Z",
    duration_minutes: 30,
  });
  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "calendar_provider_error");
});

test("internal create_calendar_event is L1, verifies, and is idempotent", async () => {
  const input = {
    start: "2026-09-02T18:00:00.000Z",
    end: "2026-09-02T19:00:00.000Z",
    title: "Brake inspection",
    customer_id: "lead_1",
    idempotency_key: "brake-sarah-2026-09-02",
  };
  const first = await run("create_calendar_event", input);
  assert.equal(first.status, "succeeded");
  assert.equal(first.record.riskLevel, 1);
  assert.equal(first.record.verificationState, "passed");
  const out1 = first.output as { eventId: string; deduplicated: boolean };
  assert.equal(out1.deduplicated, false);

  const second = await run("create_calendar_event", input);
  assert.equal(second.status, "succeeded");
  const out2 = second.output as { eventId: string; deduplicated: boolean };
  assert.equal(out2.eventId, out1.eventId);
  assert.equal(out2.deduplicated, true);
  assert.equal(
    h.calendar.allEvents().filter((e) => e.status === "confirmed").length,
    1,
  );
});

test("create with attendees requires approval (L2)", async () => {
  const input = {
    start: "2026-09-03T18:00:00.000Z",
    end: "2026-09-03T19:00:00.000Z",
    title: "Brake inspection",
    attendees: [{ email: "sarah@example.com" }],
    send_invitations: true,
  };
  assert.equal(hasExternalCalendarInvite(input), true);
  const evaluation = evaluateActionPolicy(createCalendarEvent, input, {
    accountId: "tenantA",
    agentId: "admin_records",
  });
  assert.equal(evaluation.decision, "requires_approval");
  assert.equal(evaluation.riskLevel, 2);

  const outcome = await run("create_calendar_event", input);
  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.riskLevel, 2);
  assert.equal(h.calendar.allEvents().length, 0);
});

test("approved invite create runs once and verifies", async () => {
  const input = {
    start: "2026-09-04T18:00:00.000Z",
    end: "2026-09-04T19:00:00.000Z",
    title: "Oil change",
    attendees: [{ email: "mike@example.com", display_name: "Mike" }],
    customer_id: "lead_2",
    send_invitations: true,
    idempotency_key: "oil-mike-once",
  };
  const parked = await run("create_calendar_event", input);
  assert.equal(parked.status, "pending_approval");

  const approved = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(approved.status, "succeeded");
  assert.equal(approved.record.verificationState, "passed");

  const again = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(again.status, "succeeded");
  assert.equal(
    h.calendar.allEvents().filter((e) => e.title === "Oil change").length,
    1,
  );
});

test("cross-tenant customer_id on create fails closed", async () => {
  const outcome = await run("create_calendar_event", {
    start: "2026-09-05T18:00:00.000Z",
    end: "2026-09-05T19:00:00.000Z",
    title: "Stolen booking",
    customer_id: "other_tenant_lead",
  });
  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "customer_not_found");
});

test("cross-tenant event_id on cancel fails closed", async () => {
  h.calendar.seedEvent({
    id: "evt_foreign",
    accountId: "tenantB",
    start: "2026-09-06T18:00:00.000Z",
    end: "2026-09-06T19:00:00.000Z",
    timezone: "America/Phoenix",
    title: "Foreign",
    attendees: [],
    sendInvitations: false,
    status: "confirmed",
    provider: "in_memory_calendar",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });
  const outcome = await run("cancel_calendar_event", {
    event_id: "evt_foreign",
  });
  assert.equal(outcome.status, "pending_approval");
  const approved = await approveAction({
    accountId: "tenantA",
    executionId: outcome.executionId,
    approvedBy: "owner",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(approved.status, "failed");
  assert.equal(approved.record.error?.code, "event_not_found");
});

test("search_customers returns multiple for two Mikes — never picks first", async () => {
  const outcome = await run("search_customers", { query: "Mike" });
  assert.equal(outcome.status, "succeeded");
  const out = outcome.output as { kind: string; matches?: unknown[] };
  assert.equal(out.kind, "multiple");
  assert.ok((out.matches?.length ?? 0) >= 2);
});

test("get_customer is tenant scoped", async () => {
  const ok = await run("get_customer", { customer_id: "lead_1" });
  assert.equal(ok.status, "succeeded");
  const bad = await run("get_customer", { customer_id: "lead_foreign" });
  assert.equal(bad.status, "failed");
  assert.equal(bad.record.error?.code, "customer_not_found");
});

test("update_customer preserves unspecified fields and verifies", async () => {
  const outcome = await run("update_customer", {
    customer_id: "lead_1",
    fields: { phone: "(602) 555-0100" },
  });
  assert.equal(outcome.status, "succeeded");
  assert.equal(outcome.record.verificationState, "passed");
  const out = outcome.output as {
    phone?: string;
    email?: string;
    updatedFields: string[];
  };
  assert.equal(out.phone, "(602) 555-0100");
  assert.equal(out.email, "sarah@example.com");
  assert.deepEqual(out.updatedFields, ["phone"]);
});

test("update_lead_stage rejects invalid free-text stages", async () => {
  const bad = await run("update_lead_stage", {
    customer_id: "lead_2",
    status: " vibing ",
  });
  assert.equal(bad.status, "failed");
  assert.equal(bad.record.error?.code, "invalid_lead_stage");

  const ok = await run("update_lead_stage", {
    customer_id: "lead_2",
    status: "appointment_booked",
  });
  assert.equal(ok.status, "succeeded");
  assert.equal(ok.record.verificationState, "passed");
});

test("create_customer is duplicate-aware on email", async () => {
  const first = await run("create_customer", {
    name: "Dana Whitfield",
    email: "dana@example.com",
  });
  assert.equal(first.status, "succeeded");
  const out1 = first.output as { customerId: string; deduplicated: boolean };
  assert.equal(out1.deduplicated, false);

  const second = await run("create_customer", {
    name: "Dana W",
    email: "dana@example.com",
  });
  assert.equal(second.status, "succeeded");
  const out2 = second.output as { customerId: string; deduplicated: boolean };
  assert.equal(out2.customerId, out1.customerId);
  assert.equal(out2.deduplicated, true);
});

test("add_customer_note remains ungated by CRM_ACTIONS_ENABLED", async () => {
  delete process.env[CRM_ACTIONS_FLAG];
  const outcome = await run("add_customer_note", {
    customer_id: "lead_1",
    note: "Prefers morning appointments",
  });
  assert.equal(outcome.status, "succeeded");
});
