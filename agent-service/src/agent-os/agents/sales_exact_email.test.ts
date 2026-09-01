/**
 * Sales-only exact-email: owner subject/body on unambiguous send; otherwise
 * fall back to current compose. Other departments stay on compose.
 *
 * Live miss (72273a6 / m8-live-smoke-20260901T215330Z): the park write is
 * executeAction via Sales resolveActionFromOutput. Single-quoted
 * "with subject '…' and body '…'" must win; compose must not.
 */

import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";

import { executeAction } from "../actions/executor.ts";
import { SEND_EMAIL_FLAG } from "../actions/flags.ts";
import { harness, type Harness } from "../actions/_testkit.ts";
import { resolveSalesExactEmailFromOutput } from "./sales_exact_email.ts";
import { resolveEmailSendFromOutput } from "./communication_actions.ts";
import { marketing, sales } from "./departments.ts";
import { extractParams } from "./_extract.ts";
import { readAskIntent } from "./_intent.ts";
import type { DepartmentSpec } from "./_department.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

let h: Harness;
const previousFlag = process.env[SEND_EMAIL_FLAG];

beforeEach(() => {
  h = harness();
  delete process.env[SEND_EMAIL_FLAG];
});

afterEach(() => {
  if (previousFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = previousFlag;
});

const context: SharedContext = {
  businessProfile: { businessName: "Sunset Auto Care" },
  widgetHistory: [],
  pipelineLeads: [],
  pipelineStages: [],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

const composed: AgentOutput = {
  orchestratorNotes: [],
  draft: {
    title: "COMPOSED SUBJECT",
    body: "COMPOSED BODY that must not replace the owner's words.",
    channel: "email",
    requiresApproval: true,
  },
};

function resolveExact(ask: string, output: AgentOutput = composed) {
  return resolveSalesExactEmailFromOutput({
    ownerAsk: ask,
    params: extractParams(ask),
    context,
    intent: readAskIntent(ask),
    output,
  });
}

function salesFromOutput(ask: string, output: AgentOutput = composed) {
  const spec = (sales as { __department: DepartmentSpec }).__department;
  return spec.resolveActionFromOutput?.({
    ownerAsk: ask,
    params: extractParams(ask),
    context,
    intent: readAskIntent(ask),
    output,
  });
}

const EXACT_LABELED =
  "Send exactly this email to sarah@example.com\n" +
  "Subject: Brake quote follow-up\n" +
  "Body: Hi Sarah, the quote is ready whenever you are.";

const EXACT_QUOTED =
  'Email sarah@example.com with subject "AOS smoke 2026-08-30" and body "Milestone 6 controlled send — safe to delete."';

const EXACT_CURLY =
  "Email sarah@example.com with subject \u201CBrake quote follow-up\u201D and body \u201CHi Sarah, the quote is ready whenever you are.\u201D";

const COMPOSE_FALLBACK =
  "Please send an email to sarah@example.com following up on her brake quote.";

const MISMATCHED_DOUBLE_THEN_SINGLE =
  "Send an email to sarah@example.com with subject \"Hi Sarah\" and body 'It's ready.'";

const MISMATCHED_SINGLE_THEN_DOUBLE =
  "Send an email to sarah@example.com with subject 'Hi Sarah' and body \"It's ready.\"";

const APOSTROPHE_SUBJECT = "Follow up on the customer's quote";
const APOSTROPHE_BODY = "It's ready whenever you are.";
const APOSTROPHE_ASK =
  "Send exactly this email to sarah@example.com with subject " +
  `'${APOSTROPHE_SUBJECT}' and body '${APOSTROPHE_BODY}'`;
const APOSTROPHE_INPUT = {
  to: "sarah@example.com",
  subject: APOSTROPHE_SUBJECT,
  body: APOSTROPHE_BODY,
};

const INNER_WORD_SUBJECT = "Follow up on the customer's quote";
const INNER_WORD_BODY = "Please review the 'quote' and confirm it's ready.";
const INNER_WORD_ASK =
  "Send exactly this email to sarah@example.com with subject " +
  `'${INNER_WORD_SUBJECT}' and body '${INNER_WORD_BODY}'`;
const INNER_WORD_INPUT = {
  to: "sarah@example.com",
  subject: INNER_WORD_SUBJECT,
  body: INNER_WORD_BODY,
};

// Same shape as scripts/m8_live_smoke.py _build_gmail_smoke_prompt (single quotes).
const LIVE_SMOKE_SUBJECT = "M8 smoke m8-live-20260901T215330Z";
const LIVE_SMOKE_BODY =
  "Milestone 8 controlled test message m8-live-20260901T215330Z. " +
  "No follow-up action is required.";
const LIVE_SMOKE_ASK =
  "Using Sales email tools only, send an email to sarah@example.com with subject " +
  `'${LIVE_SMOKE_SUBJECT}' and body '${LIVE_SMOKE_BODY}'. Send exactly this email and perform no other ` +
  "action. This email must require owner approval before sending.";

const LIVE_SMOKE_INPUT = {
  to: "sarah@example.com",
  subject: LIVE_SMOKE_SUBJECT,
  body: LIVE_SMOKE_BODY,
};

test("unambiguous labeled send preserves owner subject and body, not the composed draft", () => {
  const out = resolveExact(EXACT_LABELED);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "Brake quote follow-up",
    body: "Hi Sarah, the quote is ready whenever you are.",
  });
  assert.notEqual(out?.input.subject, composed.draft?.title);
  assert.notEqual(out?.input.body, composed.draft?.body);
});

