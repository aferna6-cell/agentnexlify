import { test } from "node:test";
import assert from "node:assert/strict";

import {
  extractExplicitEmailPayload,
  resolveEmailSendFromOutput,
} from "./communication_actions.ts";
import { readAskIntent } from "./_intent.ts";

test("extractExplicitEmailPayload parses M8 Gmail owner ask verbatim fields", () => {
  const marker = "m8-gmail-deadbeef";
  const subject = `M8 smoke ${marker}`;
  const body =
    `Milestone 8 controlled test message ${marker}. ` +
    "No follow-up action is required.";
  const ask =
    `Using Sales email tools only, send an email to smoke@example.com with subject ` +
    `'${subject}' and body '${body}'. Send exactly this email and perform no other ` +
    "action. This email must require owner approval before sending.";
  assert.deepEqual(extractExplicitEmailPayload(ask), { subject, body });
});

test("resolveEmailSendFromOutput uses explicit subject/body instead of composed draft", () => {
  const marker = "m8-gmail-abc12345";
  const subject = `M8 smoke ${marker}`;
  const body =
    `Milestone 8 controlled test message ${marker}. ` +
    "No follow-up action is required.";
  const ownerAsk =
    `Send an email to owner@example.com with subject '${subject}' and body '${body}'. ` +
    "Send exactly this email.";
  const intent = readAskIntent(ownerAsk);
  const action = resolveEmailSendFromOutput({
    ownerAsk,
    params: {},
    context: {} as never,
    intent,
    output: {
      draft: {
        title: "Wrong subject from composer",
        body: "Wrong multi-touch sequence body that must not be sent.",
      },
    },
  });
  assert.ok(action);
  assert.equal(action?.toolId, "send_email");
  assert.deepEqual(action?.input, {
    to: "owner@example.com",
    subject,
    body,
  });
});
