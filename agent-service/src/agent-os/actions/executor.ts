/**
 * Action executor — the controlled boundary.
 *
 * Agents never call `tool.execute()`. They call `executeAction()`, which is the
 * one place that resolves the tool, validates the input against its schema,
 * asks policy, creates the audit row, gates on approval, runs the tool, records
 * the outcome, verifies it, and returns a structured result. Anything that
 * bypasses this function bypasses the security model, so nothing does.
 *
 * Exactly-once is enforced with conditional state transitions, not with reads
 * followed by writes: `store.transition()` only succeeds from an expected
 * status, so a double-clicked approval, a retried HTTP call and two concurrent
 * workers all collapse to one tool invocation.
 */

import { createHash, randomUUID } from "node:crypto";
import {
  evaluateActionPolicy,
  loadToolPolicy,
  type PolicyEvaluation,
  type TenantToolPolicy,
} from "./policy.ts";
import { getToolPorts } from "./ports.ts";
import { toolRegistry, type ToolRegistry } from "./registry.ts";
import { getActionStore, type ActionStore } from "./store.ts";
import { sanitize, sanitizeErrorMessage, sanitizeRecord } from "./sanitize.ts";
import {
  RISK_EXTERNAL_COMMUNICATION,
  RISK_HIGH_IMPACT,
  ToolExecutionError,
  type ActionExecutionRecord,
  type ActionExecutionStatus,
  type EffectProvenance,
  type ErasedTool,
  type ToolInvocationContext,
} from "./types.ts";
import type { SharedContext, TraceEmitter } from "../types/agent.ts";

/** Raised when a caller references an execution that does not exist. */
export class ActionNotFoundError extends Error {
  constructor(executionId: string) {
    super(`unknown action execution "${executionId}"`);
    this.name = "ActionNotFoundError";
  }
}

/** Raised when an approve/reject is impossible from the current state. */
export class ActionStateError extends Error {
  readonly status: ActionExecutionStatus;
  constructor(message: string, status: ActionExecutionStatus) {
    super(message);
    this.name = "ActionStateError";
    this.status = status;
  }
}

export interface ExecuteActionInput {
  /** Tenant the action runs for (production: client_id). */
  accountId: string;
  toolId: string;
  input: unknown;
  runId?: string;
  agentId?: string;
  /** The tenant's read model. Defaults to the one the host registered. */
  sharedContext: SharedContext;
  /** Tenant policy override. Defaults to the registered policy provider. */
  policy?: TenantToolPolicy;
  /** De-duplication key: a repeat with the same key returns the first record. */
  idempotencyKey?: string;
  /** Registry override, for tests and for per-host tool sets. */
  registry?: ToolRegistry;
  /** Optional reasoning-trace emitter; tool use shows up in the honest trace. */
  trace?: TraceEmitter;
}

/** Mirror backend RISK_FAIL_CLOSED — L2+ must carry a replay key. */
const RISK_FAIL_CLOSED = RISK_EXTERNAL_COMMUNICATION;

function deriveIdempotencyKey(input: {
  accountId: string;
  runId?: string;
  toolId: string;
  payload: Record<string, unknown>;
}): string {
  const canonical = JSON.stringify({
    accountId: input.accountId,
    runId: input.runId ?? "",
    toolId: input.toolId,
    payload: input.payload,
  });
  const digest = createHash("sha256")
    .update(canonical)
    .digest("hex")
    .slice(0, 32);
  const prefix = `${input.toolId}-${input.runId ?? "norun"}`.slice(0, 120);
  return `${prefix}-${digest}`.slice(0, 200);
}

function needsDerivedIdempotencyKey(
  riskLevel: number,
  requiresApproval: boolean,
): boolean {
  return riskLevel >= RISK_FAIL_CLOSED || requiresApproval;
}

function explicitIdempotencyKey(input: ExecuteActionInput): string | undefined {
  const explicit = input.idempotencyKey?.trim();
  return explicit || undefined;
}

function derivedIdempotencyKey(
  input: ExecuteActionInput,
  toolId: string,
  riskLevel: number,
  requiresApproval: boolean,
  parsedInput: Record<string, unknown>,
): string | undefined {
  if (!needsDerivedIdempotencyKey(riskLevel, requiresApproval))
    return undefined;
  return deriveIdempotencyKey({
    accountId: input.accountId,
    runId: input.runId,
    toolId,
    payload: parsedInput,
  });
}

