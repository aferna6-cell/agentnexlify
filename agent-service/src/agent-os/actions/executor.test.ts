/**
 * Executor tests — the contract the whole action layer exists to guarantee.
 *
 * Each test names the promise it protects: approval genuinely blocks, an
 * approved action runs exactly once, failure and verification failure are
 * persisted honestly, and every attempt leaves an audit row.
 */

import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

import {
  executeAction,
  approveAction,
  rejectAction,
  getActionExecution,
  ActionNotFoundError,
  ActionStateError,
} from "./executor.ts";
import { defineTool } from "./define-tool.ts";
import { ToolRegistry } from "./registry.ts";
import { setToolPolicyProvider } from "./policy.ts";
import { REDACTED } from "./sanitize.ts";
import { harness, type Harness } from "./_testkit.ts";

let h: Harness;

beforeEach(() => {
  h = harness();
});

function run(
  toolId: string,
  input: unknown,
  extra: Record<string, unknown> = {},
) {
  return executeAction({
    accountId: "tenantA",
    agentId: "admin_records",
    runId: "run_1",
    toolId,
    input,
    sharedContext: h.context,
    registry: h.registry,
    ...extra,
  });
}

// --- registry + definition validation ---------------------------------------

test("registry rejects a duplicate tool id", () => {
  const registry = new ToolRegistry();
  const spec = {
    id: "dup_tool",
    displayName: "Dup",
    description: "d",
    riskLevel: 0 as const,
    mutating: false,
    requiresApproval: false,
    inputSchema: z.object({}),
    outputSchema: z.object({}),
    execute: async () => ({}),
  };
  registry.register(defineTool(spec));
  assert.throws(
    () => registry.register(defineTool(spec)),
    /duplicate tool id "dup_tool"/,
  );
});

test("defineTool rejects definitions that break the risk model", () => {
  const base = {
    displayName: "X",
    description: "d",
    inputSchema: z.object({}),
    outputSchema: z.object({}),
    execute: async () => ({}),
  };

  // A level-0 tool may not mutate.
  assert.throws(
    () =>
      defineTool({
        ...base,
        id: "bad_one",
        riskLevel: 0,
        mutating: true,
        requiresApproval: false,
      }),
    /read-only/,
  );
  // External communication must declare approval.
  assert.throws(
    () =>
      defineTool({
        ...base,
        id: "bad_two",
        riskLevel: 2,
        mutating: true,
        requiresApproval: false,
      }),
    /must declare requiresApproval/,
  );
  // Ids are snake_case.
  assert.throws(
    () =>
      defineTool({
        ...base,
        id: "BadThree",
        riskLevel: 0,
        mutating: false,
        requiresApproval: false,
      }),
    /snake_case/,
  );
  // Only a mutating tool can be verified.
  assert.throws(
    () =>
      defineTool({
        ...base,
        id: "bad_four",
        riskLevel: 0,
        mutating: false,
        requiresApproval: false,
        verify: async () => ({ verified: true, detail: "ok" }),
      }),
    /only meaningful for a mutating tool/,
  );
});

// --- input validation --------------------------------------------------------

test("input that fails the tool's schema never reaches the tool", async () => {
  const outcome = await run("fixture_read_only", { query: 42 });

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "invalid_input");
  assert.equal(
    h.calls["fixture_read_only"],
    undefined,
    "the tool body must not run",
  );
  assert.equal(outcome.record.startedAt, undefined);
});

// --- level 0 -----------------------------------------------------------------

test("a level-0 read executes with no approval", async () => {
  const outcome = await run("get_business_profile", {});

  assert.equal(outcome.status, "succeeded");
  assert.equal(outcome.requiresApproval, false);
  assert.equal(outcome.record.approvalState, "not_required");
  assert.equal(outcome.record.riskLevel, 0);
  assert.equal(outcome.record.attempts, 1);
  const output = outcome.output as { profile: Record<string, string> };
  assert.equal(output.profile["businessName"], "Sunset Auto Care");
});

// --- level 2 / level 3 gating -------------------------------------------------

test("a level-2 action cannot execute without approval", async () => {
  const outcome = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });

  assert.equal(outcome.status, "pending_approval");
  assert.equal(outcome.requiresApproval, true);
  assert.equal(outcome.record.approvalState, "pending");
  assert.equal(outcome.output, undefined);
  assert.equal(
    h.calls["fixture_external_message"],
    undefined,
    "the tool body must not run",
  );
});

