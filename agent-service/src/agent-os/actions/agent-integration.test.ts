/**
 * Agent integration: the whole path, end to end.
 *
 *   owner ask -> department agent -> tool selection -> executor -> policy
 *             -> execution -> verification -> audit row -> answer
 *
 * Runs the real Customer Data & Administration department (not a double), so a
 * regression anywhere in that chain fails here.
 */

import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Offline: the classifier falls back to the heuristic and drafts use the local
// composer, so this test is hermetic.
delete process.env.ANTHROPIC_API_KEY;
delete process.env.AGENT_OS_DRAFTS_DISABLED;

import { adminRecords } from "../agents/departments.ts";
import { extractParams } from "../agents/_extract.ts";
import {
  extractNoteText,
  resolveRecordAction,
} from "../agents/admin_records_actions.ts";
import { createTraceEmitter } from "../agents/_trace.ts";
import { setRunStore, type RunStore } from "../lib/providers/run-store.ts";
import { harness, type Harness } from "./_testkit.ts";
import { setToolPolicyProvider } from "./policy.ts";
import type { AgentOutput, StreamedTraceStep } from "../types/agent.ts";

let h: Harness;
const steps: StreamedTraceStep[] = [];

/** A RunStore that records nothing: this test is about the action layer. */
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

beforeEach(() => {
  h = harness();
  setRunStore(nullRunStore);
  steps.length = 0;
});

/**
 * Run the department exactly as the orchestrator does. `userId: null` models a
 * host that could not resolve a tenant (explicit null, because passing
 * `undefined` would silently re-apply the default).
 */
function runDepartment(
  ask: string,
  userId: string | null = "tenantA",
): Promise<AgentOutput> {
  const emitTrace = createTraceEmitter("run_1", {
    persist: false,
    onStep: (s) => steps.push(s),
  });
  return adminRecords.run({
    input: extractParams(ask),
    context: h.context,
    emitTrace,
    ownerAsk: ask,
    runId: "run_1",
    userId: userId ?? undefined,
  });
}

test("the department runs a real action and reports what actually happened", async () => {
  const output = await runDepartment(
    "Add a note to Sarah Chen's record saying she prefers texts after 5pm.",
  );

  // The owner is told the action happened, and gets no draft to approve.
  assert.equal(output.draft, undefined);
  assert.match(
    output.orchestratorNotes.join(" "),
    /Added a note to Sarah Chen's record/,
  );
  assert.match(output.noDraftReason ?? "", /add_customer_note/);

  // The note is really on the record.
  const notes = await h.notes.list({
    accountId: "tenantA",
    customerId: "lead_1",
  });
  assert.equal(notes.length, 1);
  assert.match(notes[0]?.note ?? "", /prefers texts after 5pm/);

  // The audit row exists, verified, attributed to the department and the run.
  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history.length, 1);
  const record = history[0]!;
  assert.equal(record.toolId, "add_customer_note");
  assert.equal(record.status, "succeeded");
  assert.equal(record.verificationState, "passed");
  assert.equal(record.agentId, "admin_records");
  assert.equal(record.runId, "run_1");
  assert.equal(record.riskLevel, 1);

  // Tool use is visible in the honest reasoning trace.
  const traced = steps.map((s) => s.step);
  assert.ok(traced.includes("tool_select"));
  assert.ok(traced.includes("tool_policy"));
  assert.ok(traced.includes("tool_execute"));
  assert.ok(traced.includes("tool_verify"));
});

test("an action the business gated on approval parks instead of writing", async () => {
  setToolPolicyProvider({
    async load() {
      return { approvalThreshold: 1 };
    },
  });

  const output = await runDepartment(
    "Add a note to Sarah Chen's record saying she prefers texts after 5pm.",
  );

  assert.match(output.orchestratorNotes.join(" "), /needs your approval/);
  assert.equal(
    (await h.notes.list({ accountId: "tenantA", customerId: "lead_1" })).length,
    0,
  );

  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history[0]?.status, "pending_approval");
});

test("an ask the department does not clearly understand drafts instead of writing", async () => {
  const output = await runDepartment(
    "Draft a service agreement template for new customers.",
  );

  assert.ok(output.draft, "it still produces a document draft");
  assert.equal(
    (await h.store.list({ accountId: "tenantA" })).length,
    0,
    "no action was attempted",
  );
});

test("a note for a customer the business does not have drafts instead of writing", async () => {
  const output = await runDepartment(
    "Add a note to Jordan Miles's record saying he prefers email.",
  );

  assert.ok(output.draft, "an unknown customer never becomes a silent write");
  assert.equal((await h.store.list({ accountId: "tenantA" })).length, 0);
});

test("without a tenant id the department drafts and says the action layer is unavailable", async () => {
  const output = await runDepartment(
    "Add a note to Sarah Chen's record saying she prefers texts after 5pm.",
    null,
  );

  assert.ok(output.draft);
  assert.ok(
    steps.some((s) => s.step === "tool_unavailable" && s.status === "fallback"),
  );
});

// --- the ask parser --------------------------------------------------------

test("note text is taken from the owner's own words", () => {
  assert.equal(
    extractNoteText(
      "Add a note to Sarah's record saying she prefers texts after 5pm.",
    ),
    "she prefers texts after 5pm.",
  );
  assert.equal(
    extractNoteText("Log a note on Mike's file: wants a Saturday slot"),
    "wants a Saturday slot",
  );
  assert.equal(extractNoteText("Add a note for Sarah"), undefined);
});

test("the resolver refuses asks that are not clearly an action", () => {
  const context = h.context;
  const ask = (a: string) =>
    resolveRecordAction({ ownerAsk: a, params: extractParams(a), context });

  assert.equal(ask("Write a one-pager on our refund policy."), undefined);
  const unnamed = ask("Add a note saying she prefers texts.");
  assert.ok(
    unnamed && "clarify" in unnamed,
    "no customer named → ask, do not guess",
  );
  const noText = ask("Add a note to Sarah Chen's record.");
  assert.ok(
    noText && "clarify" in noText,
    "no note text → ask, do not write an empty note",
  );
  const ready = ask(
    "Add a note to Sarah Chen's record saying she prefers texts.",
  );
  assert.ok(ready && "toolId" in ready);
});
