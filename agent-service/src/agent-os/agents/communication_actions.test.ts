import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { readAskIntent } from "./_intent.ts";
import {
  resolveCommunicationAmbiguity,
  resolveEmailSendFromOutput,
  soleRecipient,
} from "./communication_actions.ts";
import { SEND_EMAIL_FLAG } from "../actions/flags.ts";
import type { SharedContext } from "../types/agent.ts";

const prevFlag = process.env[SEND_EMAIL_FLAG];

beforeEach(() => {
  delete process.env[SEND_EMAIL_FLAG];
});

afterEach(() => {
  if (prevFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = prevFlag;
});

const context: SharedContext = {
  businessProfile: { businessName: "Acme" },
  widgetHistory: [],
  pipelineLeads: [
    { id: "1", name: "Mike Johnson", status: "quoted", quoteAmount: 100 },
    { id: "2", name: "Mike Rivera", status: "quoted", quoteAmount: 200 },
  ],
  appointments: [],
  invoices: [],
  agentRunHistory: [],
  kb: [],
};

test("soleRecipient refuses when two addresses are present", () => {
  assert.equal(soleRecipient("email a@x.com and b@y.com"), undefined);
  assert.equal(
    soleRecipient("email sarah@example.com about the quote"),
    "sarah@example.com",
  );
});

test("ambiguous Mike asks for clarification instead of guessing", () => {
  const ask = "Email Mike about the quote";
  const intent = readAskIntent(ask);
  const out = resolveCommunicationAmbiguity({
    ownerAsk: ask,
    params: { customer_name: "Mike" },
    context,
    intent,
    departmentId: "sales",
  });
  assert.ok(out && "clarify" in out);
  assert.match((out as { clarify: string }).clarify, /more than one/i);
});

function sendArgs(over: {
  ask: string;
  departmentId?: string;
  draft?: { title: string; body: string } | undefined;
}) {
  const ask = over.ask;
  return {
    ownerAsk: ask,
    params: {},
    context,
    intent: readAskIntent(ask),
    output: {
      draft: over.draft ?? {
        title: "Following up on your quote",
        body: "Hi — checking in on the quote.",
      },
    },
    departmentId: over.departmentId ?? "sales",
  };
}

test("flag off: resolveEmailSendFromOutput never proposes send_email", () => {
  delete process.env[SEND_EMAIL_FLAG];
  assert.equal(
    resolveEmailSendFromOutput(
      sendArgs({ ask: "Email sarah@example.com about the quote" }),
    ),
    undefined,
  );
});

test("flag on: Sales proposes send_email only with a sole recipient and a draft", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const proposed = resolveEmailSendFromOutput(
    sendArgs({ ask: "Email sarah@example.com about the quote" }),
  );
  assert.ok(proposed && "toolId" in proposed);
  assert.equal(proposed.toolId, "send_email");
  assert.equal(proposed.input.to, "sarah@example.com");
  assert.equal(proposed.input.subject, "Following up on your quote");
});

test("flag on: draft-only authorization never becomes a send", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  assert.equal(
    resolveEmailSendFromOutput(
      sendArgs({ ask: "Draft an email to sarah@example.com about the quote" }),
    ),
    undefined,
  );
});

test("flag on: Customer Service cannot propose under the default allow-list", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  assert.equal(
    resolveEmailSendFromOutput(
      sendArgs({
        ask: "Email sarah@example.com about the quote",
        departmentId: "customer_service",
      }),
    ),
    undefined,
  );
});

test("flag on: two addresses or a missing draft do not propose", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  assert.equal(
    resolveEmailSendFromOutput(
      sendArgs({ ask: "Email a@x.com and b@y.com about the quote" }),
    ),
    undefined,
  );
  assert.equal(
    resolveEmailSendFromOutput(
      sendArgs({
        ask: "Email sarah@example.com about the quote",
        draft: { title: "", body: "" },
      }),
    ),
    undefined,
  );
});
