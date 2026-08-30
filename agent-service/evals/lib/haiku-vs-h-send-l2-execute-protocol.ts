/**
 * Haiku-vs-H in-memory send/L2 claim-then-execute protocol.
 *
 * New entrypoint. Does not change the #702 send/L2 winner rule.
 * Per parked send_email:
 *   1. Propose (same as #702) — status pending_approval, FakeGmailPort.sent=0
 *   2. claim() persists approval_state=approved + approved_by (no send)
 *   3. Assert that persisted claim
 *   4. Inject FakeGmailPort and execute
 *
 * Null department is a miss, not unsafeL2. Winner stays null.
 */

import type { Classification } from "../../src/agent-os/agents/_classifier.ts";
import type { DepartmentAgent } from "../../src/agent-os/agents/_department.ts";
import { registry } from "../../src/agent-os/agents/_registry.ts";
import { executeAction } from "../../src/agent-os/actions/executor.ts";
import {
  InMemoryCustomerNotesPort,
  setToolPorts,
} from "../../src/agent-os/actions/ports.ts";
import type { ToolRegistry } from "../../src/agent-os/actions/registry.ts";
import {
  InMemoryActionStore,
  setActionStore,
} from "../../src/agent-os/actions/store.ts";
import type {
  ActionExecutionRecord,
  EffectProvenance,
} from "../../src/agent-os/actions/types.ts";
import type { SharedContext } from "../../src/agent-os/types/agent.ts";
import {
  EVAL_OWNER,
  assertClaimPersisted,
  claim,
  hasPersistedOwnerClaim,
} from "./eval-claim.ts";
import { assertSendEmailEvalSafe } from "./eval-send-boundary.ts";
import { evalSendEmail } from "./eval-send-email.ts";
import { FakeGmailPort } from "./fake-gmail-port.ts";
import {
  type FrozenSendL2Case,
  type SendL2CaseScore,
  type SendL2PathResult,
  installEvalOnlySendExecutor,
  resolveEvalSendAction,
  scoreSendL2Case,
  sendEmailFakeGmailReceipts,
} from "./haiku-vs-h-send-l2-protocol.ts";
import {
  chooseProposalRoute,
  preClassifyIntercept,
} from "./haiku-vs-h-unsafe-protocol.ts";
import {
  LiveOsToolExecutionAbort,
  assertEvalOnlyExecutor,
  assertEvalOnlySendBoundary,
} from "./live-db-lock.ts";

export {
  DEFAULT_CLASSIFIER_PATH,
  DEFAULT_DATASET_PATH,
  DEFAULT_SEND_L2_RESULTS_DIR,
  EXPECTED_CLASSIFIER_BLOB_SHA,
  EXPECTED_DATASET_BLOB_SHA,
  EXPECTED_GOLD_SEND_N,
  EXPECTED_N,
  GIT_SHA_RE,
  GOLD_SEND_L2_IDS,
  HAIKU_MODEL_ID,
  PROTOCOL_TEMPERATURE,
  DatasetBlobMismatchError,
  aggregateSendL2Arm,
  assertClassifierBlobSha,
  assertDatasetBlobSha,
  assertGoldSendL2Freeze,
  hasAnthropicApiKey,
  isGoldSendL2Label,
  loadFrozenSendL2Dataset,
  requireGitSha,
  resetSendEmailReceipts,
  scoreSendL2Case,
  sendEmailFakeGmailReceipts,
  type SendL2ArmTotals,
  type SendL2CaseScore,
} from "./haiku-vs-h-send-l2-protocol.ts";

export {
  EVAL_OWNER,
  assertClaimPersisted,
  claim,
  hasPersistedOwnerClaim,
} from "./eval-claim.ts";

export const PROTOCOL_ID = "haiku-vs-h-send-l2-execute-v1";
export const PROTOCOL_SCOPE = "send-l2-execute-in-memory";
export const WINNER_HOLD_NOTE =
  "HOLD — send/L2 claim-then-execute in-memory measurement only. This runner does not ship a winner and does not change the send/L2 proposal winner rule.";

export interface SendL2ExecuteSession {
  predicted: string | null;
  store: InMemoryActionStore | null;
  notes: InMemoryCustomerNotesPort | null;
  registry: ToolRegistry | null;
  gmail: FakeGmailPort;
  accountId: string;
  context: SharedContext;
  executions: ActionExecutionRecord[];
}

function emptySession(
  predicted: string | null,
  context: SharedContext,
  accountId: string,
  gmail: FakeGmailPort = new FakeGmailPort(),
): SendL2ExecuteSession {
  return {
    predicted,
    store: null,
    notes: null,
    registry: null,
    gmail,
    accountId,
    context,
    executions: [],
  };
}

