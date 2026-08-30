/**
 * Communication and record-action eligibility against current main policy.
 *
 * Flag-off: no department proposes send_email.
 * Flag-on: only Sales parks a send; other departments draft.
 * Record mutation acts; the same ask as a question does not.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

import { SEND_EMAIL_FLAG } from "../actions/flags.ts";
import { readAskIntent } from "./_intent.ts";
import { isClarification } from "./_department.ts";
import {
  resolveCommunicationAmbiguity,
  resolveEmailSendFromOutput,
} from "./communication_actions.ts";
import { resolveRecordAction } from "./admin_records_actions.ts";
import { extractParams } from "./_extract.ts";
import { sampleContext } from "../actions/_testkit.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

const previousFlag = process.env[SEND_EMAIL_FLAG];

beforeEach(() => {
  delete process.env[SEND_EMAIL_FLAG];
});

afterEach(() => {
  if (previousFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = previousFlag;
});

const draft: AgentOutput = {
  orchestratorNotes: [],
  draft: {
    title: "Your quote",
    body: "Hi Sarah, following up on the quote.",
    channel: "email",
    requiresApproval: true,
  },
};

function commArgs(ask: string, departmentId: string, context?: SharedContext) {
  return {
    ownerAsk: ask,
    params: extractParams(ask),
    context: context ?? sampleContext(),
    intent: readAskIntent(ask),
    departmentId,
    output: draft,
  };
}

test("flag off: no department proposes a send", () => {
  delete process.env[SEND_EMAIL_FLAG];
  const ask = "Email sarah@example.com about the quote.";
  for (const dept of [
    "sales",
    "operations",
    "invoicing",
    "customer_service",
    "marketing",
  ]) {
    assert.equal(
      resolveEmailSendFromOutput(commArgs(ask, dept)),
      undefined,
      dept,
    );
    assert.equal(
      resolveCommunicationAmbiguity(commArgs(ask, dept)),
      undefined,
      dept,
    );
  }
});

test("flag on: Sales parks a send; other departments propose nothing", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const ask = "Email sarah@example.com about the quote.";
  const sales = resolveEmailSendFromOutput(commArgs(ask, "sales"));
  assert.ok(sales);
  assert.equal(sales?.toolId, "send_email");
  assert.equal(sales?.input.to, "sarah@example.com");
  for (const dept of [
    "operations",
    "invoicing",
    "customer_service",
    "marketing",
  ]) {
    assert.equal(
      resolveEmailSendFromOutput(commArgs(ask, dept)),
      undefined,
      dept,
    );
  }
});

test("flag on, draft-only ask: Sales proposes nothing", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const ask = "Draft an email to sarah@example.com about the quote.";
  assert.equal(resolveEmailSendFromOutput(commArgs(ask, "sales")), undefined);
});

test("a recipient is never invented from a name in the pipeline", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const ask = "Email Sarah Chen about the quote.";
  assert.equal(resolveEmailSendFromOutput(commArgs(ask, "sales")), undefined);
});

test("two Mikes is a clarification, not a guessed send", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const context = sampleContext({
    pipelineLeads: [
      { id: "l1", name: "Mike Johnson", status: "quoted", quoteAmount: 100 },
      { id: "l2", name: "Mike Rivera", status: "quoted", quoteAmount: 200 },
    ],
  });
  const ask = "Email Mike about the quote.";
  const result = resolveCommunicationAmbiguity(commArgs(ask, "sales", context));
  assert.ok(isClarification(result));
  assert.match(
    (result as { clarify: string }).clarify,
    /Mike Johnson or Mike Rivera/,
  );
});

test("a record mutation runs, and the same ask phrased as a question does not", () => {
  const context = sampleContext();
  const act = resolveRecordAction({
    ownerAsk: "Note on Sarah Chen's record that she approved the quote.",
    params: extractParams(
      "Note on Sarah Chen's record that she approved the quote.",
    ),
    context,
    intent: readAskIntent(
      "Note on Sarah Chen's record that she approved the quote.",
    ),
  });
  assert.ok(act && !isClarification(act));
  assert.equal(act.toolId, "add_customer_note");

  const question = resolveRecordAction({
    ownerAsk: "Should I be noting quote approvals on customer records?",
    params: extractParams(
      "Should I be noting quote approvals on customer records?",
    ),
    context,
    intent: readAskIntent(
      "Should I be noting quote approvals on customer records?",
    ),
  });
  assert.equal(question, undefined);
});