test("unambiguous quoted send preserves owner subject and body even if the body says delete", () => {
  const out = resolveExact(EXACT_QUOTED);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "AOS smoke 2026-08-30",
    body: "Milestone 6 controlled send — safe to delete.",
  });
});

test("double-quoted body with an apostrophe is not truncated", () => {
  const out = resolveExact(
    'Email sarah@example.com with subject "Brake quote" and body "It\'s ready whenever you are."',
  );
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "Brake quote",
    body: "It's ready whenever you are.",
  });
});

test("single-quoted body with an apostrophe keeps the full owner text", () => {
  const out = resolveExact(APOSTROPHE_ASK);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, APOSTROPHE_INPUT);
  assert.equal(out?.input.subject, APOSTROPHE_SUBJECT);
  assert.equal(out?.input.body, APOSTROPHE_BODY);
});

test("curly-quoted send preserves owner subject and body", () => {
  const out = resolveExact(EXACT_CURLY);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "Brake quote follow-up",
    body: "Hi Sarah, the quote is ready whenever you are.",
  });
});

test("mismatched quotes do not parse as exact — Sales falls back to compose", () => {
  assert.equal(resolveExact(MISMATCHED_DOUBLE_THEN_SINGLE), undefined);
  assert.equal(resolveExact(MISMATCHED_SINGLE_THEN_DOUBLE), undefined);

  const composedDoubleThenSingle = salesFromOutput(
    MISMATCHED_DOUBLE_THEN_SINGLE,
  );
  assert.equal(composedDoubleThenSingle?.toolId, "send_email");
  assert.deepEqual(composedDoubleThenSingle?.input, {
    to: "sarah@example.com",
    subject: "COMPOSED SUBJECT",
    body: "COMPOSED BODY that must not replace the owner's words.",
  });

  const composedSingleThenDouble = salesFromOutput(
    MISMATCHED_SINGLE_THEN_DOUBLE,
  );
  assert.equal(composedSingleThenDouble?.toolId, "send_email");
  assert.deepEqual(composedSingleThenDouble?.input, {
    to: "sarah@example.com",
    subject: "COMPOSED SUBJECT",
    body: "COMPOSED BODY that must not replace the owner's words.",
  });
});

test("non-unambiguous ask does not take the exact path (compose fallback)", () => {
  assert.equal(resolveExact(COMPOSE_FALLBACK), undefined);
});

test("draft-only wording is not an exact send", () => {
  assert.equal(
    resolveExact(
      "Write me exactly this email to sarah@example.com\nSubject: Hi\nBody: Hello Sarah.",
    ),
    undefined,
  );
});

test("subject without body is not unambiguous", () => {
  assert.equal(
    resolveExact(
      'Email sarah@example.com with subject "Brake quote follow-up"',
    ),
    undefined,
  );
});

test("two recipients is not unambiguous", () => {
  assert.equal(
    resolveExact(
      "Send exactly this email to sarah@example.com and mike@example.com\nSubject: Hi\nBody: Hello.",
    ),
    undefined,
  );
});

test("Sales wire: unambiguous send uses owner text even when the skill composed different copy", () => {
  const out = salesFromOutput(EXACT_LABELED);
  assert.equal(out?.toolId, "send_email");
  assert.equal(out?.input.subject, "Brake quote follow-up");
  assert.equal(
    out?.input.body,
    "Hi Sarah, the quote is ready whenever you are.",
  );
});

test("Sales wire: non-unambiguous ask uses current compose subject/body", () => {
  const out = salesFromOutput(COMPOSE_FALLBACK);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "COMPOSED SUBJECT",
    body: "COMPOSED BODY that must not replace the owner's words.",
  });
});

