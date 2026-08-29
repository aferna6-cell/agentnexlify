"""Agent OS action layer — the data plane half.

The engine (``agent-service/src/agent-os/actions/``) owns the tool registry,
the risk policy and the executor. It is pure compute: it returns the execution
records it created and the writes it made, and this module persists them into
``os_tool_executions`` and applies them to the tenant's own records.

Three responsibilities:

1. **Persist** what a turn did — every attempt becomes an auditable row.
2. **Apply** an execution's internal writes (today: customer notes onto
   ``leads.notes``) and verify them by reading the row back, so a note that did
   not land downgrades its execution to ``verification_failed`` rather than
   sitting in the history as a success.
3. **Approve / reject** a parked action. Approval is at-most-once: the status
   moves out of ``pending_approval`` with a conditional update *before* the
   engine is called, so a double-clicked approval cannot run a tool twice.

Distinct from ``backend/services/os_actions/``: that package fires a channel
handler when the owner approves a *deliverable*. This one records and gates an
agent's own *tool* choice mid-run.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

#: Statuses an execution can be in. Mirrors the engine's state machine
#: (``agent-service/src/agent-os/actions/types.ts``) and the table's CHECK.
#: Status is parked / running / terminal only. ``approved`` lives on
#: ``approval_state``, never here.
STATUSES = (
    "pending_approval",
    "running",
    "succeeded",
    "failed",
    "verification_failed",
    "denied",
    "cancelled",
)

#: Risk level 2+ (external communication / high impact). An L2+ action
#: cannot be queued or treated as sent if its audit row cannot be written.
RISK_FAIL_CLOSED = 2


class ToolExecutionAuditError(RuntimeError):
    """L2+ audit row could not be written — refuse to queue or send."""

#: No further transition is possible from these.
TERMINAL_STATUSES = (
    "succeeded",
    "failed",
    "verification_failed",
    "denied",
    "cancelled",
)


class ToolExecutionStateError(RuntimeError):
    """The requested transition is impossible from the row's current state."""

    def __init__(self, message: str, status: str):
        super().__init__(message)
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _int_or(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def to_row(execution: dict, client_id: str, agent_run_id: str | None) -> dict:
    """Map one engine execution record to an ``os_tool_executions`` row.

    Only fields the engine is authoritative for are copied; anything unknown is
    dropped rather than guessed. The engine has already sanitized ``input`` and
    ``result`` (secret-looking keys redacted, oversized payloads truncated).
    """
    return {
        "id": execution.get("id"),
        "client_id": client_id,
        "agent_run_id": agent_run_id,
        "engine_run_id": execution.get("runId"),
        "agent_id": execution.get("agentId"),
        "tool_id": execution.get("toolId"),
        "risk_level": _int_or(execution.get("riskLevel"), 3),
        "mutating": bool(execution.get("mutating")),
        "requires_approval": bool(execution.get("requiresApproval")),
        "approval_state": execution.get("approvalState") or "not_required",
        "approved_by": execution.get("approvedBy"),
        "approved_at": execution.get("approvedAt"),
        "rejected_by": execution.get("rejectedBy"),
        "rejected_at": execution.get("rejectedAt"),
        "rejection_reason": execution.get("rejectionReason"),
        "status": execution.get("status") or "pending_approval",
        "input": execution.get("input") or {},
        "result": execution.get("result"),
        "error": execution.get("error"),
        "verification_state": execution.get("verificationState") or "not_applicable",
        "verification_detail": execution.get("verificationDetail"),
        "verified_at": execution.get("verifiedAt"),
        "policy_reason": execution.get("policyReason") or "",
        "attempts": _int_or(execution.get("attempts"), 0),
        "idempotency_key": execution.get("idempotencyKey"),
        "effect": execution.get("effect"),
        "started_at": execution.get("startedAt"),
        "finished_at": execution.get("finishedAt"),
        "updated_at": _now(),
    }


def _is_fail_closed(row: dict) -> bool:
    return _int_or(row.get("risk_level"), 3) >= RISK_FAIL_CLOSED


def persist_tool_executions(
    db: Any,
    client_id: str,
    agent_run_id: str | None,
    record: dict,
) -> list[dict]:
    """Persist a turn's tool executions and apply the writes they made.

    L0/L1 writes are best-effort: a missing audit row is logged and the
    owner's turn still completes. L2+ is fail-closed — if the audit row
    cannot be written the action is not queued or treated as sent.
    """
    executions = record.get("toolExecutions") or []
    if not executions:
        return []

    rows = [to_row(e, client_id, agent_run_id) for e in executions if e.get("id")]
    if not rows:
        return []

    try:
        inserted = (
            tenant_table(db, "os_tool_executions", client_id).insert(rows).execute().data
            or []
        )
    except Exception as exc:
        if any(_is_fail_closed(row) for row in rows):
            raise ToolExecutionAuditError(
                "L2+ tool execution could not be written to os_tool_executions; "
                "refusing to queue or send"
            ) from exc
        logger.exception("os_tool_executions: L0/L1 persist failed")
        return []

    inserted_ids = {row.get("id") for row in inserted}
    missing_l2 = [
        row["id"] for row in rows if _is_fail_closed(row) and row["id"] not in inserted_ids
    ]
    if missing_l2:
        raise ToolExecutionAuditError(
            f"L2+ tool execution(s) missing from persist: {missing_l2}; "
            "refusing to queue or send"
        )

    notes = record.get("customerNotes") or []
    if notes:
        apply_customer_notes(db, client_id, notes, executions)

    return inserted


def apply_customer_notes(
    db: Any,
    client_id: str,
    notes: list[dict],
    executions: list[dict] | None = None,
) -> list[dict]:
    """Append internal notes written this turn onto the customers' lead rows.

    Each note is applied and then read back. A note that cannot be applied (the
    lead is gone, the write failed) marks its execution ``verification_failed``,
    so the audit trail never claims a write that is not there.

    Returns one ``{"note_id", "applied", "detail"}`` per note.
    """
    outcomes: list[dict] = []
    for note in notes:
        note_id = note.get("id")
        customer_id = note.get("customerId")
        text = (note.get("note") or "").strip()
        if not (note_id and customer_id and text):
            outcomes.append(
                {"note_id": note_id, "applied": False, "detail": "incomplete note"}
            )
            continue

        applied, detail = _append_lead_note(db, client_id, customer_id, note, text)
        outcomes.append({"note_id": note_id, "applied": applied, "detail": detail})
        if not applied:
            _mark_note_execution_unverified(db, client_id, note_id, detail, executions)

    return outcomes


def _append_lead_note(
    db: Any, client_id: str, lead_id: str, note: dict, text: str
) -> tuple[bool, str]:
    """Append one note to ``leads.notes`` and confirm it by reading it back."""
    leads = tenant_table(db, "leads", client_id)
    try:
        found = leads.select("id, notes").eq("id", lead_id).limit(1).execute().data or []
    except Exception:
        logger.exception("os_tool_executions: lead read failed lead_id=%s", lead_id)
        return False, "could not read the customer record"

    if not found:
        return False, f"customer {lead_id} no longer exists"

    stamp = (note.get("createdAt") or _now())[:10]
    source = note.get("source") or "agent_os"
    entry = f"[{stamp}] ({source}) {text}"
    existing = (found[0].get("notes") or "").strip()
    merged = f"{existing}\n{entry}".strip() if existing else entry

    try:
        leads.update({"notes": merged}).eq("id", lead_id).execute()
    except Exception:
        logger.exception("os_tool_executions: note write failed lead_id=%s", lead_id)
        return False, "the note could not be saved to the customer record"

    # Independent read-back: the write is only reported as done once it is there.
    try:
        after = leads.select("id, notes").eq("id", lead_id).limit(1).execute().data or []
    except Exception:
        logger.exception("os_tool_executions: note read-back failed lead_id=%s", lead_id)
        return False, "the note could not be confirmed on the customer record"

    if not after or text not in (after[0].get("notes") or ""):
        return False, "the note was not present when the record was read back"
    return True, "note confirmed on the customer record"


def _mark_note_execution_unverified(
    db: Any,
    client_id: str,
    note_id: str,
    detail: str,
    executions: list[dict] | None,
) -> None:
    """Downgrade the execution that produced a note that did not land."""
    execution_id = None
    for execution in executions or []:
        result = execution.get("result")
        if isinstance(result, dict) and result.get("noteId") == note_id:
            execution_id = execution.get("id")
            break
    if not execution_id:
        return
    try:
        tenant_table(db, "os_tool_executions", client_id).update(
            {
                "status": "verification_failed",
                "verification_state": "failed",
                "verification_detail": detail,
                "verified_at": _now(),
                "error": {"code": "verification_failed", "message": detail},
                "updated_at": _now(),
            }
        ).eq("id", execution_id).execute()
    except Exception:
        logger.exception(
            "os_tool_executions: could not downgrade execution %s", execution_id
        )


# --- reads ------------------------------------------------------------------


def list_tool_executions(
    db: Any,
    client_id: str,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Recent executions for one tenant, newest first."""
    query = tenant_table(db, "os_tool_executions", client_id).select("*")
    if status:
        query = query.eq("status", status)
    rows = query.order("created_at", desc=True).limit(limit).execute().data
    return rows or []


def get_tool_execution(db: Any, client_id: str, execution_id: str) -> dict | None:
    rows = (
        tenant_table(db, "os_tool_executions", client_id)
        .select("*")
        .eq("id", execution_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


# --- approval ---------------------------------------------------------------


def claim_for_execution(db: Any, client_id: str, execution_id: str) -> dict | None:
    """Move a pending row to ``running``, or return None if it was not pending.

    This is the at-most-once gate. It is a conditional update — the status
    filter is part of the statement — so of two concurrent approvals exactly one
    gets a row back and the other gets None.
    """
    updated = (
        tenant_table(db, "os_tool_executions", client_id)
        .update({"status": "running", "started_at": _now(), "updated_at": _now()})
        .eq("id", execution_id)
        .eq("status", "pending_approval")
        .execute()
        .data
    )
    return updated[0] if updated else None


def record_execution_outcome(
    db: Any, client_id: str, execution: dict
) -> dict | None:
    """Write the engine's terminal record back onto the claimed row."""
    patch = to_row(execution, client_id, None)
    # The row already carries its identity and lineage; only the outcome moves.
    for immutable in ("id", "client_id", "agent_run_id", "engine_run_id", "agent_id", "tool_id", "created_at"):
        patch.pop(immutable, None)
    updated = (
        tenant_table(db, "os_tool_executions", client_id)
        .update(patch)
        .eq("id", execution.get("id"))
        .execute()
        .data
    )
    return updated[0] if updated else None


def mark_engine_unavailable(db: Any, client_id: str, execution_id: str, detail: str) -> None:
    """Record that the engine did not answer, leaving the row in ``running``.

    The outcome is genuinely unknown, so the row is not moved to a terminal
    state and is not retried automatically — that is the only choice that
    cannot double-execute a side effect. It shows up in the queue as a stuck
    ``running`` row with the reason attached.
    """
    try:
        tenant_table(db, "os_tool_executions", client_id).update(
            {
                "error": {"code": "engine_unavailable", "message": detail[:500]},
                "updated_at": _now(),
            }
        ).eq("id", execution_id).execute()
    except Exception:
        logger.exception(
            "os_tool_executions: could not record engine outage for %s", execution_id
        )


def reject_tool_execution(
    db: Any,
    client_id: str,
    execution_id: str,
    *,
    rejected_by: str,
    reason: str | None = None,
) -> dict:
    """Reject a parked action. Idempotent; refuses to reject one that ran."""
    current = get_tool_execution(db, client_id, execution_id)
    if current is None:
        raise LookupError(execution_id)
    if current["status"] == "denied":
        return current
    if current["status"] != "pending_approval":
        raise ToolExecutionStateError(
            f"cannot reject an action in state '{current['status']}'", current["status"]
        )

    updated = (
        tenant_table(db, "os_tool_executions", client_id)
        .update(
            {
                "status": "denied",
                "approval_state": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": _now(),
                "rejection_reason": (reason or "rejected by the owner")[:500],
                "finished_at": _now(),
                "updated_at": _now(),
            }
        )
        .eq("id", execution_id)
        .eq("status", "pending_approval")
        .execute()
        .data
    )
    if not updated:
        # Someone else decided it first; return whatever it settled on.
        return get_tool_execution(db, client_id, execution_id) or current
    return updated[0]
