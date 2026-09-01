/**
 * Action layer — core types.
 *
 * A *tool* is one executable capability an agent may invoke (read a business
 * profile, add a customer note, later: send an email, create a calendar event,
 * drive a browser). Every invocation produces one *action execution* record: a
 * durable, auditable row describing what was asked, what policy decided, what
 * happened, and whether it was independently verified.
 *
 * Two rules shape everything here:
 *  1. Agents never call `tool.execute()` — they go through the executor
 *     (`executor.ts`), which is the only place policy, approval, verification
 *     and audit can be enforced.
 *  2. Nothing is ever reported as done unless it actually happened. Status is an
 *     explicit state machine, not a bag of booleans, and `verification` is a
 *     separate axis from `status` so "it ran" and "we checked it landed" can
 *     never be conflated.
 */

import type { SharedContext } from "../types/agent.ts";
import type { ToolPorts } from "./ports.ts";

/**
 * Risk levels. The number is part of the contract (it is persisted and compared
 * against a tenant's approval threshold), so the values are fixed.
 *
 *  0 — read-only. Fetch records, inspect availability, search data.
 *  1 — reversible internal mutation. An internal note, an internal CRM field.
 *  2 — external communication. Email, SMS, a published social post.
 *  3 — financial / legal / destructive. Refunds, charges, deletions, payroll.
 */
export const RISK_READ_ONLY = 0;
export const RISK_INTERNAL_MUTATION = 1;
export const RISK_EXTERNAL_COMMUNICATION = 2;
export const RISK_HIGH_IMPACT = 3;

export type RiskLevel = 0 | 1 | 2 | 3;

export const RISK_LEVELS: readonly RiskLevel[] = [0, 1, 2, 3];

export const RISK_LABELS: Record<RiskLevel, string> = {
  0: "read_only",
  1: "internal_mutation",
  2: "external_communication",
  3: "high_impact",
};

/**
 * Execution lifecycle. Status is parked / running / terminal only.
 * `approved` is NOT a status — it lives on `approval_state`.
 *
 *   pending_approval -> running -> succeeded
 *                               -> failed
 *                               -> verification_failed
 *   pending_approval -> denied      (policy said no, or the owner rejected)
 *   pending_approval -> cancelled   (withdrawn before a decision)
 *   (allowed by policy) -> running -> succeeded | failed | verification_failed
 */
export type ActionExecutionStatus =
  | "pending_approval"
  | "running"
  | "succeeded"
  | "failed"
  | "verification_failed"
  | "denied"
  | "cancelled";

/** Statuses from which no further transition is possible. */
export const TERMINAL_STATUSES: readonly ActionExecutionStatus[] = [
  "succeeded",
  "failed",
  "verification_failed",
  "denied",
  "cancelled",
];

