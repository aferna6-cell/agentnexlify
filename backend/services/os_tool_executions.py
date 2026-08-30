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
   4. **Re-drive a claimed row** through ``_run_data_plane_tool`` with an injected
   mailbox port. A timeout or lost response stays non-terminal; a later
   re-drive rfc822msgid-adopts. Production ``send_email`` uses
   ``os_tools.run_tool`` + ``GmailMailboxPort``, gated by
   ``SEND_EMAIL_ENABLED`` (default off) and Sales-only.

Distinct from ``backend/services/os_actions/``: that package fires a channel
handler when the owner approves a *deliverable*. This one records and gates an
agent's own *tool* choice mid-run. The two tables stay dual — they are not
merged.
"""

import importlib.util
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
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


class ToolExecutionIdempotencyConflict(RuntimeError):
    """A second create reused an L2 idempotency key — not a second row."""

    def __init__(self, existing: dict):
        super().__init__("idempotency key already used")
        self.existing = existing

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
        "idempotency_key": _normalized_idempotency_key(execution.get("idempotencyKey")),
        "effect": execution.get("effect"),
        "started_at": execution.get("startedAt"),
        "finished_at": execution.get("finishedAt"),
        "updated_at": _now(),
    }


def _normalized_idempotency_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip()
    return key or None


def _is_fail_closed(row: dict) -> bool:
    return _int_or(row.get("risk_level"), 3) >= RISK_FAIL_CLOSED


def _requires_idempotency_key(row: dict) -> bool:
    """L2+ or anything parked for approval must carry a replay key."""
    return _is_fail_closed(row) or bool(row.get("requires_approval"))


def find_by_idempotency_key(
    db: Any, client_id: str, tool_id: str, key: str
) -> dict | None:
    normalized = _normalized_idempotency_key(key)
    if not normalized:
        return None
    rows = (
        tenant_table(db, "os_tool_executions", client_id)
        .select("*")
        .eq("tool_id", tool_id)
        .eq("idempotency_key", normalized)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


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

    for row in rows:
        if _requires_idempotency_key(row) and not row.get("idempotency_key"):
            raise ToolExecutionAuditError(
                "L2+ tool execution requires a non-empty idempotency_key; "
                "refusing to queue or send"
            )

    reused: list[dict] = []
    to_insert: list[dict] = []
    for row in rows:
        key = row.get("idempotency_key")
        if key:
            try:
                existing = find_by_idempotency_key(db, client_id, row["tool_id"], key)
            except Exception:
                existing = None
            if existing:
                reused.append(existing)
                continue
        to_insert.append(row)

    inserted: list[dict] = []
    if to_insert:
        try:
            inserted = (
                tenant_table(db, "os_tool_executions", client_id)
                .insert(to_insert)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            try:
                recovered = _recover_duplicate_inserts(db, client_id, to_insert)
            except Exception:
                recovered = None
            if recovered is not None:
                inserted = recovered
            elif any(_is_fail_closed(row) for row in to_insert):
                raise ToolExecutionAuditError(
                    "L2+ tool execution could not be written to os_tool_executions; "
                    "refusing to queue or send"
                ) from exc
            else:
                logger.exception("os_tool_executions: L0/L1 persist failed")
                return reused

        inserted_ids = {row.get("id") for row in inserted}
        missing_l2 = [
            row["id"]
            for row in to_insert
            if _is_fail_closed(row) and row["id"] not in inserted_ids
        ]
        if missing_l2:
            raise ToolExecutionAuditError(
                f"L2+ tool execution(s) missing from persist: {missing_l2}; "
                "refusing to queue or send"
            )

    notes = record.get("customerNotes") or []
    if notes:
        apply_customer_notes(db, client_id, notes, executions)

    return reused + inserted


def _recover_duplicate_inserts(
    db: Any, client_id: str, rows: list[dict]
) -> list[dict] | None:
    """A unique-index race: every keyed row must already exist, or this is a real write failure."""
    recovered: list[dict] = []
    for row in rows:
        key = row.get("idempotency_key")
        existing = (
            find_by_idempotency_key(db, client_id, row["tool_id"], key) if key else None
        )
        if existing is None:
            return None
        recovered.append(existing)
    return recovered


def propose_tool_execution(
    db: Any,
    client_id: str,
    agent_run_id: str | None,
    execution: dict,
    *,
    conflict: str = "reuse",
) -> dict | None:
    """Create one parked/recorded execution. Replay of the same key is a no-op or 409."""
    key = _normalized_idempotency_key(execution.get("idempotencyKey"))
    tool_id = execution.get("toolId")
    if key and tool_id:
        existing = find_by_idempotency_key(db, client_id, tool_id, key)
        if existing:
            if conflict == "raise":
                raise ToolExecutionIdempotencyConflict(existing)
            return existing
    rows = persist_tool_executions(
        db, client_id, agent_run_id, {"toolExecutions": [execution]}
    )
    return rows[0] if rows else None


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


_REDACTED_INPUT = {"redacted": True}
_SENSITIVE_RESULT_KEYS = frozenset(
    {"recipient", "to", "cc", "bcc", "subject", "body", "html", "text", "message"}
)


def present_tool_execution(row: dict | None, *, owner: bool) -> dict | None:
    """Owners see raw input for approval. Everyone else gets a redacted copy."""
    if row is None or owner:
        return row
    visible = dict(row)
    visible["input"] = dict(_REDACTED_INPUT)
    result = visible.get("result")
    if isinstance(result, dict):
        visible["result"] = {
            key: value
            for key, value in result.items()
            if str(key).lower() not in _SENSITIVE_RESULT_KEYS
        }
    return visible


# --- approval ---------------------------------------------------------------


def claim_for_execution(
    db: Any,
    client_id: str,
    execution_id: str,
    approved_by: str | None = None,
) -> dict | None:
    """Move a pending row to ``running``, or return None if it was not pending.

    This is the at-most-once gate. It is a conditional update — the status
    filter is part of the statement — so of two concurrent approvals exactly one
    gets a row back and the other gets None.

    Status stays parked/running/terminal. When ``approved_by`` is the owner
    who approved, ``approval_state`` moves ``pending → approved`` on this
    same write so a later data-plane success cannot sit as pending with no
    actor.
    """
    patch = {"status": "running", "started_at": _now(), "updated_at": _now()}
    if approved_by:
        patch["approval_state"] = "approved"
        patch["approved_by"] = approved_by
        patch["approved_at"] = _now()
    updated = (
        tenant_table(db, "os_tool_executions", client_id)
        .update(patch)
        .eq("id", execution_id)
        .eq("status", "pending_approval")
        .execute()
        .data
    )
    return updated[0] if updated else None


def record_execution_outcome(
    db: Any, client_id: str, execution: dict
) -> dict | None:
    """Write the engine's terminal record back onto the claimed row.

    ``to_row`` defaults a missing approval axis to ``not_required``. A
    data-plane success (send_email) omits that axis — the owner-approve
    claim already wrote ``approved`` + ``approved_by``. Do not stamp
    ``not_required`` or wipe the actor over that write. Status and
    approval_state stay separate columns.
    """
    patch = to_row(execution, client_id, None)
    # The row already carries its identity and lineage; only the outcome moves.
    for immutable in ("id", "client_id", "agent_run_id", "engine_run_id", "agent_id", "tool_id", "created_at"):
        patch.pop(immutable, None)
    if "approvalState" not in execution and "approval_state" not in execution:
        patch.pop("approval_state", None)
        if "approvedBy" not in execution and "approved_by" not in execution:
            patch.pop("approved_by", None)
            patch.pop("approved_at", None)
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


_RFC822_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
_NORMALIZE_EMAIL = None
_EMAIL_TOOL_IDS = frozenset({"send_email"})


def rfc822_msgid_for(execution_id: str) -> str:
    """Stable Message-ID fingerprint for one execution. Used to adopt, not to send."""
    safe = _RFC822_SAFE.sub("", str(execution_id))
    return f"aos-{safe}@actions.agentnexlify"


def apply_unknown_send_outcome(
    db: Any, client_id: str, execution_id: str, detail: str
) -> dict | None:
    """Correct write for a lost/timeout send: stay non-terminal, no finished_at."""
    mark_engine_unavailable(db, client_id, execution_id, detail)
    return get_tool_execution(db, client_id, execution_id)


def _normalize_email(raw) -> str | None:
    """Load recipients.normalize_email without importing ``os_actions``."""
    global _NORMALIZE_EMAIL
    if _NORMALIZE_EMAIL is None:
        path = Path(__file__).resolve().parent / "os_actions" / "recipients.py"
        spec = importlib.util.spec_from_file_location(
            "os_tool_executions_recipients", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _NORMALIZE_EMAIL = module.normalize_email
    return _NORMALIZE_EMAIL(raw)


def email_recipient_from_input(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    if "to" in payload:
        return payload.get("to")
    return None


def requires_preclaim_email_check(row: dict) -> bool:
    """send_email (or the send_email input shape) is checked before the claim is spent."""
    if row.get("tool_id") in _EMAIL_TOOL_IDS:
        return True
    payload = row.get("input") or {}
    return isinstance(payload, dict) and "to" in payload


def input_passes_python_email_gate(payload: Any) -> bool:
    return _normalize_email(email_recipient_from_input(payload)) is not None


def validate_before_claim(
    db: Any, client_id: str, execution_id: str
) -> tuple[dict | None, str | None]:
    """Schema check that must run before ``claim_for_execution``.

    Returns ``(row, error)``. A Zod-pass / Python-fail email must return
    ``invalid_email`` so the only approval claim is not burned.
    """
    row = get_tool_execution(db, client_id, execution_id)
    if row is None:
        return None, "not_found"
    if requires_preclaim_email_check(row) and not input_passes_python_email_gate(
        row.get("input")
    ):
        return row, "invalid_email"
    return row, None


def claim_if_input_valid(db: Any, client_id: str, execution_id: str) -> dict | None:
    """Validate then claim. A Python-fail email leaves the row pending_approval."""
    _row, error = validate_before_claim(db, client_id, execution_id)
    if error:
        return None
    return claim_for_execution(db, client_id, execution_id)


def _run_data_plane_tool(
    db: Any, client_id: str, execution_id: str, port: Any
) -> dict:
    """Post-claim mailbox attempt. Lookup first; unknown stays non-terminal.

    ``port`` is an injected mailbox. Production ``send_email`` attaches
    ``GmailMailboxPort`` only after ``os_tools.refuse_send_email`` returns
    None (flag on + Sales).
    """
    row = get_tool_execution(db, client_id, execution_id)
    if row is None or row.get("status") != "running":
        return {"executed": False, "adopted": False, "unknown": False}
    if port is None:
        return {"executed": False, "adopted": False, "unknown": False}

    msgid = rfc822_msgid_for(execution_id)
    payload = row.get("input") or {}
    try:
        existing = port.find_by_rfc822_msgid(msgid)
    except Exception:
        apply_unknown_send_outcome(
            db,
            client_id,
            execution_id,
            "Gmail Message-ID lookup failed; send was not attempted",
        )
        return {
            "executed": False,
            "adopted": False,
            "unknown": True,
            "reason": "deduplication lookup unavailable",
        }
    if existing:
        verification = _verify_sent_message(
            port,
            existing,
            to=payload.get("to") or "",
            subject=payload.get("subject") or "",
            rfc822_msgid=msgid,
        )
        _record_send_verification(
            db,
            client_id,
            execution_id,
            existing,
            payload,
            msgid,
            deduplicated=True,
            verification=verification,
        )
        return {
            "executed": False,
            "adopted": True,
            "unknown": False,
            "message_id": existing,
            "verified": verification["verified"],
        }

    try:
        sent = port.send(
            to=payload.get("to"),
            subject=payload.get("subject"),
            body=payload.get("body"),
            rfc822_msgid=msgid,
        )
    except TimeoutError:
        apply_unknown_send_outcome(
            db, client_id, execution_id, "gmail transport timed out; outcome unknown"
        )
        return {"executed": True, "adopted": False, "unknown": True}

    if sent is None:
        apply_unknown_send_outcome(
            db,
            client_id,
            execution_id,
            "gmail accepted the message but the response was lost; outcome unknown",
        )
        return {"executed": True, "adopted": False, "unknown": True}

    verification = _verify_sent_message(
        port,
        sent["message_id"],
        to=payload.get("to") or "",
        subject=payload.get("subject") or "",
        rfc822_msgid=msgid,
    )
    _record_send_verification(
        db,
        client_id,
        execution_id,
        sent["message_id"],
        payload,
        msgid,
        deduplicated=False,
        verification=verification,
    )
    return {
        "executed": True,
        "adopted": False,
        "unknown": False,
        "message_id": sent["message_id"],
        "verified": verification["verified"],
    }


def _verify_sent_message(
    port: Any,
    message_id: str,
    *,
    to: str,
    subject: str,
    rfc822_msgid: str,
) -> dict:
    """Read a sent/adopted message back; missing verification fails closed."""
    verify = getattr(port, "verify", None)
    if not callable(verify):
        return {
            "verified": False,
            "detail": "mailbox port does not support read-back verification",
        }
    try:
        result = verify(
            message_id,
            to=to,
            subject=subject,
            rfc822_msgid=rfc822_msgid,
        )
    except Exception:
        logger.exception(
            "os_tool_executions: Gmail read-back failed message_id=%s", message_id
        )
        return {"verified": False, "detail": "Gmail read-back failed"}
    if not isinstance(result, dict):
        return {"verified": False, "detail": "mailbox returned no verification result"}
    return {
        "verified": result.get("verified") is True,
        "detail": str(result.get("detail") or "mailbox verification returned no detail")[
            :500
        ],
    }


def _record_send_verification(
    db: Any,
    client_id: str,
    execution_id: str,
    message_id: str,
    payload: dict,
    rfc822_msgid: str,
    *,
    deduplicated: bool,
    verification: dict,
) -> None:
    verified = verification["verified"] is True
    detail = verification["detail"]
    record_execution_outcome(
        db,
        client_id,
        {
            "id": execution_id,
            "status": "succeeded" if verified else "verification_failed",
            "result": {
                "messageId": message_id,
                "deduplicated": deduplicated,
                "rfc822MsgId": rfc822_msgid,
                "to": payload.get("to"),
                "subject": payload.get("subject"),
            },
            "verificationState": "passed" if verified else "failed",
            "verificationDetail": detail,
            "verifiedAt": _now(),
            "finishedAt": _now(),
            "error": (
                None
                if verified
                else {"code": "verification_failed", "message": detail}
            ),
        },
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