/**
 * Canonical replay key: when derivation applies it wins persist AND lookup.
 * One field cannot store both; caller-wins persist with derived-only lookup
 * misses on a retry that omits the caller key.
 */
function canonicalIdempotencyKey(
  explicit: string | undefined,
  derived: string | undefined,
): string | undefined {
  return derived ?? explicit;
}

/**
 * Lookup the canonical key. Persist writes the same value.
 */
async function findByAnyIdempotencyKey(
  store: ActionStore,
  accountId: string,
  toolId: string,
  keys: Array<string | undefined>,
): Promise<ActionExecutionRecord | null> {
  const seen = new Set<string>();
  for (const key of keys) {
    if (!key || seen.has(key)) continue;
    seen.add(key);
    const existing = await store.findByIdempotencyKey(accountId, toolId, key);
    if (existing) return existing;
  }
  return null;
}

export interface ActionOutcome {
  executionId: string;
  status: ActionExecutionStatus;
  /** True when the action is parked waiting for a human decision. */
  requiresApproval: boolean;
  record: ActionExecutionRecord;
  /** Present only on a genuinely successful execution. */
  output?: unknown;
  /** Present on failure/denial: a safe, human-readable reason. */
  error?: string;
}

export interface ApproveActionInput {
  accountId: string;
  executionId: string;
  approvedBy: string;
  sharedContext: SharedContext;
  registry?: ToolRegistry;
  trace?: TraceEmitter;
}

export interface RejectActionInput {
  accountId: string;
  executionId: string;
  rejectedBy: string;
  reason?: string;
}

function nowIso(): string {
  return new Date().toISOString();
}

function outcomeOf(record: ActionExecutionRecord): ActionOutcome {
  return {
    executionId: record.id,
    status: record.status,
    requiresApproval: record.status === "pending_approval",
    record,
    output: record.status === "succeeded" ? record.result : undefined,
    error:
      record.error?.message ??
      (record.status === "denied" ? record.policyReason : undefined),
  };
}

/** Guard: an execution row belongs to exactly one tenant, and only that tenant. */
function assertTenant(record: ActionExecutionRecord, accountId: string): void {
  if (record.accountId !== accountId) {
    // Do not leak the existence of another tenant's row.
    throw new ActionNotFoundError(record.id);
  }
}

/**
 * Resolve → validate → policy → record → (gate | run).
 *
 * Returns a structured outcome in every case, including denial and
 * approval-required. It throws only for programmer errors (no store or ports
 * registered) — never for a policy or tool failure, which are data.
 */
