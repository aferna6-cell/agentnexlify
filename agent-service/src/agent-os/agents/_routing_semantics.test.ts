/**
 * Category tests for semantic routing.
 *
 * Every case here uses names and situations that appear in no benchmark case.
 * What is being tested is that a department is reachable for what it can DO,
 * and that a task outranks a noun — not that any particular sentence works.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { classifyHeuristic } from "./_classifier.ts";
import { readAskIntent } from "./_intent.ts";
import { departmentSemanticScore, eligibleSkills } from "./_department.ts";
import { adminRecords, sales } from "./departments.ts";

const top = (ask: string): string | undefined => classifyHeuristic(ask).candidates[0]?.agentId;

test("record mutation reaches the department that owns records, whatever noun it mentions", () => {
  // The subject nouns here belong to four different departments. The task does
  // not: putting a note on a customer record is Customer Data & Administration
  // in every one of them. Before the intent axis existed, each of these routed
  // to whichever department owned the noun.
  const asks = [
    "Note on Priya's record that she approved the tire quote.",
    "Log on Dana's file that her invoice was disputed.",
    "Add a note to Sam's record that he missed his appointment.",
    "Record on Priya's file that she left us a bad review.",
    "Note on Dana's record that she asked about our hiring.",
  ];
  for (const ask of asks) assert.equal(top(ask), "admin_records", ask);
});

test("scheduling reaches Operations, whatever noun it mentions", () => {
  for (const ask of [
    "Reschedule Priya's appointment after her quote fell through.",
    "Cancel the booking for the customer who disputed her invoice.",
  ]) {
    assert.equal(top(ask), "operations", ask);
  }
});

test("a department is routable for a capability none of its drafting skills describe", () => {
  // The regression this guards: routing signals used to be the union of the
  // skills' keywords, so a department whose skills all write documents could
  // never be reached for mutating a record.
  const intent = readAskIntent("Add a note to Dana's record that she prefers mornings.");
  assert.ok(
    departmentSemanticScore(adminRecords.__department, intent) > 0,
    "the department that owns record mutation must score for a record mutation",
  );
});

test("a generative skill is ineligible for a request about something that exists", () => {
  const existing = readAskIntent("Email Dana about the quote we already sent her.");
  const eligible = eligibleSkills(sales.__department, existing).map((s) => s.agent.agent_id);
  assert.ok(!eligible.includes("quote_generator"), "a quote generator cannot serve a request about an existing quote");

  const brandNew = readAskIntent("Draft a quote for Dana, parts $300 and labor $200.");
  const eligibleNew = eligibleSkills(sales.__department, brandNew).map((s) => s.agent.agent_id);
  assert.ok(eligibleNew.includes("quote_generator"), "a genuinely new quote still reaches the generator");
});

test("replying to a customer and writing to one go to different departments", () => {
  assert.equal(top("Reply to the customer asking whether we service hybrids."), "customer_service");
  assert.equal(top("Reply to the question that came in about our hours."), "customer_service");
});

test("an exclusively-owned intent is not merely a strong hint", () => {
  // A department that exclusively owns an intent must beat any pile of keywords
  // belonging to another, or the orchestrator asks the owner to break a tie
  // that is not actually a tie.
  const ask = "Note on Dana's record that she approved the quote, the invoice and the appointment.";
  const candidates = classifyHeuristic(ask).candidates;
  const admin = candidates.find((c) => c.agentId === "admin_records");
  const runnerUp = candidates.find((c) => c.agentId !== "admin_records");
  assert.ok(admin, "admin_records must be a candidate");
  assert.ok(
    !runnerUp || (runnerUp.score ?? 0) / (admin.score ?? 1) < 0.85,
    `exclusive ownership must be decisive; got ${admin.score} vs ${runnerUp?.score}`,
  );
});

test("a plural subject routes like its singular", () => {
  const pairs: [string, string][] = [
    ["Send a reminder about the appointment tomorrow.", "Send reminders about the appointments tomorrow."],
    ["Chase the overdue invoice.", "Chase the overdue invoices."],
  ];
  for (const [one, many] of pairs) assert.equal(top(one), top(many), `${one} / ${many}`);
});

test("both halves of an act/ask pair route to the same department", () => {
  // Pairs differ in what should HAPPEN, never in who should handle it. A pair
  // that splits across departments means the router is reading the permission
  // axis, which is not its job.
  const pairs: [string, string][] = [
    ["Email dana@example.com that her car is ready.", "What would you say to Dana to tell her the car is ready?"],
    ["Note on Sam's record that he approved the work.", "Draft a note I could put on Sam's record."],
    ["Chase the overdue invoice for Priya.", "Write me something to chase Priya's overdue invoice."],
  ];
  for (const [act, ask] of pairs) assert.equal(top(act), top(ask), `${act} / ${ask}`);
});
