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
process.env.SEND_EMAIL_ENABLED = "1";

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

test("generic on-file questions do not become business-profile reads", () => {
  for (const ownerAsk of [
    "What customers do I have on file?",
    "Which invoices do we have on file?",
    "How many leads are on file right now?",
  ]) {
    const resolved = resolveRecordAction({
      ownerAsk,
      params: extractParams(ownerAsk),
      context: h.context,
      intent: readAskIntent(ownerAsk),
    });
    assert.equal(resolved, undefined, ownerAsk);
  }
});

test("the resolver acts only on an authorized record mutation", () => {
  const context = h.context;
  const ask = (a: string) =>
    resolveRecordAction({
      ownerAsk: a,
      params: extractParams(a),
      context,
      intent: readAskIntent(a),
    });

  assert.equal(
    ask("Write a one-pager on our refund policy."),
    undefined,
    "not a record mutation",
  );
  assert.equal(
    ask("Should I be noting things like this on customer records?"),
    undefined,
    "a question about the practice is never the act",
  );

  // Under-specified asks now produce a question rather than silently drafting:
  // the owner clearly wants a record updated, they just left something out.
  const noCustomer = ask("Add a note saying she prefers texts.");
  assert.ok(
    noCustomer && "clarify" in noCustomer,
    "no customer named -> ask which one",
  );
  const noText = ask("Add a note to Sarah Chen's record.");
  assert.ok(
    noText && "clarify" in noText,
    "no note text -> ask what it should say",
  );

  const action = ask(
    "Add a note to Sarah Chen's record saying she prefers texts.",
  );
  assert.ok(
    action && "toolId" in action && action.toolId === "add_customer_note",
  );
});
// --- Sales: composing an email, then proposing the send -----------------------
//
// The first department that can send something real. It composes exactly as it
// did before; the difference is that when the owner named a recipient, the
// composed text becomes a send_email action they approve rather than a draft
// they copy somewhere.

import { sales } from "../agents/departments.ts";
import { soleRecipient } from "../agents/communication_actions.ts";
import { authorizesAction, readAskIntent } from "../agents/_intent.ts";

function runSales(
  ask: string,
  userId: string | null = "tenantA",
): Promise<AgentOutput> {
  const emitTrace = createTraceEmitter("run_1", {
    persist: false,
    onStep: (s) => steps.push(s),
  });
  return sales.run({
    input: extractParams(ask),
    context: h.context,
    emitTrace,
    ownerAsk: ask,
    runId: "run_1",
    userId: userId ?? undefined,
  });
}

test("Sales proposes a real send and never sends it itself", async () => {
  const output = await runSales(
    "Email sarah@example.com to follow up on her brake quote.",
  );

  // No draft to copy: the thing awaiting approval IS the email.
  assert.equal(output.draft, undefined);
  assert.match(output.orchestratorNotes.join(" "), /sarah@example\.com/);
  assert.match(output.orchestratorNotes.join(" "), /Nothing has been sent/);

  const history = await h.store.list({ accountId: "tenantA" });
  assert.equal(history.length, 1);
  const execution = history[0]!;
  assert.equal(execution.toolId, "send_email");
  assert.equal(execution.status, "pending_approval");
  assert.equal(execution.riskLevel, 2);
  assert.equal(execution.agentId, "sales");
  assert.equal(execution.attempts, 0, "the engine never ran it");

  // The owner approves the exact text the agent wrote — recipient, subject and
  // body are all on the record.
  assert.equal(execution.input["to"], "sarah@example.com");
  assert.ok(String(execution.input["subject"] ?? "").length > 0);
  assert.ok(String(execution.input["body"] ?? "").length > 0);
});

test("Sales drafts, and proposes nothing, when no recipient was given", async () => {
  const output = await runSales(
    "Follow up with Sarah Chen on her brake quote.",
  );

  assert.ok(output.draft, "the existing draft behaviour is untouched");
  assert.equal((await h.store.list({ accountId: "tenantA" })).length, 0);
});

test("two recipients propose nothing rather than guessing which one to email", async () => {
  // The invariant is "no send is proposed", not "a draft appears" — which
  // skill answers, and whether it can draft at all, is its own business.
  const output = await runSales(
    "Email sarah@example.com and mike@example.com about the brake quote.",
  );

  assert.equal((await h.store.list({ accountId: "tenantA" })).length, 0);
  assert.ok(
    output.draft || output.noDraftReason,
    "the owner still gets an answer, just never a send to a guessed address",
  );
});

test("a recipient is only ever taken from the owner's own words", () => {
  assert.equal(
    soleRecipient("Email sarah@example.com about the quote"),
    "sarah@example.com",
  );
  assert.equal(soleRecipient("Email Sarah about the quote"), undefined);
  assert.equal(soleRecipient("Email a@x.com and b@y.com"), undefined);
  // Authorization is read off the permission axis, not off a send verb: an ask
  // for words never authorizes an act, however many send verbs it contains.
  assert.equal(
    authorizesAction(readAskIntent("Draft a follow-up for Sarah")),
    false,
  );
  assert.equal(
    authorizesAction(readAskIntent("Email sarah@example.com")),
    true,
  );
  assert.equal(
    authorizesAction(
      readAskIntent("Write me something I can send to sarah@example.com"),
    ),
    false,
    "asking for words that could be sent is not asking for a send",
  );
});