export function isTerminal(status: ActionExecutionStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

/** Approval is its own axis: a level-0 read never enters the approval machine. */
export type ApprovalState =
  "not_required" | "pending" | "approved" | "rejected";

/**
 * Verification is its own axis too. `not_applicable` means the tool declares no
 * verifier — which is honest — and is never presented as "verified".
 */
export type VerificationState =
  "not_applicable" | "pending" | "passed" | "failed";

export interface VerificationOutcome {
  /** True when the verifier independently confirmed the effect exists. */
  verified: boolean;
  /** Human-readable detail, shown in the audit trail. */
  detail: string;
  /** Optional structured evidence (sanitized before it is persisted). */
  evidence?: unknown;
}

export interface ActionExecutionError {
  code: string;
  message: string;
}

/** Where a tool's side effect actually landed. Never inferred — always declared. */
export interface EffectProvenance {
  /** The port that performed the effect, e.g. "in_memory", "collecting". */
  port: string;
  /**
   * True only when the effect reaches storage that outlives the process. An
   * in-memory demo port reports false, so nothing downstream can claim
   * durability the system does not have.
   */
  durable: boolean;
}

/** One row of the audit trail. Everything the executor knows about one attempt. */
export interface ActionExecutionRecord {
  id: string;
  /** Tenant / owner the action runs for (production: client_id). */
  accountId: string;
  /** The agent run that initiated it, when there is one. */
  runId?: string;
  /** The agent that selected the tool. */
  agentId?: string;
  toolId: string;
  riskLevel: RiskLevel;
  mutating: boolean;
  requiresApproval: boolean;
  approvalState: ApprovalState;
  approvedBy?: string;
  approvedAt?: string;
  rejectedBy?: string;
  rejectedAt?: string;
  rejectionReason?: string;
  status: ActionExecutionStatus;
  /** Sanitized input as validated by the tool's schema. */
  input: Record<string, unknown>;
  /** Sanitized tool output. Absent until the tool succeeds. */
  result?: unknown;
  error?: ActionExecutionError;
  verificationState: VerificationState;
  verificationDetail?: string;
  verifiedAt?: string;
  /** Why policy allowed / gated / denied this execution. */
  policyReason: string;
  /** Number of times the tool body has actually been invoked. */
  attempts: number;
  /**
   * De-duplication key. Callers may supply one; the executor derives one for
   * L2+ / approval tools when omitted. Persist and lookup use the same key.
   */
  idempotencyKey?: string;
  effect?: EffectProvenance;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

/** What a tool's `execute()` receives. */
export interface ToolExecuteArgs<TInput> {
  input: TInput;
  context: ToolInvocationContext;
}

/** What a tool's `verify()` receives — the input it ran on and what it returned. */
export interface ToolVerifyArgs<TInput, TOutput> {
  input: TInput;
  output: TOutput;
  context: ToolInvocationContext;
}

/**
 * Everything a tool may read. Deliberately narrow: a tool gets the tenant's
 * already-assembled read model and the capability ports — never a database
 * handle, never ambient credentials. An LLM asking for a tool does not widen
 * this surface.
 */
export interface ToolInvocationContext {
  accountId: string;
  runId?: string;
  agentId?: string;
  executionId: string;
  sharedContext: SharedContext;
  ports: ToolPorts;
  /**
   * A mutating tool calls this once it has performed its side effect, naming
   * the port that did it and whether that port is durable. The executor records
   * it verbatim on the execution row, so provenance is always declared by the
   * code that actually wrote — never inferred by the layer above. A mutating
   * tool that declares nothing is recorded as undeclared/non-durable.
   */
  declareEffect(effect: EffectProvenance): void;
}

/** The registry entry for one tool. Built by `defineTool` — never by hand. */
export interface ToolDefinition<TInput = unknown, TOutput = unknown> {
  /** Unique, stable, snake_case. Persisted on every execution row. */
  id: string;
  displayName: string;
  description: string;
  /** Owning department (an agent_id from the registry) when there is one. */
  department?: string;
  /** Integrations this tool needs, for later per-tenant availability gating. */
  requiredConnectors: string[];
  riskLevel: RiskLevel;
  /** False for pure reads. True for anything that changes state anywhere. */
  mutating: boolean;
  /** The tool's own floor. Policy may add approval; it may never remove it. */
  requiresApproval: boolean;
  inputSchema: import("zod").ZodType<TInput>;
  outputSchema: import("zod").ZodType<TOutput>;
  execute(args: ToolExecuteArgs<TInput>): Promise<TOutput>;
  /** Optional independent check that the effect actually landed. */
  verify?(args: ToolVerifyArgs<TInput, TOutput>): Promise<VerificationOutcome>;
}

/**
 * A tool with its input/output types erased.
 *
 * The registry and the executor are generic over every tool at once, so they
 * cannot carry each tool's concrete types. Rather than sprinkling `any` through
 * the boundary, the generic types are erased exactly once — in
 * `ToolRegistry.register()` — into this structural shape, and everything
 * downstream is fully typed against it. Type safety for authors is preserved by
 * `defineTool`, which validates the real schemas at definition time.
 */
export type ErasedParseResult =
  | { success: true; data: unknown; error?: undefined }
  | {
      success: false;
      data?: undefined;
      error: { issues: { path: PropertyKey[]; message: string }[] };
    };

export interface ErasedSchema {
  safeParse(value: unknown): ErasedParseResult;
}

export interface ErasedTool {
  id: string;
  displayName: string;
  description: string;
  department?: string;
  requiredConnectors: string[];
  riskLevel: RiskLevel;
  mutating: boolean;
  requiresApproval: boolean;
  inputSchema: ErasedSchema;
  outputSchema: ErasedSchema;
  execute(args: {
    input: unknown;
    context: ToolInvocationContext;
  }): Promise<unknown>;
  verify?(args: {
    input: unknown;
    output: unknown;
    context: ToolInvocationContext;
  }): Promise<VerificationOutcome>;
}

/** Registry metadata — what the orchestrator/agents may see without executing. */
export interface ToolMetadata {
  id: string;
  displayName: string;
  description: string;
  department?: string;
  requiredConnectors: string[];
  riskLevel: RiskLevel;
  riskLabel: string;
  mutating: boolean;
  requiresApproval: boolean;
  verifiable: boolean;
}

/** Thrown when a tool body wants to fail with a specific, safe code. */
export class ToolExecutionError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = "ToolExecutionError";
    this.code = code;
  }
}