test("a level-2 action without an explicit idempotency key stores a derived replay key", async () => {
  const outcome = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });

  assert.equal(outcome.status, "pending_approval");
  assert.ok(outcome.record.idempotencyKey);
  assert.ok(outcome.record.idempotencyKey!.trim().length >= 16);
  assert.match(
    outcome.record.idempotencyKey!,
    /^fixture_external_message-run_1-/,
  );
});

test("a level-0 action does not auto-derive an idempotency key", async () => {
  const outcome = await run("get_business_profile", {});
  assert.equal(outcome.status, "succeeded");
  assert.equal(outcome.record.idempotencyKey, undefined);
});

function spyIdempotencyLookups(): string[] {
  const keys: string[] = [];
  const inner = h.store.findByIdempotencyKey.bind(h.store);
  h.store.findByIdempotencyKey = async (accountId, toolId, key) => {
    keys.push(key);
    return inner(accountId, toolId, key);
  };
  return keys;
}

test("L2 retry with no caller key looks up the derived key and does not duplicate", async () => {
  const payload = { to: "sarah@example.com", body: "hi" };
  const first = await run("fixture_external_message", payload);
  assert.equal(first.status, "pending_approval");
  const derived = first.record.idempotencyKey;
  assert.ok(derived);

  const lookedUp = spyIdempotencyLookups();
  const second = await run("fixture_external_message", payload);

  assert.equal(second.executionId, first.executionId);
  assert.equal(second.record.idempotencyKey, derived);
  assert.ok(
    lookedUp.includes(derived!),
    `findByIdempotencyKey must query the derived key; got ${JSON.stringify(lookedUp)}`,
  );
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(
    history.length,
    1,
    "retry must not insert a second execution row",
  );
});

test("L2 retry with a different caller key still hits the derived key and does not duplicate", async () => {
  const payload = { to: "sarah@example.com", body: "hi" };
  const first = await run("fixture_external_message", payload);
  const derived = first.record.idempotencyKey;
  assert.ok(derived);

  const lookedUp = spyIdempotencyLookups();
  const second = await run("fixture_external_message", payload, {
    idempotencyKey: "caller-other-key",
  });

  assert.equal(second.executionId, first.executionId);
  assert.equal(second.record.idempotencyKey, derived);
  assert.ok(
    lookedUp.includes(derived!),
    `findByIdempotencyKey must query the derived key on a mismatched caller key; got ${JSON.stringify(lookedUp)}`,
  );
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history.length, 1);
});

test("L2 persist with a caller key stores the derived key; retry with none finds it", async () => {
  const payload = { to: "sarah@example.com", body: "hi" };
  const first = await run("fixture_external_message", payload, {
    idempotencyKey: "caller-supplied-key",
  });
  assert.equal(first.status, "pending_approval");
  const stored = first.record.idempotencyKey;
  assert.ok(stored);
  assert.notEqual(stored, "caller-supplied-key");
  assert.match(stored!, /^fixture_external_message-run_1-/);

  const lookedUp = spyIdempotencyLookups();
  const second = await run("fixture_external_message", payload);

  assert.equal(second.executionId, first.executionId);
  assert.equal(second.record.idempotencyKey, stored);
  assert.ok(
    lookedUp.includes(stored!),
    `retry with no caller key must look up the stored derived key; got ${JSON.stringify(lookedUp)}`,
  );
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(
    history.length,
    1,
    "retry must not insert a second execution row",
  );
});

test("a level-3 action always requires approval, even if the tenant lowers its threshold", async () => {
  const outcome = await run(
    "fixture_high_impact",
    { amount: 250 },
    { policy: { approvalThreshold: 3 } },
  );

  assert.equal(outcome.status, "pending_approval");
  assert.match(outcome.record.policyReason, /level 3/);
  assert.equal(h.calls["fixture_high_impact"], undefined);
});

// --- approval ----------------------------------------------------------------

test("approving a parked action runs it, once", async () => {
  const parked = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });
  assert.equal(parked.status, "pending_approval");

  const approved = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  });

  assert.equal(approved.status, "succeeded");
  assert.equal(approved.record.approvalState, "approved");
  assert.equal(approved.record.approvedBy, "owner@sunsetauto.com");
  assert.ok(approved.record.approvedAt);
  assert.equal(h.calls["fixture_external_message"], 1);
  assert.equal(approved.record.attempts, 1);
});

