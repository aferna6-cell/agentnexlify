/**
 * Reference-tool tests: the two shipped tools, exercised through the executor
 * (never by calling their execute() directly — that is the boundary the rest of
 * the system relies on), plus the registry metadata and the sanitizer.
 */

import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

import { executeAction } from "./executor.ts";
import { toolRegistry } from "./registry.ts";
import { resolveCustomer } from "./tools/add_customer_note.ts";
import { sanitize, sanitizeRecord, isSecretKey, REDACTED, MAX_STRING_LENGTH } from "./sanitize.ts";
import { harness, sampleContext, type Harness } from "./_testkit.ts";
import type { SharedContext } from "../types/agent.ts";

let h: Harness;

beforeEach(() => {
  h = harness();
});

function run(toolId: string, input: unknown, context: SharedContext = h.context) {
  return executeAction({
    accountId: "tenantA",
    agentId: "admin_records",
    runId: "run_1",
    toolId,
    input,
    sharedContext: context,
    registry: h.registry,
  });
}

// --- get_business_profile -----------------------------------------------------

test("get_business_profile returns the profile and names what is missing", async () => {
  const outcome = await run("get_business_profile", {});
  const output = outcome.output as { profile: Record<string, string>; presentFields: string[]; missingFields: string[] };

  assert.equal(outcome.status, "succeeded");
  assert.equal(output.profile["ownerName"], "Maya");
  assert.ok(output.presentFields.includes("phone"));
  assert.ok(output.missingFields.includes("website"), "an absent field is reported, never invented");
  assert.equal(output.profile["website"], undefined);
});

test("get_business_profile can be narrowed to specific fields", async () => {
  const outcome = await run("get_business_profile", { fields: ["businessName", "website"] });
  const output = outcome.output as { profile: Record<string, string>; missingFields: string[] };

  assert.deepEqual(Object.keys(output.profile), ["businessName"]);
  assert.deepEqual(output.missingFields, ["website"]);
});

test("get_business_profile on an empty profile reports everything missing", async () => {
  const empty = sampleContext({ businessProfile: {} });
  const outcome = await run("get_business_profile", { fields: ["businessName"] }, empty);
  const output = outcome.output as { profile: Record<string, string>; missingFields: string[] };

  assert.equal(outcome.status, "succeeded");
  assert.deepEqual(output.profile, {});
  assert.deepEqual(output.missingFields, ["businessName"]);
});

test("get_business_profile rejects a field it does not know", async () => {
  const outcome = await run("get_business_profile", { fields: ["bank_account"] });

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "invalid_input");
});

// --- add_customer_note --------------------------------------------------------

test("add_customer_note writes the note and verifies it landed", async () => {
  const outcome = await run("add_customer_note", {
    customer_id: "lead_1",
    note: "Prefers texts after 5pm.",
  });
  const output = outcome.output as { noteId: string; customerName: string; durable: boolean };

  assert.equal(outcome.status, "succeeded");
  assert.equal(output.customerName, "Sarah Chen");
  assert.equal(outcome.record.verificationState, "passed");
  assert.equal(outcome.record.riskLevel, 1);
  assert.equal(outcome.record.mutating, true);

  const notes = await h.notes.list({ accountId: "tenantA", customerId: "lead_1" });
  assert.equal(notes.length, 1);
  assert.equal(notes[0]?.note, "Prefers texts after 5pm.");
  assert.equal(notes[0]?.source, "agent:admin_records");
});

test("add_customer_note records where the write landed and whether it is durable", async () => {
  const outcome = await run("add_customer_note", { customer_id: "lead_1", note: "Called back." });

  assert.deepEqual(outcome.record.effect, { port: "in_memory", durable: false });
  assert.equal((outcome.output as { durable: boolean }).durable, false, "an in-memory port never claims durability");
});

test("add_customer_note resolves a customer by name", async () => {
  const outcome = await run("add_customer_note", { customer_name: "Mike Johnson", note: "Wants a Saturday slot." });

  assert.equal(outcome.status, "succeeded");
  assert.equal((await h.notes.list({ accountId: "tenantA", customerId: "lead_2" })).length, 1);
});

test("add_customer_note refuses a customer it cannot resolve, and writes nothing", async () => {
  const outcome = await run("add_customer_note", { customer_name: "Nobody At All", note: "hi" });

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "customer_not_found");
  assert.equal((await h.notes.list({ accountId: "tenantA", customerId: "lead_1" })).length, 0);
});

test("add_customer_note refuses an ambiguous name rather than guessing", () => {
  const leads = [
    { id: "a", name: "Chris Green", status: "new" },
    { id: "b", name: "Chris Green", status: "quoted" },
  ];
  assert.equal(resolveCustomer(leads, { customer_name: "Chris Green" }), null);
  // A unique prefix still resolves.
  assert.equal(resolveCustomer([leads[0]!], { customer_name: "chris" })?.id, "a");
});