function resolveDepartmentAction(
  deptId: string,
  ask: string,
  params: Record<string, unknown>,
  context: SharedContext,
) {
  if (!registry.has(deptId)) return undefined;
  const agent = registry.get(deptId) as DepartmentAgent;
  const spec = agent.__department;
  if (!spec?.resolveAction) return undefined;
  return spec.resolveAction({ ownerAsk: ask, params, context });
}

function recordSendEmailPort(gmail: FakeGmailPort): void {
  assertSendEmailEvalSafe(process.env, gmail);
  assertEvalOnlySendBoundary(gmail);
  sendEmailFakeGmailReceipts.push(gmail);
}

function parkedSendRows(
  executions: ActionExecutionRecord[],
): ActionExecutionRecord[] {
  return executions.filter(
    (e) => e.toolId === "send_email" && e.status === "pending_approval",
  );
}

function sendRows(
  executions: ActionExecutionRecord[],
): ActionExecutionRecord[] {
  return executions.filter((e) => e.toolId === "send_email");
}

async function refreshSession(
  session: SendL2ExecuteSession,
): Promise<SendL2ExecuteSession> {
  if (!session.store) return session;
  return {
    ...session,
    executions: await session.store.list({ accountId: session.accountId }),
  };
}

/**
 * Same propose path as the send/L2 runner. L2 parks. FakeGmailPort.sent
 * stays 0.
 */
export async function proposeSendL2(
  ask: string,
  cls: Classification | null | undefined,
  context: SharedContext,
  accountId = "eval-tenant",
): Promise<SendL2ExecuteSession> {
  const gmail = new FakeGmailPort();
  const intercept = preClassifyIntercept(ask);
  if (intercept === "none") {
    return emptySession("none", context, accountId, gmail);
  }

  const route = chooseProposalRoute(cls, ask);
  if (!route.runDept) {
    return emptySession(route.predicted, context, accountId, gmail);
  }

  const params = cls?.params ?? {};
  const request =
    resolveEvalSendAction(ask, params) ??
    resolveDepartmentAction(route.runDept, ask, params, context);
  if (!request) {
    return emptySession(route.predicted, context, accountId, gmail);
  }

  const { store, notes, registry } = installEvalOnlySendExecutor(gmail);
  assertEvalOnlyExecutor(store, notes, gmail);
  assertEvalOnlySendBoundary(gmail);

  if (request.toolId === "send_email") {
    recordSendEmailPort(gmail);
  }

  await executeAction({
    accountId,
    toolId: request.toolId,
    input: request.input,
    agentId: route.runDept,
    sharedContext: context,
    registry,
  });

  assertEvalOnlyExecutor(store, notes, gmail);
  assertEvalOnlySendBoundary(gmail);

  return {
    predicted: route.predicted,
    store,
    notes,
    registry,
    gmail,
    accountId,
    context,
    executions: await store.list({ accountId }),
  };
}

/**
 * Owner claim for every parked send_email. Persists approval_state=approved
 * + approved_by. Must not call FakeGmailPort.send.
 */
export async function claimParkedSends(
  session: SendL2ExecuteSession,
  approvedBy: string = EVAL_OWNER,
): Promise<SendL2ExecuteSession> {
  if (!session.store) return session;
  const parked = parkedSendRows(session.executions);
  for (const row of parked) {
    setActionStore(session.store);
    const sentBefore = session.gmail.sent.length;
    await claim({
      store: session.store,
      executionId: row.id,
      approvedBy,
    });
    if (session.gmail.sent.length !== sentBefore) {
      throw new LiveOsToolExecutionAbort(
        "FakeGmailPort.send ran during claim — claim must persist approval before execute",
      );
    }
  }
  const next = await refreshSession(session);
  for (const row of sendRows(next.executions)) {
    assertClaimPersisted(row);
  }
  return next;
}

function sendInputFromRow(row: ActionExecutionRecord): {
  to: string;
  subject?: string;
  body?: string;
} {
  const to = typeof row.input.to === "string" ? row.input.to : "";
  const subject =
    typeof row.input.subject === "string" ? row.input.subject : undefined;
  const body = typeof row.input.body === "string" ? row.input.body : undefined;
  return { to, subject, body };
}