test("approving twice does not execute twice", async () => {
  const parked = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });
  const args = {
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  };

  const first = await approveAction(args);
  const second = await approveAction(args);

  assert.equal(first.status, "succeeded");
  assert.equal(second.status, "succeeded");
  assert.equal(second.executionId, first.executionId);
  assert.equal(
    h.calls["fixture_external_message"],
    1,
    "the tool ran exactly once",
  );
  assert.equal(second.record.attempts, 1);
});

test("concurrent approvals of the same action still execute it once", async () => {
  const parked = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });
  const args = {
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  };

  const results = await Promise.all([
    approveAction(args),
    approveAction(args),
    approveAction(args),
  ]);

  assert.equal(h.calls["fixture_external_message"], 1);
  assert.ok(results.every((r) => ["succeeded", "running"].includes(r.status)));
});

test("status never uses approved — that value lives on approval_state", async () => {
  const allowed = await run("get_business_profile", {});
  const parked = await run("fixture_external_message", {
    to: "s@example.com",
    body: "hi",
  });
  const decided = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  });

  assert.notEqual(allowed.record.status, "approved");
  assert.equal(parked.status, "pending_approval");
  assert.equal(parked.record.approvalState, "pending");
  assert.notEqual(decided.record.status, "approved");
  assert.equal(decided.record.approvalState, "approved");
});

test("rejecting an action prevents it from ever executing", async () => {
  const parked = await run("fixture_external_message", {
    to: "sarah@example.com",
    body: "hi",
  });

  const rejected = await rejectAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    rejectedBy: "owner@sunsetauto.com",
    reason: "wrong customer",
  });
  assert.equal(rejected.status, "denied");
  assert.equal(rejected.record.approvalState, "rejected");
  assert.equal(rejected.record.rejectionReason, "wrong customer");

  // A later approval must not resurrect it.
  const afterwards = await approveAction({
    accountId: "tenantA",
    executionId: parked.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(afterwards.status, "denied");
  assert.equal(
    h.calls["fixture_external_message"],
    undefined,
    "the tool never ran",
  );
});

test("rejecting is idempotent, and cannot undo an action that already ran", async () => {
  const parked = await run("fixture_external_message", {
    to: "s@example.com",
    body: "hi",
  });
  const reject = {
    accountId: "tenantA",
    executionId: parked.executionId,
    rejectedBy: "owner@sunsetauto.com",
  };
  await rejectAction(reject);
  const again = await rejectAction(reject);
  assert.equal(again.status, "denied");

  const ran = await run("fixture_read_only", { query: "hours" });
  await assert.rejects(
    () =>
      rejectAction({
        accountId: "tenantA",
        executionId: ran.executionId,
        rejectedBy: "owner",
      }),
    (err: unknown) =>
      err instanceof ActionStateError && err.status === "succeeded",
  );
});

test("an idempotency key collapses a repeated request to one execution", async () => {
  const first = await run(
    "fixture_read_only",
    { query: "hours" },
    { idempotencyKey: "req-1" },
  );
  const second = await run(
    "fixture_read_only",
    { query: "hours" },
    { idempotencyKey: "req-1" },
  );

  assert.equal(second.executionId, first.executionId);
  assert.equal(h.calls["fixture_read_only"], 1);
});

// --- failure + verification ---------------------------------------------------

test("a tool failure is persisted, not swallowed", async () => {
  const outcome = await run("fixture_always_fails", {});

  assert.equal(outcome.status, "failed");
  assert.equal(outcome.record.error?.code, "tool_error");
  assert.match(outcome.record.error?.message ?? "", /upstream exploded/);
  assert.ok(outcome.record.startedAt, "it did start");
  assert.ok(outcome.record.finishedAt);
  assert.equal(outcome.output, undefined);

  const stored = await getActionExecution("tenantA", outcome.executionId);
  assert.equal(stored?.status, "failed");
});

test("verification success is recorded on the execution", async () => {
  const outcome = await run("add_customer_note", {
    customer_name: "Sarah Chen",
    note: "Prefers texts after 5pm.",
  });

  assert.equal(outcome.status, "succeeded");
  assert.equal(outcome.record.verificationState, "passed");
  assert.ok(outcome.record.verifiedAt);
  assert.match(outcome.record.verificationDetail ?? "", /confirmed/);
});

