/**
 * Category tests for action eligibility — the end-to-end behaviour, not the
 * intent parser in isolation.
 *
 * Sending is a system capability rather than a Sales one, so the same
 * authorization rule has to hold from whichever department writes the message.
 * These run real departments through the real action executor with in-memory
 * ports; nothing can leave the process.
 */

import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { harness, sampleContext, type Harness } from "../actions/_testkit.ts";
import { createTraceEmitter } from "./_trace.ts";
import { extractParams } from "./_extract.ts";
import { customerService, invoicing, operations, sales } from "./departments.ts";
import type { Agent } from "./_schema.ts";
import type { AgentOutput } from "../types/agent.ts";

let h: Harness;
beforeEach(() => {
  h = harness();
});

function run(dept: Agent, ask: string, context = h.context): Promise<AgentOutput> {
  return dept.run({
    input: extractParams(ask),
    context,
    emitTrace: createTraceEmitter("run_1", { persist: false }),
    ownerAsk: ask,
    runId: "run_1",
    userId: "tenantA",
  });
}

/** The execution rows this turn produced, if any. */
const executions = () => h.store.list({ accountId: "tenantA" });

test("every department that writes to a customer can propose a send", async () => {
  // The defect this guards: sending used to be wired into Sales alone, so
  // Operations would compose a perfect message to an address the owner had
  // written out in full and then hand it back as a draft.
  const cases: [Agent, string][] = [
    [sales, "Email sarah.chen@example.com about the quote we sent her."],
    [operations, "Email mike.johnson@example.com to confirm his tire rotation appointment."],
    [invoicing, "Email sarah.chen@example.com about her outstanding invoice."],
    [customerService, "Email sarah.chen@example.com a reply to her question about our hours."],
  ];
  for (const [dept, ask] of cases) {
    h = harness();
    await run(dept, ask);
    const rows = await executions();
    assert.equal(rows.length, 1, `${dept.agent_id}: ${ask}`);
    assert.equal(rows[0]!.toolId, "send_email", ask);
    assert.equal(rows[0]!.status, "pending_approval", `${ask} — parked, never sent`);
  }
});

test("no department sends when the owner only asked for words", async () => {
  const cases: [Agent, string][] = [
    [sales, "Draft an email to sarah.chen@example.com about the quote, I'll look it over first."],
    [operations, "Write me something I could send to mike.johnson@example.com about his appointment."],
    [invoicing, "What would you say to sarah.chen@example.com about her overdue invoice?"],
    [customerService, "Rough out a reply I could send to sarah.chen@example.com."],
  ];
  for (const [dept, ask] of cases) {
    h = harness();
    await run(dept, ask);
    assert.deepEqual(await executions(), [], `${dept.agent_id} must not propose a send for: ${ask}`);
  }
});

test("a recipient is never invented from a name in the pipeline", async () => {
  // Sarah Chen is in the fixture pipeline. Her address is not in the ask, and
  // the system has no business supplying one.
  await run(sales, "Email Sarah Chen about her brake quote.");
  for (const row of await executions()) {
    assert.notEqual(row.toolId, "send_email", "a send was proposed without an address from the owner");
  }
});

test("an ambiguous recipient produces a question, not a draft and not a send", async () => {
  // Two customers share a first name. There is no confidence threshold that
  // makes choosing between two real people acceptable, so none is offered.
  const twoMikes = sampleContext({
    pipelineLeads: [
      { id: "lead_1", name: "Mike Johnson", status: "quoted", subject: "brakes", quoteAmount: 640 },
      { id: "lead_2", name: "Mike Rivera", status: "new", subject: "tires" },
    ],
  });
  const out = await run(sales, "Email Mike about the quote we discussed.", twoMikes);
  assert.deepEqual(await executions(), [], "nothing may be proposed while the recipient is unknown");
  assert.equal(out.needsClarification, true);
  assert.ok(out.orchestratorNotes.join(" ").toLowerCase().includes("mike"), "the question names the candidates");
});

test("a record mutation runs, and the same ask phrased as a question does not", async () => {
  const { adminRecords } = await import("./departments.ts");

  await run(adminRecords, "Add a note to Sarah Chen's record saying she prefers morning appointments.");
  const acted = await executions();
  assert.equal(acted.length, 1);
  assert.equal(acted[0]!.toolId, "add_customer_note");
  assert.equal(acted[0]!.status, "succeeded", "a level-1 internal write needs no approval");

  h = harness();
  await run(adminRecords, "Should I be adding notes to customer records when they prefer mornings?");
  assert.deepEqual(await executions(), [], "a question about the practice must never perform it");
});
