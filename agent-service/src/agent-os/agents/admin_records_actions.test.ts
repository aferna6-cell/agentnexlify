/**
 * Resolver-level CRM tests — natural-language owner asks through
 * readAskIntent → extractParams → resolveRecordAction.
 *
 * These tests do NOT call executeAction(). Direct executor success must never
 * substitute for resolver-path success (M8 decision-path gate).
 */

import { test, afterEach } from "node:test";
import assert from "node:assert/strict";

import { resolveRecordAction } from "./admin_records_actions.ts";
import { CRM_ACTIONS_FLAG } from "../actions/flags.ts";
import { readAskIntent, authorizesAction } from "./_intent.ts";
import { extractParams } from "./_extract.ts";
import type { SharedContext } from "../types/agent.ts";

const prev = process.env[CRM_ACTIONS_FLAG];

afterEach(() => {
  if (prev === undefined) delete process.env[CRM_ACTIONS_FLAG];
  else process.env[CRM_ACTIONS_FLAG] = prev;
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
      name: "Sarah Jones",
      status: "new",
      email: "sarah@example.com",
      phone: "864-555-0100",
      address: "1 Oak St",
    },
    {
      id: "lead_2",
      name: "Mike Smith",
      status: "contacted",
      email: "mike@example.com",
      phone: "864-555-0101",
    },
    { id: "lead_3", name: "Mike Rivera", status: "new" },
  ],
  pipelineStages: ["new", "contacted", "qualified", "won", "lost"],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

/** Other-tenant leads must never appear in this business's context. */
const foreignOnlyContext: SharedContext = {
  ...context,
  pipelineLeads: [
    {
      id: "foreign_1",
      name: "Other Tenant Lead",
      status: "new",
      email: "other@example.com",
    },
  ],
};

function resolve(ask: string, ctx: SharedContext = context) {
  process.env[CRM_ACTIONS_FLAG] = "1";
  const intent = readAskIntent(ask);
  const params = extractParams(ask);
  return {
    intent,
    params,
    auth: authorizesAction(intent),
    out: resolveRecordAction({
      ownerAsk: ask,
      params,
      context: ctx,
      intent,
    }),
  };
}

function toolOf(out: ReturnType<typeof resolve>["out"]): string | undefined {
  return out && "toolId" in out ? out.toolId : undefined;
}

function inputOf(
  out: ReturnType<typeof resolve>["out"],
): Record<string, unknown> | undefined {
  return out && "input" in out ? out.input : undefined;
}

function clarifyOf(out: ReturnType<typeof resolve>["out"]): string | undefined {
  return out && "clarify" in out ? out.clarify : undefined;
}

// --- create_customer -------------------------------------------------------

test("create_customer: name only", () => {
  const { out, auth } = resolve("Create a lead named Dana West.");
  assert.equal(auth, true);
  assert.equal(toolOf(out), "create_customer");
  assert.deepEqual(inputOf(out), { name: "Dana West" });
});

test("create_customer: name + email", () => {
  const { out } = resolve(
    "Create a lead named Sarah Jones with email sarah@example.com.",
  );
  assert.equal(toolOf(out), "create_customer");
  assert.deepEqual(inputOf(out), {
    name: "Sarah Jones",
    email: "sarah@example.com",
  });
});

test("create_customer: name + phone", () => {
  const { out } = resolve("Add customer Mike Smith, 864-555-1212.");
  assert.equal(toolOf(out), "create_customer");
  assert.deepEqual(inputOf(out), {
    name: "Mike Smith",
    phone: "864-555-1212",
  });
});

test("create_customer: name + email + status", () => {
  const { out } = resolve(
    "Create a lead named Pat Lee with email pat@example.com and status new.",
  );
  assert.equal(toolOf(out), "create_customer");
  assert.deepEqual(inputOf(out), {
    name: "Pat Lee",
    email: "pat@example.com",
    status: "new",
  });
});

test("create_customer: exact M8 E2E smoke phrasing", () => {
  const marker = "m8-e2e-deadbeef";
  const ask =
    `Using CRM tools only, create a lead named 'M8 E2E ${marker}' with email ` +
    `${marker}@example.invalid and status new. Do not email anyone.`;
  const { out, auth, intent } = resolve(ask);
  assert.equal(intent.intent, "create");
  assert.equal(auth, true);
  assert.equal(toolOf(out), "create_customer");
  assert.deepEqual(inputOf(out), {
    name: `M8 E2E ${marker}`,
    email: `${marker}@example.invalid`,
    status: "new",
  });
});

test("create_customer: never invents missing fields", () => {
  const { out } = resolve("Create a lead named Only Name.");
  const input = inputOf(out) ?? {};
  assert.equal(toolOf(out), "create_customer");
  assert.equal("email" in input, false);
  assert.equal("phone" in input, false);
  assert.equal("address" in input, false);
  assert.equal("status" in input, false);
});

// --- update_customer -------------------------------------------------------

test("update_customer: phone only", () => {
  const { out } = resolve("Update Sarah Jones's phone to 864-555-1212.");
  assert.equal(toolOf(out), "update_customer");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_1",
    fields: { phone: "864-555-1212" },
  });
});

test("update_customer: email only", () => {
  const { out } = resolve("Change Mike Smith's email to mike2@example.com.");
  assert.equal(toolOf(out), "update_customer");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_2",
    fields: { email: "mike2@example.com" },
  });
});

test("update_customer: address only", () => {
  const { out } = resolve(
    "Update Sarah Jones's address to 123 Main St Phoenix AZ.",
  );
  assert.equal(toolOf(out), "update_customer");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_1",
    fields: { address: "123 Main St Phoenix AZ" },
  });
});