export async function executeAction(
  input: ExecuteActionInput,
): Promise<ActionOutcome> {
  const store = getActionStore();
  const registry = input.registry ?? toolRegistry;
  const trace = input.trace;
  const explicit = explicitIdempotencyKey(input);

  if (explicit) {
    const existing = await store.findByIdempotencyKey(
      input.accountId,
      input.toolId,
      explicit,
    );
    if (existing) return outcomeOf(existing);
  }

  const tool = registry.find(input.toolId);

  // An unknown tool is audited, not swallowed: an agent (or a model) asking for
  // a tool that does not exist is exactly the kind of thing we want a row for.
  // It is recorded at the highest risk level because nothing is known about it.
  if (!tool) {
    const unknownInput = sanitizeRecord(input.input) as Record<string, unknown>;
    const derived = derivedIdempotencyKey(
      input,
      input.toolId,
      RISK_HIGH_IMPACT,
      false,
      unknownInput,
    );
    const canonical = canonicalIdempotencyKey(explicit, derived);
    const replay = await findByAnyIdempotencyKey(
      store,
      input.accountId,
      input.toolId,
      [canonical],
    );
    if (replay) return outcomeOf(replay);
    const record = await store.create(
      baseRecord({
        accountId: input.accountId,
        runId: input.runId,
        agentId: input.agentId,
        toolId: input.toolId,
        riskLevel: RISK_HIGH_IMPACT,
        mutating: false,
        requiresApproval: false,
        status: "denied",
        approvalState: "not_required",
        input: unknownInput,
        policyReason: `unknown tool "${input.toolId}"`,
        idempotencyKey: canonical,
        error: {
          code: "unknown_tool",
          message: `unknown tool "${input.toolId}"`,
        },
      }),
    );
    await trace?.fallback(
      "tool_select",
      `No such tool "${input.toolId}" — nothing was run.`,
    );
    return outcomeOf(record);
  }

  await trace?.work("tool_select", `Selected the ${tool.displayName} tool`);

  const parsed = tool.inputSchema.safeParse(input.input);
  if (!parsed.success) {
    const message = parsed.error.issues
      .map((i) => `${i.path.join(".") || "input"}: ${i.message}`)
      .join("; ");
    const invalidInput = sanitizeRecord(input.input) as Record<string, unknown>;
    const derived = derivedIdempotencyKey(
      input,
      tool.id,
      tool.riskLevel,
      tool.requiresApproval,
      invalidInput,
    );
    const canonical = canonicalIdempotencyKey(explicit, derived);
    const replay = await findByAnyIdempotencyKey(
      store,
      input.accountId,
      tool.id,
      [canonical],
    );
    if (replay) return outcomeOf(replay);
    const record = await store.create(
      baseRecord({
        accountId: input.accountId,
        runId: input.runId,
        agentId: input.agentId,
        toolId: tool.id,
        riskLevel: tool.riskLevel,
        mutating: tool.mutating,
        requiresApproval: tool.requiresApproval,
        status: "failed",
        approvalState: "not_required",
        input: invalidInput,
        policyReason:
          "input rejected by the tool's schema — nothing was executed",
        idempotencyKey: canonical,
        error: {
          code: "invalid_input",
          message: sanitizeErrorMessage(message),
        },
        finishedAt: nowIso(),
      }),
    );
    await trace?.fallback(
      "tool_input",
      `The ${tool.displayName} tool rejected the input: ${message}`,
    );
    return outcomeOf(record);
  }

  const policy = input.policy ?? (await loadToolPolicy(input.accountId));
  const evaluation: PolicyEvaluation = evaluateActionPolicy(tool, parsed.data, {
    accountId: input.accountId,
    agentId: input.agentId,
    policy,
  });
  await trace?.work("tool_policy", `Permission check: ${evaluation.reason}`);

  const parsedInput = sanitizeRecord(parsed.data) as Record<string, unknown>;
  const derived = derivedIdempotencyKey(
    input,
    tool.id,
    evaluation.riskLevel,
    evaluation.requiresApproval,
    parsedInput,
  );
  const canonical = canonicalIdempotencyKey(explicit, derived);
  const replay = await findByAnyIdempotencyKey(
    store,
    input.accountId,
    tool.id,
    [canonical],
  );
  if (replay) return outcomeOf(replay);

  const common = {
    accountId: input.accountId,
    runId: input.runId,
    agentId: input.agentId,
    toolId: tool.id,
    riskLevel: evaluation.riskLevel,
    mutating: tool.mutating,
    requiresApproval: evaluation.requiresApproval,
    input: parsedInput,
    policyReason: evaluation.reason,
    idempotencyKey: canonical,
  };

  if (evaluation.decision === "deny") {
    const record = await store.create(
      baseRecord({
        ...common,
        status: "denied",
        approvalState: "not_required",
        finishedAt: nowIso(),
      }),
    );
    await trace?.fallback("tool_policy", `Not permitted: ${evaluation.reason}`);
    return outcomeOf(record);
  }

  if (evaluation.decision === "requires_approval") {
    const record = await store.create(
      baseRecord({
        ...common,
        status: "pending_approval",
        approvalState: "pending",
      }),
    );
    await trace?.fallback(
      "tool_approval",
      `${tool.displayName} needs your approval before it runs (${evaluation.reason}).`,
    );
    return outcomeOf(record);
  }

  const record = await store.create(
    baseRecord({
      ...common,
      status: "running",
      approvalState: "not_required",
      startedAt: nowIso(),
      attempts: 1,
    }),
  );
  return runRecorded(record, tool, parsed.data, input.sharedContext, trace);
}

/**
 * Approve a parked action and run it — exactly once, however many times this is
 * called. A second approval of an already-decided action returns that action's
 * current state instead of executing again.
 */
