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
import { isPracticeAdviceAsk, namesDeliverable } from "./_advice.ts";
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
];

const BOOKING = [
  "book an appointment for Tuesday at 3",
  "book me Tuesday at 3",
  "reschedule my appointment",
  "book a cleaning Tuesday 3pm",
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
    assert.match(text, /Generic checklist/i, ask);
    assert.doesNotMatch(text, /direct take/i, ask);
    assert.doesNotMatch(text, /your appointment/i, ask);
    assert.doesNotMatch(text, /what day and time/i, ask);
    assert.equal(out.record.drafts.length, 0, ask);
  }
});

test("the warehouse ideas prompt is a checklist where no skill scores", async () => {
  const ask = "Give me three ideas to reduce late shipments at a warehouse.";
  // "late" scores People → HR Memo, so that department is covered separately.
  for (const dept of [
    "operations",
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
      /Generic checklist/i,
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

test("advice plus a confirm text still drafts instead of the checklist", async () => {
  const ask = "how can we reduce no-shows? text Jane to confirm 3pm";
  assert.equal(isPracticeAdviceAsk(ask), true);
  const out = await runOrchestration({
    accountId: "tenant",
    ask,
    context: CONTEXT,
    forceAgentId: "operations",
  });
  assert.equal(
    out.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  const drafted = Boolean(out.result.draft);
  const acted =
    out.result.status === "needs_clarification" ||
    out.record.traceSteps.some((s) => s.step.startsWith("tool_"));
  assert.ok(drafted || acted, "expected a draft or an action");
  assert.match(skillLine(out.record.traceSteps) ?? "", /Booking skill/);
  assert.equal(out.result.draft?.channel, "sms");
});

test("a scored People skill is not replaced by the checklist", async () => {
  const out = await runOrchestration({
    accountId: "tenant",
    ask: "Give me three ideas to reduce late shipments at a warehouse.",
    context: CONTEXT,
    forceAgentId: "people",
  });
  assert.match(skillLine(out.record.traceSteps) ?? "", /HR Memo skill/);
  assert.equal(
    out.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  assert.ok(out.result.draft);
});

test("Operations appointment reminders still run and are not the Booking skill", async () => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(15, 0, 0, 0);
  const out = await runOrchestration({
    accountId: "tenant",
    ask: "Send tomorrow's appointments their day-before reminders.",
    context: {
      ...CONTEXT,
      appointments: [
        {
          id: "apt_1",
          customerName: "Jane",
          service: "cleaning",
          scheduledFor: tomorrow.toISOString(),
          status: "scheduled",
          reviewRequested: false,
        },
      ],
    },
  });
  assert.equal(out.result.agentId, "operations");
  assert.match(
    skillLine(out.record.traceSteps) ?? "",
    /Appointment Reminder skill/,
  );
  assert.doesNotMatch(skillLine(out.record.traceSteps) ?? "", /Booking skill/);
  assert.equal(
    out.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  assert.equal(out.result.draft?.channel, "sms");
  assert.match(out.result.draft?.title ?? "", /reminder/i);
});

test("a named deliverable skips the checklist and keeps the draft skill", async () => {
  const promo = "give me ideas for a promo text to customers";
  const reply = "suggestions for a reply to Dana";
  assert.equal(isPracticeAdviceAsk(promo), true);
  assert.equal(isPracticeAdviceAsk(reply), true);
  assert.equal(namesDeliverable(promo), true);
  assert.equal(namesDeliverable(reply), true);
  assert.equal(
    namesDeliverable(
      "Give me three ideas to reduce late shipments at a warehouse.",
    ),
    false,
  );

  const marketing = await runOrchestration({
    accountId: "tenant",
    ask: promo,
    context: CONTEXT,
    forceAgentId: "marketing",
  });
  assert.match(skillLine(marketing.record.traceSteps) ?? "", /Campaign skill/);
  assert.equal(
    marketing.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  assert.ok(marketing.result.draft);
  assert.equal(marketing.result.draft?.channel, "email");

  const service = await runOrchestration({
    accountId: "tenant",
    ask: reply,
    context: CONTEXT,
    forceAgentId: "customer_service",
  });
  assert.match(
    skillLine(service.record.traceSteps) ?? "",
    /Customer Question skill/,
  );
  assert.equal(
    service.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  assert.ok(service.result.draft);
  assert.equal(service.result.draft?.channel, "widget_reply");
});

test("a deliverable with no skill keyword still skips the checklist", async () => {
  const ask = "Give me ideas for an sms to the night crew.";
  assert.equal(isPracticeAdviceAsk(ask), true);
  assert.equal(namesDeliverable(ask), true);
  const out = await runOrchestration({
    accountId: "tenant",
    ask,
    context: CONTEXT,
    forceAgentId: "operations",
  });
  assert.equal(
    out.record.traceSteps.some((s) => s.step === "advisory_answer"),
    false,
  );
  assert.match(skillLine(out.record.traceSteps) ?? "", /Booking skill/);
  assert.ok(out.result.draft);
});
