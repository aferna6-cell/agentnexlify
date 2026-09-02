/**
 * M9.1 workflow contract transition tests — mirror Python coverage.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  ALLOWED_STEP_TRANSITIONS,
  ALLOWED_WORKFLOW_TRANSITIONS,
  assertPlannerCannotExecute,
  InvalidWorkflowTransition,
  isStepTerminal,
  isWorkflowTerminal,
  PlannerExecutionForbidden,
  STEP_TERMINAL_STATES,
  transitionStep,
  transitionWorkflow,
} from "./types.ts";

test("L0/L1 ready may run without approval", () => {
  assert.equal(transitionStep("ready", "running", 0), "running");
  assert.equal(transitionStep("ready", "running", 1), "running");
});

test("L2/L3 cannot skip approval", () => {
  assert.throws(
    () => transitionStep("ready", "running", 2),
    InvalidWorkflowTransition,
  );
  assert.throws(
    () => transitionStep("ready", "running", 3),
    InvalidWorkflowTransition,
  );
});

test("missing risk on ready→running fails closed", () => {
  assert.throws(
    () => transitionStep("ready", "running"),
    InvalidWorkflowTransition,
  );
});

test("approval path for L2 succeeds", () => {
  let state = transitionStep("planned", "ready", 2);
  state = transitionStep(state, "pending_approval", 2);
  state = transitionStep(state, "running", 2);
  assert.equal(state, "running");
});

test("failed is retryable and not terminal", () => {
  assert.equal(STEP_TERMINAL_STATES.includes("failed"), false);
  assert.equal(isStepTerminal("failed"), false);
  assert.equal(transitionStep("failed", "ready", 1), "ready");
  assert.equal(transitionStep("failed", "planned", 1), "planned");
  assert.equal(transitionStep("failed", "cancelled", 1), "cancelled");
});

test("terminal step states have empty outbound", () => {
  for (const terminal of ["succeeded", "cancelled"] as const) {
    assert.equal(isStepTerminal(terminal), true);
    assert.deepEqual(ALLOWED_STEP_TRANSITIONS[terminal], []);
    assert.throws(
      () => transitionStep(terminal, "ready", 1),
      InvalidWorkflowTransition,
    );
  }
});

test("L0/L1 unknown allows controlled recovery", () => {
  assert.equal(transitionStep("unknown", "ready", 0), "ready");
  assert.equal(transitionStep("unknown", "planned", 1), "planned");
  assert.equal(transitionStep("unknown", "blocked", 1), "blocked");
  assert.equal(transitionStep("unknown", "cancelled", 1), "cancelled");
});

test("L2/L3 unknown is cancel-only with no replay", () => {
  assert.throws(
    () => transitionStep("unknown", "ready", 2),
    InvalidWorkflowTransition,
  );
  assert.throws(
    () => transitionStep("unknown", "planned", 3),
    InvalidWorkflowTransition,
  );
  assert.throws(
    () => transitionStep("unknown", "blocked", 3),
    InvalidWorkflowTransition,
  );
  assert.equal(transitionStep("unknown", "cancelled", 2), "cancelled");
});

test("workflow failed is genuinely terminal", () => {
  assert.deepEqual(ALLOWED_WORKFLOW_TRANSITIONS.failed, []);
  assert.equal(isWorkflowTerminal("failed"), true);
  assert.throws(
    () => transitionWorkflow("failed", "cancelled"),
    InvalidWorkflowTransition,
  );
});

test("planner execution guard throws", () => {
  assert.throws(
    () => assertPlannerCannotExecute("m9.1-test"),
    PlannerExecutionForbidden,
  );
});
