/**
 * Category tests for the intent/subject split.
 *
 * These deliberately use subjects and phrasings that appear in no benchmark
 * case. The point is not that the system handles the sentences we happened to
 * measure — it is that the abstraction generalized. A rule that only works on
 * the examples that motivated it is a keyword patch wearing a type signature.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { authorizesAction, readAskIntent } from "./_intent.ts";

// --- Task intent is independent of business subject --------------------------
//
// The same subject noun appears on both sides of every pair. Only the task
// differs, and the task is what must decide.

test("the four quote examples stay distinguishable on independent axes", () => {
  const draft = readAskIntent("Draft an email to Sarah about the quote");
  const send = readAskIntent("Email Sarah about the quote");
  const note = readAskIntent("Make a note that Sarah approved the quote");
  const create = readAskIntent("Prepare a quote for Sarah");

  assert.equal(draft.intent, "communicate");
  assert.equal(draft.authorization, "draft_only");
  assert.equal(authorizesAction(draft), false);

  assert.equal(send.intent, "communicate");
  assert.equal(send.authorization, "execute");
  assert.equal(authorizesAction(send), true);

  assert.equal(note.intent, "update_record");
  assert.equal(authorizesAction(note), true);

  assert.equal(create.intent, "create");
  assert.equal(authorizesAction(create), false);

  // The noun "quote" is shared. It must not collapse the four asks.
  assert.equal(draft.subjectType, "quote");
  assert.equal(send.subjectType, "quote");
  assert.equal(note.subjectType, "quote");
  assert.equal(create.subjectType, "quote");
});

test("creating a business object and communicating about one are different tasks", () => {
  const pairs: [string, string][] = [
    [
      "Create a quote for Dana Whitfield, parts $300 and labor $200.",
      "Email Dana about her existing quote.",
    ],
    [
      "Generate an invoice for the Whitfield job.",
      "Email Dana about that invoice we sent her.",
    ],
    [
      "Draft a service agreement for new customers.",
      "Email Dana the service agreement we already agreed.",
    ],
    [
      "Write a job post for a part-time detailer.",
      "Email the applicant about the job post we ran.",
    ],
  ];
  for (const [creating, communicating] of pairs) {
    assert.equal(readAskIntent(creating).intent, "create", creating);
    assert.equal(
      readAskIntent(communicating).intent,
      "communicate",
      communicating,
    );
    // Both name the same subject; the subject is not what separates them.
    assert.equal(
      readAskIntent(creating).subjectType,
      readAskIntent(communicating).subjectType,
      `${creating} / ${communicating} should share a subject`,
    );
  }
});

test("a reference to an existing object rules out creating one", () => {
  for (const ask of [
    "Follow up on the estimate we sent Priya.",
    "Chase the invoice we issued last month.",
    "Write me something to send about the brake quote.",
    "Check in with Priya about her outstanding balance.",
  ]) {
    assert.equal(readAskIntent(ask).subjectExists, true, ask);
    assert.notEqual(readAskIntent(ask).intent, "create", ask);
  }
});

test("a note placed on a record is a record mutation whatever noun it mentions", () => {
  for (const ask of [
    "Note on Priya's record that she approved the tire quote.",
    "Log on Dana's file that her invoice was disputed.",
    "Add a note to Sam's profile that he cancelled his appointment.",
    "Record on Priya's file that she left a five-star review.",
  ]) {
    assert.equal(readAskIntent(ask).intent, "update_record", ask);
  }
});

// --- Authorization is its own axis ------------------------------------------

test("asking for words never authorizes an act, however many send verbs it carries", () => {
  const wordsOnly = [
    "Write me something I can send to Priya about the quote.",
    "Draft an email to dana@example.com and I'll look it over first.",
    "What would you say to Sam to tell him the part arrived?",
    "Give me wording for a text to send tomorrow's customers.",
    "Rough out a reply I could send to that review.",
  ];
  for (const ask of wordsOnly) {
    assert.equal(readAskIntent(ask).authorization, "draft_only", ask);
    assert.equal(authorizesAction(readAskIntent(ask)), false, ask);
  }
});

test("an instruction to perform an outward act authorizes one", () => {
  for (const ask of [
    "Email dana@example.com that her car is ready.",
    "Send sam@example.com the appointment reminder.",
    "Add a note to Priya's record that she prefers mornings.",
  ]) {
    assert.equal(readAskIntent(ask).authorization, "execute", ask);
    assert.equal(authorizesAction(readAskIntent(ask)), true, ask);
  }
});

test("a task with no stated channel or permission is ambiguous, not authorized", () => {
  for (const ask of [
    "Follow up with Priya.",
    "Circle back with the Whitfield account.",
  ]) {
    assert.equal(readAskIntent(ask).authorization, "ambiguous", ask);
    assert.equal(authorizesAction(readAskIntent(ask)), false, ask);
  }
});

test("a question about a practice is never the practice", () => {
  for (const ask of [
    "Should I be noting quote approvals on customer records?",
    "Do we usually email customers when a part arrives?",
    "Is it worth logging cancellations on the customer file?",
  ]) {
    const intent = readAskIntent(ask);
    assert.equal(intent.isQuestion, true, ask);
    assert.equal(authorizesAction(intent), false, ask);
    assert.notEqual(intent.intent, "update_record", ask);
  }
});

test("destruction and analysis never authorize an action", () => {
  for (const ask of [
    "Delete Priya from the pipeline.",
    "Remove Dana's invoice from the system.",
    "Figure out why afternoon bookings are down.",
  ]) {
    assert.equal(authorizesAction(readAskIntent(ask)), false, ask);
  }
});

// --- Direction separates replying from initiating ----------------------------

test("replying and initiating are different subjects", () => {
  for (const ask of [
    "Reply to the customer asking about our hours.",
    "Respond to the question that came in.",
  ]) {
    assert.equal(readAskIntent(ask).subjectType, "inbound_message", ask);
  }
  for (const ask of [
    "Email dana@example.com that the part arrived.",
    "Text Priya that we're running late.",
  ]) {
    assert.equal(readAskIntent(ask).subjectType, "outbound_message", ask);
  }
});

// --- Plurals ----------------------------------------------------------------

test("a subject is recognised in the plural as well as the singular", () => {
  const singularPlural: [string, string][] = [
    [
      "Remind him about the appointment.",
      "Remind them about the appointments.",
    ],
    ["Chase the invoice.", "Chase the invoices."],
    ["Follow up on the quote.", "Follow up on the quotes."],
    ["Reply to the review.", "Reply to the reviews."],
  ];
  for (const [one, many] of singularPlural) {
    assert.equal(
      readAskIntent(one).subjectType,
      readAskIntent(many).subjectType,
      `${one} / ${many}`,
    );
  }
});