test("other departments stay on current compose — not the Sales exact path", () => {
  const marketingSpec = (marketing as { __department: DepartmentSpec })
    .__department;
  const salesSpec = (sales as { __department: DepartmentSpec }).__department;
  assert.equal(
    marketingSpec.resolveActionFromOutput,
    resolveEmailSendFromOutput,
  );
  assert.notEqual(
    salesSpec.resolveActionFromOutput,
    resolveEmailSendFromOutput,
  );

  const marketingOut = marketingSpec.resolveActionFromOutput?.({
    ownerAsk: EXACT_LABELED,
    params: extractParams(EXACT_LABELED),
    context,
    intent: readAskIntent(EXACT_LABELED),
    output: composed,
  });
  assert.equal(marketingOut?.toolId, "send_email");
  assert.equal(marketingOut?.input.subject, "COMPOSED SUBJECT");
  assert.equal(
    marketingOut?.input.body,
    "COMPOSED BODY that must not replace the owner's words.",
  );
});

test("live smoke single-quoted ask preserves owner subject and body, not compose", () => {
  const out = salesFromOutput(LIVE_SMOKE_ASK);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, LIVE_SMOKE_INPUT);
  assert.notEqual(out?.input.subject, composed.draft?.title);
  assert.notEqual(out?.input.body, composed.draft?.body);
});

test("park write: Sales pending row input equals owner subject and body", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const request = salesFromOutput(LIVE_SMOKE_ASK);
  assert.ok(request);
  // Production park write: shipped toolRegistry + in-memory store from harness().
  const outcome = await executeAction({
    accountId: "tenantA",
    agentId: "sales",
    runId: "run_park_exact",
    toolId: "send_email",
    input: request.input,
    sharedContext: h.context,
  });
  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.approvalState, "pending");
  assert.deepEqual(outcome.record.input, LIVE_SMOKE_INPUT);
  assert.equal(outcome.record.input.subject, LIVE_SMOKE_SUBJECT);
  assert.equal(outcome.record.input.body, LIVE_SMOKE_BODY);
  const parked = await h.store.list({ accountId: "tenantA" });
  assert.equal(parked.length, 1);
  assert.deepEqual(parked[0]?.input, LIVE_SMOKE_INPUT);
  assert.equal(parked[0]?.input.subject, LIVE_SMOKE_SUBJECT);
  assert.equal(parked[0]?.input.body, LIVE_SMOKE_BODY);
  assert.equal(parked[0]?.status, "pending_approval");
});

test("park write: inner single-quoted word in single-quoted body is byte-for-byte", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const request = salesFromOutput(INNER_WORD_ASK);
  assert.ok(request);
  assert.equal(request.input.subject, INNER_WORD_SUBJECT);
  assert.equal(request.input.body, INNER_WORD_BODY);
  const outcome = await executeAction({
    accountId: "tenantA",
    agentId: "sales",
    runId: "run_park_inner_word",
    toolId: "send_email",
    input: request.input,
    sharedContext: h.context,
  });
  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.input.subject, INNER_WORD_SUBJECT);
  assert.equal(outcome.record.input.body, INNER_WORD_BODY);
  assert.deepEqual(outcome.record.input, INNER_WORD_INPUT);
  const parked = await h.store.list({ accountId: "tenantA" });
  assert.equal(parked.length, 1);
  assert.equal(parked[0]?.status, "pending_approval");
  assert.equal(parked[0]?.input.subject, INNER_WORD_SUBJECT);
  assert.equal(parked[0]?.input.body, INNER_WORD_BODY);
});

test("park write: single-quoted customer's / it's is byte-for-byte owner payload", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const request = salesFromOutput(APOSTROPHE_ASK);
  assert.ok(request);
  const outcome = await executeAction({
    accountId: "tenantA",
    agentId: "sales",
    runId: "run_park_apostrophe",
    toolId: "send_email",
    input: request.input,
    sharedContext: h.context,
  });
  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.input.subject, APOSTROPHE_SUBJECT);
  assert.equal(outcome.record.input.body, APOSTROPHE_BODY);
  assert.deepEqual(outcome.record.input, APOSTROPHE_INPUT);
  const parked = await h.store.list({ accountId: "tenantA" });
  assert.equal(parked.length, 1);
  assert.equal(parked[0]?.status, "pending_approval");
  assert.equal(parked[0]?.input.subject, APOSTROPHE_SUBJECT);
  assert.equal(parked[0]?.input.body, APOSTROPHE_BODY);
});

test("park write: non-unambiguous ask still parks current compose", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const request = salesFromOutput(COMPOSE_FALLBACK);
  assert.ok(request);
  const outcome = await executeAction({
    accountId: "tenantA",
    agentId: "sales",
    runId: "run_park_compose",
    toolId: "send_email",
    input: request.input,
    sharedContext: h.context,
  });
  assert.equal(outcome.status, "pending_approval");
  assert.deepEqual(outcome.record.input, {
    to: "sarah@example.com",
    subject: "COMPOSED SUBJECT",
    body: "COMPOSED BODY that must not replace the owner's words.",
  });
});
