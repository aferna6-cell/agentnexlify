/**
 * Sales-only exact-email: owner subject/body on unambiguous send; otherwise
 * fall back to current compose. Other departments stay on compose.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { resolveSalesExactEmailFromOutput } from "./sales_exact_email.ts";
import { resolveEmailSendFromOutput } from "./communication_actions.ts";
import { marketing, sales } from "./departments.ts";
import { extractParams } from "./_extract.ts";
import { readAskIntent } from "./_intent.ts";
import type { DepartmentSpec } from "./_department.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

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

const COMPOSE_FALLBACK =
  "Please send an email to sarah@example.com following up on her brake quote.";

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

test("unambiguous quoted send preserves owner subject and body", () => {
  const out = resolveExact(EXACT_QUOTED);
  assert.equal(out?.toolId, "send_email");
  assert.deepEqual(out?.input, {
    to: "sarah@example.com",
    subject: "AOS smoke 2026-08-30",
    body: "Milestone 6 controlled send — safe to delete.",
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
