/**
 * Category tests for semantic routing.
 *
 * Every case here uses names and situations that appear in no benchmark case.
 * What is being tested is that a department is reachable for what it can DO,
 * and that a task outranks a noun — not that any particular sentence works.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  classify,
  classifyHeuristic,
  setClassifierModel,
} from "./_classifier.ts";
import { readAskIntent } from "./_intent.ts";
import {
  departmentSemanticScore,
  eligibleSkills,
  pickSkill,
} from "./_department.ts";
import { adminRecords, customerService, sales } from "./departments.ts";
import {
  businessAnswerPrompt,
  customerFacingSnippets,
  extractiveKbAnswer,
} from "./customer_question/agent.ts";
import { fakeEmitter, fullContext } from "./_testkit.ts";

const top = (ask: string): string | undefined =>
  classifyHeuristic(ask).candidates[0]?.agentId;

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
  const intent = readAskIntent(
    "Add a note to Dana's record that she prefers mornings.",
  );
  assert.ok(
    departmentSemanticScore(adminRecords.__department, intent) > 0,
    "the department that owns record mutation must score for a record mutation",
  );
});

test("a generative skill is ineligible for a request about something that exists", () => {
  const existing = readAskIntent(
    "Email Dana about the quote we already sent her.",
  );
  const eligible = eligibleSkills(sales.__department, existing).map(
    (s) => s.agent.agent_id,
  );
  assert.ok(
    !eligible.includes("quote_generator"),
    "a quote generator cannot serve a request about an existing quote",
  );

  const brandNew = readAskIntent(
    "Draft a quote for Dana, parts $300 and labor $200.",
  );
  const eligibleNew = eligibleSkills(sales.__department, brandNew).map(
    (s) => s.agent.agent_id,
  );
  assert.ok(
    eligibleNew.includes("quote_generator"),
    "a genuinely new quote still reaches the generator",
  );
});

test("business facts route to customer service ahead of admin records", () => {
  const asks = [
    "what services do we offer",
    "what products do we offer",
    "what are our hours",
    "what's our pricing",
    "tell me about our business",
  ];
  for (const ask of asks) {
    const topId = top(ask);
    assert.equal(topId, "customer_service", ask);
    const ranked = classifyHeuristic(ask).candidates.map((c) => c.agentId);
    const adminAt = ranked.indexOf("admin_records");
    const serviceAt = ranked.indexOf("customer_service");
    assert.ok(serviceAt !== -1 && (adminAt === -1 || serviceAt < adminAt), ask);
  }
});

test("drafting about hours stays with marketing, not a KB lookup", () => {
  assert.equal(
    top("Write a Facebook post about our weekend hours."),
    "marketing",
  );
});

test("a business-fact question is answered from the KB with no draft", async () => {
  const { emitter } = fakeEmitter();
  const out = await customerService.run({
    input: {},
    context: fullContext({
      kb: [
        { topic: "Services", answer: "We offer oil changes and brake jobs." },
      ],
    }),
    emitTrace: emitter,
    ownerAsk: "what services do we offer",
    runId: "",
  });
  assert.equal(out.draft, undefined);
  assert.match(out.noDraftReason ?? "", /knowledge base/);
  assert.match(out.orchestratorNotes.join(" "), /oil changes/);
});

test("business-fact answers omit gap text and do not dump fragments", async () => {
  const { emitter } = fakeEmitter();
  const out = await customerService.run({
    input: {},
    context: fullContext({
      kb: [
        {
          topic: "setup gaps — gather these from the owner",
          internal: true,
          answer:
            "Your knowledge about this business is incomplete. Still missing: the list of services offered.",
        },
        { topic: "frag", answer: "offer offers offer" },
        {
          topic: "roadmap",
          answer: "What we are NOT building in v1 is a marketplace.",
        },
        {
          topic: "Services",
          answer:
            "We offer oil changes, brake jobs, and tire rotations for drivers in town.",
        },
      ],
    }),
    emitTrace: emitter,
    ownerAsk: "What services do we offer?",
    runId: "",
  });
  const note = out.orchestratorNotes.join(" ");
  assert.match(note, /oil changes/i);
  assert.equal(out.draft, undefined);
  assert.doesNotMatch(note, /incomplete/i);
  assert.doesNotMatch(note, /NOT building/i);
  assert.doesNotMatch(note, /offer offers offer/);
});

const SPLICED_SERVICES_REPLY =
  "We offer What plans do you offer and how much do they cost? Two plans... AI Workforce is $99.99/month and adds...; current generalist produces empty placeholder drafts that just echo the owner's request back. New behavior: 1. If the LLM is available...{nearest_specialist}... Wishlist capture lives here...considered.";

test("a services question is not a spliced FAQ question plus spec notes", async () => {
  const kb = [
    {
      topic: "What plans do you offer and how much do they cost?",
      answer:
        "Two plans. The chatbot plan is $19.99/month. AI Workforce is $99.99/month and adds scheduling and follow-ups.",
    },
    {
      topic: "rag:pricing-span",
      answer: "Two plans... AI Workforce is $99.99/month and adds...",
    },
    {
      topic: "rag:spec",
      answer:
        "current generalist produces empty placeholder drafts that just echo the owner's request back. New behavior: 1. If the LLM is available, route to {nearest_specialist}. Wishlist capture lives here until considered.",
    },
  ];
  const snippets = customerFacingSnippets("What services do we offer?", kb);
  assert.ok(snippets.some((snippet) => snippet.includes("$99.99")));
  assert.equal(
    snippets.some((snippet) => /What plans do you offer/.test(snippet)),
    false,
  );
  assert.equal(
    snippets.some((snippet) =>
      /New behavior|nearest_specialist|Wishlist capture/.test(snippet),
    ),
    false,
  );
  const fallback = extractiveKbAnswer("What services do we offer?", snippets);
  assert.notEqual(fallback, SPLICED_SERVICES_REPLY);
  assert.match(fallback, /\$99\.99/);
  assert.doesNotMatch(fallback, /We offer What plans/);
  assert.doesNotMatch(fallback, /\.\.\./);
  assert.doesNotMatch(
    fallback,
    /New behavior|nearest_specialist|Wishlist capture/,
  );
  const prompt = businessAnswerPrompt("What services do we offer?", snippets);
  assert.match(prompt, /answer only|Snippets/i);
  assert.doesNotMatch(prompt, /New behavior|nearest_specialist/);

  const { emitter } = fakeEmitter();
  const out = await customerService.run({
    input: {},
    context: fullContext({ kb }),
    emitTrace: emitter,
    ownerAsk: "What services do we offer?",
    runId: "",
  });
  const note = out.orchestratorNotes.join(" ");
  assert.notEqual(note, SPLICED_SERVICES_REPLY);
  assert.equal(out.draft, undefined);
  assert.doesNotMatch(note, /We offer What plans/);
  assert.doesNotMatch(note, /New behavior/);
  assert.doesNotMatch(note, /\{nearest_specialist\}/);
  assert.doesNotMatch(note, /Wishlist capture/);
  assert.match(note, /\$99\.99/);
});

test("business facts short-circuit before Haiku even if the model picks admin_records", async () => {
  setClassifierModel(async () => ({
    text: JSON.stringify({
      routed_to: "admin_records",
      confidence: 0.99,
      extracted_params: {},
      alternates: [],
    }),
    model: "stub",
    inputTokens: 1,
    outputTokens: 1,
    costUsd: 0,
  }));
  try {
    const result = await classify("what services do we offer");
    assert.equal(result.candidates[0]?.agentId, "customer_service");
    assert.equal(result.candidates[0]?.confidence, 0.95);
    assert.equal(result.params.customer_question, "what services do we offer");
    assert.equal(
      pickSkill(customerService.__department, "what services do we offer").agent
        .agent_id,
      "customer_question",
    );
  } finally {
    setClassifierModel(null);
  }
});

test("replying to a customer and writing to one go to different departments", () => {
  assert.equal(
    top("Reply to the customer asking whether we service hybrids."),
    "customer_service",
  );
  assert.equal(
    top("Reply to the question that came in about our hours."),
    "customer_service",
  );
});

test("an exclusively-owned intent is not merely a strong hint", () => {
  // A department that exclusively owns an intent must beat any pile of keywords
  // belonging to another, or the orchestrator asks the owner to break a tie
  // that is not actually a tie.
  const ask =
    "Note on Dana's record that she approved the quote, the invoice and the appointment.";
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
    [
      "Send a reminder about the appointment tomorrow.",
      "Send reminders about the appointments tomorrow.",
    ],
    ["Chase the overdue invoice.", "Chase the overdue invoices."],
  ];
  for (const [one, many] of pairs)
    assert.equal(top(one), top(many), `${one} / ${many}`);
});

test("both halves of an act/ask pair route to the same department", () => {
  // Pairs differ in what should HAPPEN, never in who should handle it. A pair
  // that splits across departments means the router is reading the permission
  // axis, which is not its job.
  const pairs: [string, string][] = [
    [
      "Email dana@example.com that her car is ready.",
      "What would you say to Dana to tell her the car is ready?",
    ],
    [
      "Note on Sam's record that he approved the work.",
      "Draft a note I could put on Sam's record.",
    ],
    [
      "Chase the overdue invoice for Priya.",
      "Write me something to chase Priya's overdue invoice.",
    ],
  ];
  for (const [act, ask] of pairs)
    assert.equal(top(act), top(ask), `${act} / ${ask}`);
});