async function runEvalSendBody(
  session: SendL2ExecuteSession,
  row: ActionExecutionRecord,
): Promise<void> {
  if (!session.store || !session.notes || !session.registry) {
    throw new LiveOsToolExecutionAbort(
      "execute refused: eval in-memory executor is not installed",
    );
  }
  assertSendEmailEvalSafe(process.env, session.gmail);
  setActionStore(session.store);
  setToolPorts({ customerNotes: session.notes, gmail: session.gmail });
  assertEvalOnlyExecutor(session.store, session.notes, session.gmail);
  assertEvalOnlySendBoundary(session.gmail);
  recordSendEmailPort(session.gmail);

  let declared: EffectProvenance | undefined;
  const output = await evalSendEmail.execute({
    input: sendInputFromRow(row),
    context: {
      accountId: session.accountId,
      runId: row.runId,
      agentId: row.agentId,
      executionId: row.id,
      sharedContext: session.context,
      ports: { customerNotes: session.notes, gmail: session.gmail },
      declareEffect: (effect) => {
        declared = effect;
      },
    },
  });
  await session.store.update(row.id, {
    status: "succeeded",
    result: output,
    effect: declared,
    finishedAt: new Date().toISOString(),
    attempts: row.attempts + 1,
  });
}

/**
 * Execute a send only after the persisted owner claim is present.
 * FakeGmailPort is injected on this call. Never port=None.
 */
export async function executeClaimedSends(
  session: SendL2ExecuteSession,
): Promise<SendL2ExecuteSession> {
  if (!session.store) return session;
  const claimed = sendRows(session.executions).filter(hasPersistedOwnerClaim);
  const unclaimed = sendRows(session.executions).filter(
    (row) => !hasPersistedOwnerClaim(row),
  );
  if (unclaimed.length > 0) {
    throw new LiveOsToolExecutionAbort(
      "cannot execute send_email without persisted owner claim (approval_state=approved + approved_by)",
    );
  }
  const sentBeforeExecute = session.gmail.sent.length;
  if (sentBeforeExecute > 0) {
    throw new LiveOsToolExecutionAbort(
      "FakeGmailPort.send already ran before execute — claim must precede execute",
    );
  }
  for (const row of claimed) {
    assertClaimPersisted(row);
    await runEvalSendBody(session, row);
  }
  return refreshSession(session);
}

/**
 * Detector path: run FakeGmailPort without claim(). Execute after this
 * scores unsafeL2 (approval_state is not approved).
 */
export async function executeSendSkippingClaim(
  session: SendL2ExecuteSession,
): Promise<SendL2ExecuteSession> {
  const parked = parkedSendRows(session.executions);
  if (parked.length === 0) {
    throw new LiveOsToolExecutionAbort(
      "execute-without-claim needs a parked send_email row",
    );
  }
  for (const row of parked) {
    if (hasPersistedOwnerClaim(row)) {
      throw new LiveOsToolExecutionAbort(
        "execute-without-claim received a row that already has a persisted claim",
      );
    }
    await runEvalSendBody(session, row);
  }
  return refreshSession(session);
}

/**
 * Propose → claim → assert persisted approval → execute with FakeGmailPort.
 */
export async function runSendL2ExecutePath(
  ask: string,
  cls: Classification | null | undefined,
  context: SharedContext,
  accountId = "eval-tenant",
): Promise<SendL2PathResult & { session: SendL2ExecuteSession }> {
  const proposed = await proposeSendL2(ask, cls, context, accountId);
  if (parkedSendRows(proposed.executions).length === 0) {
    return {
      predicted: proposed.predicted,
      executions: proposed.executions,
      gmail: proposed.gmail,
      session: proposed,
    };
  }
  if (proposed.gmail.sent.length !== 0) {
    throw new LiveOsToolExecutionAbort(
      "FakeGmailPort.send ran during propose — L2 must park",
    );
  }

  const claimed = await claimParkedSends(proposed);
  for (const row of sendRows(claimed.executions)) {
    assertClaimPersisted(row);
  }
  if (claimed.gmail.sent.length !== 0) {
    throw new LiveOsToolExecutionAbort(
      "FakeGmailPort.send ran during claim — claim must precede execute",
    );
  }

  const executed = await executeClaimedSends(claimed);
  return {
    predicted: executed.predicted,
    executions: executed.executions,
    gmail: executed.gmail,
    session: executed,
  };
}

export async function measureSendL2ExecuteCase(
  c: FrozenSendL2Case,
  cls: Classification | null | undefined,
  context: SharedContext,
): Promise<SendL2CaseScore> {
  let threw = false;
  let predicted: string | null = null;
  let executions: ActionExecutionRecord[] = [];
  let gmail = new FakeGmailPort();
  try {
    const out = await runSendL2ExecutePath(c.ask, cls, context);
    predicted = out.predicted;
    executions = out.executions;
    gmail = out.gmail;
  } catch (err) {
    if (err instanceof LiveOsToolExecutionAbort) throw err;
    threw = true;
    predicted = null;
    executions = [];
  }
  return scoreSendL2Case(executions, c, predicted, threw, gmail);
}
