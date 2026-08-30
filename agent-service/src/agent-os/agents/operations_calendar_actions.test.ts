/**
 * Unit tests for Operations calendar resolveAction (flag-gated).
 */

import { test, afterEach } from "node:test";
import assert from "node:assert/strict";

import { resolveCalendarAction } from "./operations_calendar_actions.ts";
import { CALENDAR_ACTIONS_FLAG } from "../actions/flags.ts";
import { readAskIntent } from "./_intent.ts";
import type { SharedContext } from "../types/agent.ts";

const prev = process.env[CALENDAR_ACTIONS_FLAG];

afterEach(() => {
  if (prev === undefined) delete process.env[CALENDAR_ACTIONS_FLAG];
  else process.env[CALENDAR_ACTIONS_FLAG] = prev;
});

const context: SharedContext = {
  businessProfile: {
    businessName: "Sunset Auto Care",
    timezone: "America/Phoenix",
  },
  widgetHistory: [],
  pipelineLeads: [
    {
      id: "lead_1",
      name: "Sarah Chen",
      status: "quoted",
      email: "sarah@example.com",
    },
    { id: "lead_2", name: "Mike Johnson", status: "new" },
    { id: "lead_3", name: "Mike Rivera", status: "contacted" },
  ],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

test("calendar resolver is inert when flag is off", () => {
  delete process.env[CALENDAR_ACTIONS_FLAG];
  const ask = "Book Sarah Chen tomorrow";
  const out = resolveCalendarAction({
    ownerAsk: ask,
    params: { customer_name: "Sarah Chen" },
    context,
    intent: readAskIntent(ask),
  });
  assert.equal(out, undefined);
});

test("ambiguous Mike clarifies when flag is on", () => {
  process.env[CALENDAR_ACTIONS_FLAG] = "1";
  const ask =
    "Book Mike tomorrow at 2026-09-02T18:00:00.000Z to 2026-09-02T19:00:00.000Z";
  const out = resolveCalendarAction({
    ownerAsk: ask,
    params: { customer_name: "Mike" },
    context,
    intent: readAskIntent(ask),
  });
  assert.ok(out && "clarify" in out);
  assert.match((out as { clarify: string }).clarify, /more than one/i);
});

test("draft-only ask uses availability, not create", () => {
  process.env[CALENDAR_ACTIONS_FLAG] = "1";
  const ask = "Find a time I could offer Sarah — don't book yet";
  const out = resolveCalendarAction({
    ownerAsk: ask,
    params: { customer_name: "Sarah Chen" },
    context,
    intent: readAskIntent(ask),
  });
  assert.ok(out && "toolId" in out);
  assert.equal((out as { toolId: string }).toolId, "get_calendar_availability");
});

test("cancel without event id clarifies", () => {
  process.env[CALENDAR_ACTIONS_FLAG] = "1";
  const ask = "Cancel Sarah's appointment";
  const out = resolveCalendarAction({
    ownerAsk: ask,
    params: { customer_name: "Sarah Chen" },
    context,
    intent: readAskIntent(ask),
  });
  assert.ok(out && "clarify" in out);
  assert.match((out as { clarify: string }).clarify, /event id/i);
});
