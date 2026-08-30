/**
 * Sales send_email proposal path: flag-off never queues; flag-on parks L2
 * pending_approval and does not execute. No mailbox port is attached.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { sales } from "./departments.ts";
import { extractParams } from "./_extract.ts";
import { createTraceEmitter } from "./_trace.ts";
import { setRunStore, type RunStore } from "../lib/providers/run-store.ts";
import { harness, type Harness } from "../actions/_testkit.ts";
import { SEND_EMAIL_FLAG } from "../actions/flags.ts";

const ASK =
  "Email sarah.chen@example.com and see if she still wants that brake quote.";

const nullRunStore: RunStore = {
  async createRoutingDecision() {
    return { id: "d1" };
  },
  async markRoutingDecisionOverridden() {},
  async createRun() {
    return { id: "run_1" };
  },
  async setRunStatus() {},
  async createDraft() {
    return { id: "draft_1" };
  },
  async captureWishlist() {},
  async recordTraceStep() {},
  async logModelCall() {},
};

let h: Harness;
const prevFlag = process.env[SEND_EMAIL_FLAG];

beforeEach(() => {
  h = harness();
  setRunStore(nullRunStore);
  delete process.env[SEND_EMAIL_FLAG];
});

afterEach(() => {
  if (prevFlag === undefined) delete process.env[SEND_EMAIL_FLAG];
  else process.env[SEND_EMAIL_FLAG] = prevFlag;
});

function runSales(ask: string) {
  return sales.run({
    input: extractParams(ask),
    context: h.context,
    emitTrace: createTraceEmitter("run_1", { persist: false }),
    ownerAsk: ask,
    runId: "run_1",
    userId: "tenantA",
  });
}

test("flag off: Sales drafts or clarifies and does not queue send_email", async () => {
  delete process.env[SEND_EMAIL_FLAG];
  await runSales(ASK);
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(
    history.filter((r) => r.toolId === "send_email").length,
    0,
    "SEND_EMAIL_ENABLED off must not queue a send",
  );
});

test("flag on: Sales parks send_email for approval and does not execute", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const output = await runSales(ASK);
  const history = await h.store.list({ accountId: "tenantA" });
  const send = history.find((r) => r.toolId === "send_email");
  assert.ok(
    send,
    `expected a parked send_email, notes=${output.orchestratorNotes.join(" ")}`,
  );
  assert.equal(send.status, "pending_approval");
  assert.equal(send.approvalState, "pending");
  assert.equal(send.riskLevel, 2);
  assert.equal(send.requiresApproval, true);
  assert.equal(send.agentId, "sales");
  assert.equal(send.input.to, "sarah.chen@example.com");
  assert.equal(
    history.filter((r) => r.status === "succeeded").length,
    0,
    "Gmail must not be touched before owner approval",
  );
});

test("flag on: a draft-only ask never queues send_email", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  await runSales(
    "Draft an email to sarah.chen@example.com about the brake quote.",
  );
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history.filter((r) => r.toolId === "send_email").length, 0);
});