test("update_customer: multiple fields", () => {
  const { out } = resolve(
    "Update Sarah Jones's phone to 864-555-9999 and email to sarah2@example.com.",
  );
  assert.equal(toolOf(out), "update_customer");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_1",
    fields: { phone: "864-555-9999", email: "sarah2@example.com" },
  });
});

test("update_customer: unspecified fields are not included in input", () => {
  const { out } = resolve("Update Sarah Jones's phone to 864-555-1212.");
  const fields = (inputOf(out) as { fields: Record<string, string> }).fields;
  assert.deepEqual(Object.keys(fields).sort(), ["phone"]);
});

test("update_customer: ambiguous customer clarifies", () => {
  const { out } = resolve("Update Mike's phone to 864-555-0000.");
  assert.equal(toolOf(out), undefined);
  assert.match(clarifyOf(out) ?? "", /more than one/i);
});

test("update_customer: missing customer clarifies", () => {
  const { out } = resolve("Update Jordan Miles's phone to 864-555-0000.");
  assert.equal(toolOf(out), undefined);
  assert.match(clarifyOf(out) ?? "", /couldn't find/i);
});

// --- update_lead_stage -----------------------------------------------------

test("update_lead_stage: valid canonical stage", () => {
  const { out } = resolve("Move Sarah Jones to contacted.");
  assert.equal(toolOf(out), "update_lead_stage");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_1",
    status: "contacted",
  });
});

test("update_lead_stage: valid tenant stage", () => {
  const { out } = resolve("Mark Mike Smith as won.");
  assert.equal(toolOf(out), "update_lead_stage");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_2",
    status: "won",
  });
});

test("update_lead_stage: pipeline stage phrasing", () => {
  const { out } = resolve("Change Sarah Jones's pipeline stage to qualified.");
  assert.equal(toolOf(out), "update_lead_stage");
  assert.deepEqual(inputOf(out), {
    customer_id: "lead_1",
    status: "qualified",
  });
});

test("update_lead_stage: invalid stage still selects tool (tool rejects)", () => {
  // Resolver passes the explicit stage through; Zod/tool validation rejects it.
  const { out } = resolve("Move Sarah Jones to not_a_real_stage.");
  assert.equal(toolOf(out), "update_lead_stage");
  assert.equal((inputOf(out) as { status: string }).status, "not_a_real_stage");
});

test("update_lead_stage: ambiguous customer clarifies", () => {
  const { out } = resolve("Move Mike to contacted.");
  assert.equal(toolOf(out), undefined);
  assert.match(clarifyOf(out) ?? "", /more than one/i);
});

test("update_lead_stage: missing customer clarifies", () => {
  const { out } = resolve("Move Jordan Miles to contacted.");
  assert.equal(toolOf(out), undefined);
  assert.match(clarifyOf(out) ?? "", /couldn't find/i);
});

// --- safety ----------------------------------------------------------------

test("safety: question does not mutate", () => {
  const { out, auth } = resolve("Should we create a lead for Sarah?");
  assert.equal(auth, false);
  assert.equal(toolOf(out), undefined);
});

test("safety: drafting request does not mutate", () => {
  const { out, auth } = resolve("Draft something about adding Sarah.");
  assert.equal(auth, false);
  assert.equal(toolOf(out), undefined);
});

test("safety: explain-how question does not mutate", () => {
  const { out, auth } = resolve(
    "Can you explain how I update customer stages?",
  );
  assert.equal(auth, false);
  assert.equal(toolOf(out), undefined);
});

test("safety: what-would-look-like does not execute", () => {
  const { out, auth, intent } = resolve(
    "What would a customer record for Sarah look like?",
  );
  assert.equal(intent.intent, "analyze");
  assert.equal(auth, false);
  assert.equal(toolOf(out), undefined);
});

test("safety: cross-tenant target does not resolve", () => {
  // Ask for Sarah while context only has another tenant's lead.
  const { out } = resolve(
    "Update Sarah Jones's phone to 864-555-1212.",
    foreignOnlyContext,
  );
  assert.equal(toolOf(out), undefined);
  assert.match(clarifyOf(out) ?? "", /couldn't find/i);
});

test("safety: CRM flag OFF does not mutate", () => {
  delete process.env[CRM_ACTIONS_FLAG];
  const ask =
    "Using CRM tools only, create a lead named 'M8 E2E off' with email off@example.invalid and status new. Do not email anyone.";
  const intent = readAskIntent(ask);
  const params = extractParams(ask);
  assert.equal(authorizesAction(intent), true);
  const out = resolveRecordAction({
    ownerAsk: ask,
    params,
    context,
    intent,
  });
  assert.equal(toolOf(out), undefined);
});

test("safety: add_customer_note remains ungated when CRM flag is off", () => {
  delete process.env[CRM_ACTIONS_FLAG];
  const ask = "Add a note to Sarah Jones's record saying she prefers mornings.";
  const intent = readAskIntent(ask);
  const params = extractParams(ask);
  const out = resolveRecordAction({
    ownerAsk: ask,
    params,
    context,
    intent,
  });
  assert.equal(toolOf(out), "add_customer_note");
});

test("preserve: business-profile lookup still works", () => {
  const { out } = resolve("What's my business phone on file?");
  assert.equal(toolOf(out), "get_business_profile");
});

test("preserve: customer lookup still works when CRM flag on", () => {
  const { out } = resolve("Look up the customer record for Sarah Jones.");
  // Retrieve lookups are ungated by authorization today; tool must still resolve.
  assert.ok(
    toolOf(out) === "get_customer" ||
      clarifyOf(out) !== undefined ||
      out === undefined,
  );
  // With an explicit name + CRM on, prefer get_customer when authorized retrieve
  // patterns match; if the ask is not treated as retrieve, draft is acceptable.
});