test("a tool that runs but cannot be verified never reports success", async () => {
  const outcome = await run("fixture_fails_verification", {});

  assert.equal(outcome.status, "verification_failed");
  assert.equal(outcome.record.verificationState, "failed");
  assert.equal(outcome.record.error?.code, "verification_failed");
  assert.equal(
    outcome.output,
    undefined,
    "no output is handed back as if it worked",
  );
  assert.equal(h.calls["fixture_fails_verification"], 1);
});

// --- policy ------------------------------------------------------------------

test("a tool disabled for the business is denied without running", async () => {
  const outcome = await run(
    "fixture_read_only",
    { query: "hours" },
    { policy: { disabledToolIds: ["fixture_read_only"] } },
  );

  assert.equal(outcome.status, "denied");
  assert.match(outcome.record.policyReason, /disabled for this business/);
  assert.equal(h.calls["fixture_read_only"], undefined);
});

test("a business can raise the gate so a level-1 action also needs approval", async () => {
  const outcome = await run(
    "add_customer_note",
    { customer_name: "Sarah Chen", note: "Follow up Monday." },
    { policy: { approvalThreshold: 1 } },
  );

  assert.equal(outcome.status, "pending_approval");
  assert.equal(
    (await h.notes.list({ accountId: "tenantA", customerId: "lead_1" })).length,
    0,
  );

  const approved = await approveAction({
    accountId: "tenantA",
    executionId: outcome.executionId,
    approvedBy: "owner@sunsetauto.com",
    sharedContext: h.context,
    registry: h.registry,
  });
  assert.equal(approved.status, "succeeded");
  assert.equal(
    (await h.notes.list({ accountId: "tenantA", customerId: "lead_1" })).length,
    1,
  );
});

test("a registered policy provider supplies the tenant's policy", async () => {
  setToolPolicyProvider({
    async load(accountId) {
      return accountId === "tenantA"
        ? { disabledToolIds: ["fixture_read_only"] }
        : {};
    },
  });

  const denied = await run("fixture_read_only", { query: "hours" });
  assert.equal(denied.status, "denied");
});

test("a policy provider that throws falls back to the safe defaults", async () => {
  setToolPolicyProvider({
    async load() {
      throw new Error("policy service down");
    },
  });

  const gated = await run("fixture_external_message", {
    to: "s@example.com",
    body: "hi",
  });
  assert.equal(
    gated.status,
    "pending_approval",
    "approval is still required when policy is unavailable",
  );
});

// --- audit + isolation --------------------------------------------------------

test("every attempt leaves an auditable row, with secrets redacted", async () => {
  await run("fixture_read_only", {
    query: "hours",
    api_key: "sk-live-should-never-persist",
  });
  await run("fixture_external_message", { to: "s@example.com", body: "hi" });
  await run("no_such_tool", { anything: true });

  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history.length, 3);
  assert.deepEqual(
    history.map((r) => r.status),
    ["succeeded", "pending_approval", "denied"],
  );
  assert.ok(
    history.every((r) => r.runId === "run_1" && r.agentId === "admin_records"),
  );
  assert.equal(history[0]?.input["api_key"], REDACTED);
  assert.equal(history[2]?.error?.code, "unknown_tool");
});

test("an unknown tool is denied and audited rather than thrown away", async () => {
  const outcome = await run("send_nuclear_launch_codes", { x: 1 });

  assert.equal(outcome.status, "denied");
  assert.equal(
    outcome.record.riskLevel,
    3,
    "an unknown tool is treated as maximum risk",
  );
  assert.match(outcome.record.policyReason, /unknown tool/);
});

test("one tenant cannot approve another tenant's action", async () => {
  const parked = await run("fixture_external_message", {
    to: "s@example.com",
    body: "hi",
  });

  await assert.rejects(
    () =>
      approveAction({
        accountId: "tenantB",
        executionId: parked.executionId,
        approvedBy: "attacker@example.com",
        sharedContext: h.context,
        registry: h.registry,
      }),
    ActionNotFoundError,
  );
  assert.equal(h.calls["fixture_external_message"], undefined);
  assert.equal(await getActionExecution("tenantB", parked.executionId), null);
});
