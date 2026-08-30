/**
 * Eval-only owner claim.
 *
 * Mirrors the #700 production claim contract (pending_approval → running
 * with approval_state=approved and approved_by on the same write) against
 * InMemoryActionStore. This is not the live table writer and it does not
 * execute the tool body — FakeGmailPort must stay at sent=0 until a later
 * execute call.
 *
 * Callers must go through claim(). Do not store.update the approval axis
 * as a shortcut.
 */

import type { InMemoryActionStore } from "../../src/agent-os/actions/store.ts";
import type { ActionExecutionRecord } from "../../src/agent-os/actions/types.ts";

export const EVAL_OWNER = "eval-owner";

export class ClaimRequiredError extends Error {
  constructor(reason: string) {
    super(reason);
    this.name = "ClaimRequiredError";
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

/** True when the #700 claim axis is persisted on the in-memory row. */
export function hasPersistedOwnerClaim(row: ActionExecutionRecord): boolean {
  return row.approvalState === "approved" && Boolean(row.approvedBy);
}

export function assertClaimPersisted(row: ActionExecutionRecord): void {
  if (!hasPersistedOwnerClaim(row)) {
    throw new ClaimRequiredError(
      "owner claim did not persist approval_state=approved and approved_by",
    );
  }
}

/**
 * Production-shaped claim: conditional pending_approval → running, and
 * when approvedBy is present write approval_state=approved + approved_by
 * on that same transition. Does not invoke any send port.
 */
export async function claim(input: {
  store: InMemoryActionStore;
  executionId: string;
  approvedBy: string;
}): Promise<ActionExecutionRecord> {
  const approvedBy =
    typeof input.approvedBy === "string" ? input.approvedBy.trim() : "";
  if (!approvedBy) {
    throw new ClaimRequiredError(
      "claim requires approved_by (owner) — refusing a claim that would not persist approval_state=approved",
    );
  }

  const existing = await input.store.get(input.executionId);
  if (!existing) {
    throw new ClaimRequiredError(
      `claim: unknown execution "${input.executionId}"`,
    );
  }

  const claimed = await input.store.transition(
    input.executionId,
    ["pending_approval"],
    "running",
    {
      approvalState: "approved",
      approvedBy,
      approvedAt: nowIso(),
      startedAt: nowIso(),
    },
  );
  if (!claimed) {
    throw new ClaimRequiredError(
      `claim lost — execution "${input.executionId}" was not pending_approval`,
    );
  }
  assertClaimPersisted(claimed);
  return claimed;
}
