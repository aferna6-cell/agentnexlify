/**
 * Practice-advice asks must not inherit a department's default draft skill.
 *
 * Production failure (2026-11-04): "Give me three ideas to reduce late
 * shipments at a warehouse." was labeled Operations and, with no booking
 * keyword, fell through to defaultSkillId "booking", which drafted
 * "SMS to customer — your appointment" and asked for a time slot.
 *
 * The classifier is not under test here. forceAgentId is the department the
 * router already chose — the same shape Haiku returns with no raw score.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;
delete process.env.CALENDAR_ACTIONS_ENABLED;
delete process.env.CRM_ACTIONS_ENABLED;
delete process.env.INVOICE_ACTIONS_ENABLED;
delete process.env.SEND_EMAIL_ENABLED;

import { runOrchestration } from "../../agent-os-runtime/orchestrate.ts";
import { isPracticeAdviceAsk } from "./_advice.ts";
import type { SharedContext } from "../types/agent.ts";

const CONTEXT: SharedContext = {
  businessProfile: {
    businessName: "North Dock",
    ownerName: "Sam",
    businessType: "warehouse",
  },
  widgetHistory: [],
  pipelineLeads: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

const ADVICE = [
  "Give me three ideas to reduce late shipments at a warehouse.",
  "how can I improve picking accuracy",
  "what are tips for reducing overtime",
  "Any suggestions for cutting dock wait time?",
  "How should we reduce mis-picks on the floor?",
  "Give me some advice on lowering overtime this month.",
  "how can I improve our booking show rate",
];

const BOOKING = [
  "book an appointment for Tuesday at 3",
  "Confirm Maria's Saturday 10am appointment.",
  "Reschedule Dana's Friday appointment to Thursday at 2.",
  "Cancel the booking for Priya's Tuesday slot.",
  "Mike Johnson called wanting a tire rotation Thursday at 10:30.",
  "Offer her a slot Wednesday at 4.",
];

function skillLine(
  steps: { step: string; description: string }[],
): string | undefined {
  return steps.find((s) => s.step === "select_skill")?.description;
}

test("advice phrasing is a class, and real booking requests are not in it", () => {
  for (const ask of ADVICE) assert.equal(isPracticeAdviceAsk(ask), true, ask);
  for (const ask of BOOKING) assert.equal(isPracticeAdviceAsk(ask), false, ask);
});

test("the frozen 215-case routing set is not labeled as practice advice", () => {
  const path = join(
    dirname(fileURLToPath(import.meta.url)),
    "../../../evals/datasets/action-eval-v1.json",
  );
  const data = JSON.parse(readFileSync(path, "utf8")) as {
    cases: { id: string; ask: string }[];
  };
  assert.equal(data.cases.length, 215);
  const hits = data.cases
    .filter((c) => isPracticeAdviceAsk(c.ask))
    .map((c) => c.id);
  assert.deepEqual(hits, []);
});

test("advice forced into Operations is not the Booking skill and does not draft an SMS", async () => {
  for (const ask of ADVICE) {
    const out = await runOrchestration({
      accountId: "tenant",
      ask,
      context: CONTEXT,
      forceAgentId: "operations",
    });
    const text = out.result.orchestratorNotes.join("\n");
    assert.equal(out.result.draft, undefined, ask);
    assert.equal(skillLine(out.record.traceSteps), undefined, ask);
    assert.ok(
      out.record.traceSteps.some((s) => s.step === "advisory_answer"),
      ask,
    );
    assert.match(text, /advice for you/i, ask);
    assert.doesNotMatch(text, /your appointment/i, ask);
    assert.doesNotMatch(text, /what day and time/i, ask);
    assert.equal(out.record.drafts.length, 0, ask);
  }
});

test("the warehouse ideas prompt is not a draft skill in any department", async () => {
  const ask = "Give me three ideas to reduce late shipments at a warehouse.";
  for (const dept of [
    "operations",
    "people",
    "sales",
    "marketing",
    "invoicing",
    "customer_service",
    "admin_records",
    "accounting",
  ]) {
    const out = await runOrchestration({
      accountId: "tenant",
      ask,
      context: CONTEXT,
      forceAgentId: dept,
    });
    assert.equal(out.result.agentId, dept, dept);
    assert.equal(out.result.draft, undefined, dept);
    assert.equal(skillLine(out.record.traceSteps), undefined, dept);
    assert.match(
      out.result.orchestratorNotes.join("\n"),
      /late shipments/i,
      dept,
    );
  }
});

test("other advice prompts stay plain answers when the router picks Operations", async () => {
  for (const ask of [
    "how can I improve picking accuracy",
    "what are tips for reducing overtime",
  ]) {
    const out = await runOrchestration({
      accountId: "tenant",
      ask,
      context: CONTEXT,
      forceAgentId: "operations",
    });
    assert.equal(out.result.draft, undefined, ask);
    assert.match(
      out.result.orchestratorNotes.join("\n"),
      /advice for you/i,
      ask,
    );
    assert.equal(out.record.drafts.length, 0, ask);
  }
});

test("real booking requests still route to the Booking skill", async () => {
  for (const ask of BOOKING) {
    const out = await runOrchestration({
      accountId: "tenant",
      ask,
      context: CONTEXT,
    });
    assert.equal(out.result.agentId, "operations", ask);
    assert.match(skillLine(out.record.traceSteps) ?? "", /Booking skill/, ask);
    assert.ok(out.result.draft, ask);
    assert.equal(out.result.draft?.channel, "sms", ask);
  }
});

test("the reported prompt does not draft a booking SMS on the heuristic path either", async () => {
  const out = await runOrchestration({
    accountId: "tenant",
    ask: "Give me three ideas to reduce late shipments at a warehouse.",
    context: CONTEXT,
  });
  assert.equal(out.result.draft, undefined);
  assert.doesNotMatch(skillLine(out.record.traceSteps) ?? "", /Booking/);
  assert.equal(out.record.drafts.length, 0);
});