export async function approveAction(
  input: ApproveActionInput,
): Promise<ActionOutcome> {
  const store = getActionStore();
  const registry = input.registry ?? toolRegistry;

  const existing = await store.get(input.executionId);
  if (!existing) throw new ActionNotFoundError(input.executionId);
  assertTenant(existing, input.accountId);

  // Idempotency: only a parked action can be approved. Status stays parked /
  // running / terminal — `approved` is written on approval_state, not status.
  // Anything else — already running, already finished, already rejected —
  // returns as-is.
  const running = await store.transition(
    input.executionId,
    ["pending_approval"],
    "running",
    {
      approvalState: "approved",
      approvedBy: input.approvedBy,
      approvedAt: nowIso(),
      startedAt: nowIso(),
      attempts: existing.attempts + 1,
    },
  );
  if (!running) {
    const current = await store.get(input.executionId);
    if (!current) throw new ActionNotFoundError(input.executionId);
    return outcomeOf(current);
  }

  const tool = registry.find(running.toolId);
  if (!tool) {
    const failed = await store.update(running.id, {
      status: "failed",
      error: {
        code: "unknown_tool",
        message: `tool "${running.toolId}" is no longer registered`,
      },
      finishedAt: nowIso(),
    });
    return outcomeOf(failed);
  }

  // Re-validate against the tool's current schema: the stored input crossed a
  // process (and possibly a deploy) boundary since it was written.
  const parsed = tool.inputSchema.safeParse(running.input);
  if (!parsed.success) {
    const message = parsed.error.issues
      .map((i) => `${i.path.join(".") || "input"}: ${i.message}`)
      .join("; ");
    const failed = await store.update(running.id, {
      status: "failed",
      error: { code: "invalid_input", message: sanitizeErrorMessage(message) },
      finishedAt: nowIso(),
    });
    return outcomeOf(failed);
  }

  return runRecorded(
    running,
    tool,
    parsed.data,
    input.sharedContext,
    input.trace,
  );
}

/** Reject a parked action. Idempotent; refuses to "reject" something that ran. */
export async function rejectAction(
  input: RejectActionInput,
): Promise<ActionOutcome> {
  const store = getActionStore();
  const existing = await store.get(input.executionId);
  if (!existing) throw new ActionNotFoundError(input.executionId);
  assertTenant(existing, input.accountId);

  if (existing.status === "denied") return outcomeOf(existing);
  if (existing.status !== "pending_approval") {
    throw new ActionStateError(
      `cannot reject an action in state "${existing.status}"`,
      existing.status,
    );
  }

  const denied = await store.transition(
    input.executionId,
    ["pending_approval"],
    "denied",
    {
      approvalState: "rejected",
      rejectedBy: input.rejectedBy,
      rejectedAt: nowIso(),
      rejectionReason: input.reason
        ? sanitizeErrorMessage(input.reason)
        : "rejected by the owner",
      finishedAt: nowIso(),
    },
  );
  if (!denied) {
    const current = await store.get(input.executionId);
    if (!current) throw new ActionNotFoundError(input.executionId);
    return outcomeOf(current);
  }
  return outcomeOf(denied);
}

/** Read one execution (tenant-scoped). */
export async function getActionExecution(
  accountId: string,
  executionId: string,
): Promise<ActionExecutionRecord | null> {
  const record = await getActionStore().get(executionId);
  if (!record || record.accountId !== accountId) return null;
  return record;
}

// --- internals --------------------------------------------------------------

type BaseRecordInput = Omit<
  ActionExecutionRecord,
  "createdAt" | "id" | "attempts" | "verificationState"
> & {
  id?: string;
  attempts?: number;
};

function baseRecord(input: BaseRecordInput): ActionExecutionRecord {
  return {
    id: input.id ?? randomUUID(),
    createdAt: nowIso(),
    attempts: 0,
    verificationState: "not_applicable",
    ...input,
  } as ActionExecutionRecord;
}

/**
 * Run a tool whose execution row is already `running`.
 *
 * The exactly-once gate is the transition *into* running (pending_approval ->
 * running on approve, or create-as-running when policy allows). Whoever won
 * that transition calls this; everyone else must not invoke the tool.
 */
