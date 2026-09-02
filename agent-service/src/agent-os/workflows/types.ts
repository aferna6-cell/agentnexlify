/**
 * M9 Persistent Planner — workflow contract types (M9.1).
 *
 * Mirror of `backend/services/os_workflows/contract.py`.
 *
 * Non-negotiable: the planner may decide what should happen next; it may
 * never independently perform the action. Execution stays on the existing
 * Action Executor + risk + approval + verification path.
 */

import type { RiskLevel } from "../actions/types.ts";

export type { RiskLevel };

export type StepState =
  | "planned"
  | "ready"
  | "pending_approval"
  | "running"
  | "verifying"
  | "succeeded"
  | "failed"
  | "unknown"
  | "blocked"
  | "cancelled";

export type WorkflowStatus =
  "planned" | "running" | "paused" | "succeeded" | "failed" | "cancelled";

export type VerificationState =
  "not_required" | "pending" | "passed" | "failed" | "unknown";

export const STEP_TERMINAL_STATES: readonly StepState[] = [
  "succeeded",
  "failed",
  "cancelled",
];

export const WORKFLOW_TERMINAL_STATUSES: readonly WorkflowStatus[] = [
  "succeeded",
  "failed",
  "cancelled",
];

/** Explicit allow-list — keep in sync with Python contract. */
export const ALLOWED_STEP_TRANSITIONS: Readonly<
  Record<StepState, readonly StepState[]>
> = {
  planned: ["ready", "blocked", "cancelled"],
  ready: ["pending_approval", "running", "blocked", "cancelled"],
  pending_approval: ["running", "blocked", "cancelled"],
  running: ["verifying", "failed", "unknown", "cancelled"],
  verifying: ["succeeded", "failed", "unknown"],
  blocked: ["ready", "cancelled"],
  failed: ["planned", "ready", "cancelled"],
  // L2/L3 unknown: cancel only — never auto-replay.
  unknown: ["cancelled"],
  succeeded: [],
  cancelled: [],
};

export const ALLOWED_WORKFLOW_TRANSITIONS: Readonly<
  Record<WorkflowStatus, readonly WorkflowStatus[]>
> = {
  planned: ["running", "paused", "cancelled"],
  running: ["paused", "succeeded", "failed", "cancelled"],
  paused: ["running", "cancelled"],
  succeeded: [],
  failed: ["cancelled"],
  cancelled: [],
};

export interface ToolIntent {
  /** Registry name resolved by Action Executor at run time — not callable here. */
  toolName: string;
  arguments?: Record<string, unknown>;
  department?: string | null;
}

export interface WorkflowStep {
  id: string;
  workflowId: string;
  ordinal: number;
  description: string;
  dependencies: string[];
  department?: string | null;
  toolIntent?: ToolIntent | null;
  state: StepState;
  riskLevel: RiskLevel;
  executionId?: string | null;
  verificationState?: VerificationState | null;
  error?: string | null;
}

/**
 * API shape. Persist `tenantId` as Postgres `client_id`.
 */
export interface Workflow {
  id: string;
  tenantId: string;
  ownerGoal: string;
  status: WorkflowStatus;
  steps?: WorkflowStep[];
  createdAt: string;
  updatedAt: string;
}

export class InvalidWorkflowTransition extends Error {
  readonly kind: "step" | "workflow";
  readonly current: string;
  readonly target: string;

  constructor(kind: "step" | "workflow", current: string, target: string) {
    super(`invalid ${kind} transition: ${current} → ${target}`);
    this.name = "InvalidWorkflowTransition";
    this.kind = kind;
    this.current = current;
    this.target = target;
  }
}

export class PlannerExecutionForbidden extends Error {
  constructor(context = "planner") {
    super(
      `${context} must not execute tools; enqueue a WorkflowStep for the Action Executor instead`,
    );
    this.name = "PlannerExecutionForbidden";
  }
}

export function assertPlannerCannotExecute(context = "planner"): never {
  throw new PlannerExecutionForbidden(context);
}

export function isStepTerminal(state: StepState): boolean {
  return (STEP_TERMINAL_STATES as readonly string[]).includes(state);
}

export function isWorkflowTerminal(status: WorkflowStatus): boolean {
  return (WORKFLOW_TERMINAL_STATUSES as readonly string[]).includes(status);
}

export function transitionStep(
  current: StepState,
  target: StepState,
): StepState {
  const allowed = ALLOWED_STEP_TRANSITIONS[current];
  if (!allowed.includes(target)) {
    throw new InvalidWorkflowTransition("step", current, target);
  }
  return target;
}

export function transitionWorkflow(
  current: WorkflowStatus,
  target: WorkflowStatus,
): WorkflowStatus {
  const allowed = ALLOWED_WORKFLOW_TRANSITIONS[current];
  if (!allowed.includes(target)) {
    throw new InvalidWorkflowTransition("workflow", current, target);
  }
  return target;
}