test("add_customer_note requires an identifier and a note", async () => {
  const noTarget = await run("add_customer_note", { note: "orphan note" });
  assert.equal(noTarget.status, "failed");
  assert.equal(noTarget.record.error?.code, "invalid_input");

  const empty = await run("add_customer_note", { customer_id: "lead_1", note: "" });
  assert.equal(empty.status, "failed");
  assert.equal(empty.record.error?.code, "invalid_input");
});

test("a customer id from another tenant's pipeline cannot be written to", async () => {
  const outcome = await run("add_customer_note", { customer_id: "lead_from_other_tenant", note: "hi" });

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "customer_not_found");
});

// --- registry metadata ---------------------------------------------------------

test("the shipped registry exposes honest metadata", () => {
  const meta = toolRegistry.metadata();
  const ids = meta.map((m) => m.id).sort();
  assert.deepEqual(ids, ["add_customer_note", "get_business_profile", "send_email"]);

  const read = meta.find((m) => m.id === "get_business_profile")!;
  assert.equal(read.riskLevel, 0);
  assert.equal(read.riskLabel, "read_only");
  assert.equal(read.mutating, false);
  assert.equal(read.verifiable, false);

  const note = meta.find((m) => m.id === "add_customer_note")!;
  assert.equal(note.riskLevel, 1);
  assert.equal(note.mutating, true);
  assert.equal(note.verifiable, true);
  assert.equal(note.department, "admin_records");
  assert.equal(note.implementation, "engine");

  // The first external tool. Its metadata is what an owner is shown before
  // approving, so every field here is load-bearing.
  const email = meta.find((m) => m.id === "send_email")!;
  assert.equal(email.riskLevel, 2);
  assert.equal(email.riskLabel, "external_communication");
  assert.equal(email.mutating, true);
  assert.equal(email.requiresApproval, true);
  assert.equal(email.implementation, "data_plane");
  assert.deepEqual(email.requiredConnectors, ["gmail"]);
});

test("availableFor honours a tenant's allow-list", () => {
  const allowed = toolRegistry.availableFor({ enabledToolIds: ["get_business_profile"] });
  assert.deepEqual(allowed.map((t) => t.id), ["get_business_profile"]);

  const none = toolRegistry.availableFor({
    disabledToolIds: ["get_business_profile", "add_customer_note", "send_email"],
  });
  assert.deepEqual(none, []);
});

// --- sanitizer -----------------------------------------------------------------

test("the sanitizer redacts secret-looking keys without eating ordinary ones", () => {
  assert.ok(isSecretKey("api_key"));
  assert.ok(isSecretKey("accessToken"));
  assert.ok(isSecretKey("Authorization"));
  assert.equal(isSecretKey("businessName"), false, "'ssn' inside a word is not a secret");
  assert.equal(isSecretKey("keywords"), false);

  const cleaned = sanitizeRecord({
    businessName: "Sunset Auto Care",
    api_key: "sk-live-abc",
    nested: { refresh_token: "rt", note: "fine" },
  });
  assert.equal(cleaned["businessName"], "Sunset Auto Care");
  assert.equal(cleaned["api_key"], REDACTED);
  assert.equal((cleaned["nested"] as Record<string, unknown>)["refresh_token"], REDACTED);
  assert.equal((cleaned["nested"] as Record<string, unknown>)["note"], "fine");
});

test("the sanitizer bounds runaway payloads", () => {
  const long = sanitize("x".repeat(MAX_STRING_LENGTH + 50)) as string;
  assert.ok(long.includes("[truncated 50 chars]"));

  const big = sanitize(Array.from({ length: 60 }, (_, i) => i)) as unknown[];
  assert.equal(big.length, 51);
  assert.equal(big[50], "[+10 more]");
});

test("a long email body is recorded verbatim, not truncated into a different email", async () => {
  // The bug this pins: the audit sanitizer shortens long strings, and a parked
  // action is later SENT from its recorded input. Truncating it would mean the
  // owner approves one email and a clipped one goes out.
  const body = `Hi Sarah,\n\n${"This is the part of the message that must survive. ".repeat(120)}\n\nThanks!`;
  assert.ok(body.length > MAX_STRING_LENGTH, "the fixture must exceed the shortening cap");

  const outcome = await run("send_email", {
    to: "sarah@example.com",
    subject: "Following up",
    body,
  });

  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.input["body"], body);
  assert.ok(!String(outcome.record.input["body"]).includes("truncated"));
});

test("results are still shortened — they are a record, not an instruction", () => {
  const long = sanitize({ detail: "x".repeat(MAX_STRING_LENGTH + 10) }) as Record<string, string>;
  assert.ok(long["detail"]!.includes("[truncated 10 chars]"));
});

test("secret-looking keys are redacted in an action's input even when kept verbatim", async () => {
  const outcome = await run("fixture_read_only", {
    query: "hours",
    api_key: "sk-live-should-never-persist",
  });

  assert.equal(outcome.record.input["query"], "hours");
  assert.equal(outcome.record.input["api_key"], REDACTED);
});
