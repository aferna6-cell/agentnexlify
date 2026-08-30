/**
 * Capability-gated send_email: flag defaults off, unauthorized departments
 * cannot propose, and the engine never sends mail.
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

import { executeAction } from "./executor.ts";
import { evaluateActionPolicy } from "./policy.ts";
import { toolRegistry } from "./registry.ts";
import { SEND_EMAIL_CAPABLE_DEPARTMENTS } from "./communication-capabilities.ts";
import { SEND_EMAIL_FLAG, sendEmailEnabled } from "./flags.ts";
import { sendEmail } from "./tools/send_email.ts";
import { harness, type Harness } from "./_testkit.ts";

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

function run(agentId: string, input: unknown) {
  return executeAction({
    accountId: "tenantA",
    agentId,
    runId: "run_1",
    toolId: "send_email",
    input,
    sharedContext: h.context,
  });
}

const validInput = {
  to: "sarah@example.com",
  subject: "Following up",
  body: "Hi Sarah",
};

test("SEND_EMAIL_ENABLED defaults off", () => {
  delete process.env[SEND_EMAIL_FLAG];
  assert.equal(sendEmailEnabled(), false);
  process.env[SEND_EMAIL_FLAG] = "0";
  assert.equal(sendEmailEnabled(), false);
  process.env[SEND_EMAIL_FLAG] = "false";
  assert.equal(sendEmailEnabled(), false);
});

test("send_email is a shared level-2 tool that requires approval", () => {
  assert.equal(sendEmail.id, "send_email");
  assert.equal(sendEmail.department, undefined);
  assert.equal(sendEmail.riskLevel, 2);
  assert.equal(sendEmail.mutating, true);
  assert.equal(sendEmail.requiresApproval, true);
  assert.deepEqual(sendEmail.requiredConnectors, ["gmail"]);
  assert.equal(toolRegistry.find("send_email")?.department, undefined);
});

test("flag off: send_email is denied and not queued, even for Sales", async () => {
  delete process.env[SEND_EMAIL_FLAG];
  const outcome = await run("sales", validInput);
  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /SEND_EMAIL_ENABLED defaults off/);
  assert.equal(outcome.record.approvalState, "not_required");
});

test("flag on: an unauthorized department cannot propose or send", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  for (const agentId of ["admin_records", "accounting", "people", undefined]) {
    const evaluation = evaluateActionPolicy(sendEmail, validInput, {
      accountId: "tenantA",
      agentId,
    });
    assert.equal(evaluation.decision, "deny", `expected deny for ${agentId}`);
    assert.match(evaluation.reason, /not permitted/);
  }
  const outcome = await run("admin_records", validInput);
  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /not permitted/);
});

test("flag on: every capable department parks for approval", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  for (const department of SEND_EMAIL_CAPABLE_DEPARTMENTS) {
    const outcome = await run(department, validInput);
    assert.equal(outcome.status, "pending_approval");
    assert.equal(outcome.record.approvalState, "pending");
    assert.equal(outcome.record.agentId, department);
  }
  await assert.rejects(
    () => sendEmail.execute({ input: validInput, context: {} as never }),
    (err: Error & { code?: string }) => {
      assert.equal(err.code, "data_plane_only");
      return true;
    },
  );
});

test("approval record preserves the exact validated email body", async () => {
  process.env[SEND_EMAIL_FLAG] = "1";
  const body = "x".repeat(5000);
  const outcome = await run("sales", { ...validInput, body });

  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.record.input.body, body);
});
