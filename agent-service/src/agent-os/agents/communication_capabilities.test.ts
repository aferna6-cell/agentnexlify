/**
 * Communication capability config — Sales-only send by default.
 * Does not enable five-department email globally.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  COMMUNICATION_ELIGIBLE_DEPARTMENTS,
  SEND_EMAIL_PROPOSE_DEPARTMENTS_DEFAULT,
  SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG,
  canProposeSendEmail,
  isCommunicationEligible,
  sendEmailProposeDepartments,
} from "./communication_capabilities.ts";
import { SEND_EMAIL_FLAG } from "../actions/flags.ts";
import { readAskIntent } from "./_intent.ts";

const prevFlag = process.env[SEND_EMAIL_FLAG];
const prevDepts = process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG];

beforeEach(() => {
  delete process.env[SEND_EMAIL_FLAG];
  delete process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG];
});

afterEach(() => {
  if (prevFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = prevFlag;
  if (prevDepts === undefined)
    delete process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG];
  else process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG] = prevDepts;
});

test("default propose list is Sales only", () => {
  assert.deepEqual(sendEmailProposeDepartments(), ["sales"]);
  assert.deepEqual([...SEND_EMAIL_PROPOSE_DEPARTMENTS_DEFAULT], ["sales"]);
});

test("eligible communication departments are explicit and do not include marketing", () => {
  assert.deepEqual(
    [...COMMUNICATION_ELIGIBLE_DEPARTMENTS],
    ["sales", "customer_service", "operations", "invoicing"],
  );
  assert.equal(isCommunicationEligible("marketing"), false);
  assert.equal(isCommunicationEligible("accounting"), false);
  assert.equal(isCommunicationEligible("admin_records"), false);
  assert.equal(isCommunicationEligible("people"), false);
});

test("flag off: no department may propose send_email", () => {
  delete process.env[SEND_EMAIL_FLAG];
  for (const dept of [
    "sales",
    "customer_service",
    "operations",
    "invoicing",
    "marketing",
  ]) {
    assert.equal(canProposeSendEmail(dept), false, dept);
  }
});

test("flag on: only Sales may propose unless the allow-list is widened", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  assert.equal(canProposeSendEmail("sales"), true);
  assert.equal(canProposeSendEmail("customer_service"), false);
  assert.equal(canProposeSendEmail("operations"), false);
  assert.equal(canProposeSendEmail("invoicing"), false);
  assert.equal(canProposeSendEmail("marketing"), false);
});

test("widening the allow-list still cannot include ineligible departments", () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG] =
    "sales,marketing,customer_service";
  assert.equal(canProposeSendEmail("sales"), true);
  assert.equal(canProposeSendEmail("customer_service"), true);
  assert.equal(canProposeSendEmail("marketing"), false);
});

test("four-axis examples stay distinguishable", () => {
  const draft = readAskIntent("Draft an email to Sarah about the quote");
  assert.equal(draft.intent, "communicate");
  assert.equal(draft.channel, "email");
  assert.equal(draft.authorization, "draft_only");
  assert.equal(draft.subjectType, "quote");

  const send = readAskIntent("Email Sarah about the quote");
  assert.equal(send.intent, "communicate");
  assert.equal(send.channel, "email");
  assert.equal(send.authorization, "execute");
  assert.equal(send.subjectType, "quote");

  const note = readAskIntent("Make a note that Sarah approved the quote");
  assert.equal(note.intent, "update_record");
  assert.equal(note.authorization, "execute");

  const prepare = readAskIntent("Prepare a quote for Sarah");
  assert.equal(prepare.intent, "create");
  assert.equal(prepare.subjectType, "quote");
  assert.notEqual(prepare.intent, send.intent);
});