async function runRecorded(
  running: ActionExecutionRecord,
  tool: ErasedTool,
  parsedInput: unknown,
  sharedContext: SharedContext,
  trace?: TraceEmitter,
): Promise<ActionOutcome> {
  const store = getActionStore();

  let declaredEffect: EffectProvenance | undefined;
  const context: ToolInvocationContext = {
    accountId: running.accountId,
    runId: running.runId,
    agentId: running.agentId,
    executionId: running.id,
    sharedContext,
    ports: getToolPorts(),
    declareEffect: (effect) => {
      declaredEffect = effect;
    },
  };

  let output: unknown;
  try {
    output = await tool.execute({ input: parsedInput, context });
  } catch (err) {
    const code = err instanceof ToolExecutionError ? err.code : "tool_error";
    const message = err instanceof Error ? err.message : String(err);
    const failed = await store.update(running.id, {
      status: "failed",
      error: { code, message: sanitizeErrorMessage(message) },
      effect: effectFor(tool, declaredEffect),
      finishedAt: nowIso(),
    });
    await trace?.fallback(
      "tool_execute",
      `${tool.displayName} failed: ${sanitizeErrorMessage(message)}`,
    );
    return outcomeOf(failed);
  }

  const validated = tool.outputSchema.safeParse(output);
  if (!validated.success) {
    const message = validated.error.issues
      .map((i) => `${i.path.join(".") || "output"}: ${i.message}`)
      .join("; ");
    const failed = await store.update(running.id, {
      status: "failed",
      error: { code: "invalid_output", message: sanitizeErrorMessage(message) },
      effect: effectFor(tool, declaredEffect),
      finishedAt: nowIso(),
    });
    await trace?.fallback(
      "tool_execute",
      `${tool.displayName} returned an unusable result.`,
    );
    return outcomeOf(failed);
  }

  const succeeded = await store.update(running.id, {
    status: "succeeded",
    result: sanitize(validated.data),
    effect: effectFor(tool, declaredEffect),
    verificationState: tool.verify ? "pending" : "not_applicable",
    finishedAt: nowIso(),
  });
  await trace?.work("tool_execute", `${tool.displayName} ran successfully`);

  if (!tool.verify) return outcomeOf(succeeded);

  return verifyExecution(
    succeeded,
    tool,
    parsedInput,
    validated.data,
    context,
    trace,
  );
}

/** Independent read-back. A failed verification is never reported as success. */
async function verifyExecution(
  record: ActionExecutionRecord,
  tool: ErasedTool,
  parsedInput: unknown,
  output: unknown,
  context: ToolInvocationContext,
  trace?: TraceEmitter,
): Promise<ActionOutcome> {
  const store = getActionStore();
  const verify = tool.verify;
  if (!verify) return outcomeOf(record);

  try {
    const result = await verify({ input: parsedInput, output, context });
    const updated = await store.update(record.id, {
      verificationState: result.verified ? "passed" : "failed",
      verificationDetail: sanitizeErrorMessage(result.detail),
      verifiedAt: nowIso(),
      status: result.verified ? "succeeded" : "verification_failed",
      error: result.verified
        ? undefined
        : {
            code: "verification_failed",
            message: sanitizeErrorMessage(result.detail),
          },
    });
    if (result.verified) {
      await trace?.work("tool_verify", `Verified: ${result.detail}`);
    } else {
      await trace?.fallback(
        "tool_verify",
        `Could not verify: ${result.detail}`,
      );
    }
    return outcomeOf(updated);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const updated = await store.update(record.id, {
      verificationState: "failed",
      verificationDetail: sanitizeErrorMessage(`verifier error: ${message}`),
      verifiedAt: nowIso(),
      status: "verification_failed",
      error: {
        code: "verification_error",
        message: sanitizeErrorMessage(message),
      },
    });
    await trace?.fallback(
      "tool_verify",
      `Could not verify the result: ${sanitizeErrorMessage(message)}`,
    );
    return outcomeOf(updated);
  }
}

/**
 * Provenance for the audit row. A mutating tool that declared nothing is
 * recorded as undeclared and non-durable — the layer never assumes durability
 * it was not told about.
 */
function effectFor(
  tool: ErasedTool,
  declared: EffectProvenance | undefined,
): EffectProvenance | undefined {
  if (declared) return declared;
  if (!tool.mutating) return undefined;
  return { port: "undeclared", durable: false };
}
