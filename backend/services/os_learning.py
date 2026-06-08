"""Agent OS learning loop — action -> outcome -> memory (the "Learn" verb).

North-star gap #2. After a lead-targeting action succeeds (``email.send`` /
``sms.send`` / ``calendar.event.create``), capture a *pending* outcome row
keyed to the lead it targeted, then settle it deterministically after a
3-day window and write the verdict back into semantic memory so the
orchestrator's ``search_memory`` recalls it on the next turn.

Deterministic-first. The only model call in this loop is the single
``embed_text`` on the memory summary; everything else is plain joins:

* Recipient -> lead: ``email``/``attendee_email`` match ``leads.email``,
  ``sms`` ``to`` matches ``leads.phone``. No lead match -> skip
  (lead-targeting only; broadcasts never produce an outcome row).
* Outcome ladder (booked > converted > no_response), judged at settle time:
    - booked    — an appointment for this lead created after ``sent_at``
                  (``appointments.lead_id`` FK, high precision)
    - converted — ``leads.status`` is now ``closed`` and was not ``closed``
                  at send (status-transition detection; live vocab has no
                  ``won`` — terminal conversion is ``closed``)
    - no_response — neither, once the 3-day window elapses

One ``os_memory_entries`` row (kind=``outcome``) is written per resolved
outcome, deduped by ``source_ref='outcome:<action_run_id>'``. This is the
on-ramp to the Karpathy graph layer (gap #8): outcomes accrete as recallable
facts today, edges come later.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.embeddings import embed_text
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Days a pending outcome waits before it is judged. Long enough for a lead to
# book or convert, short enough to feed the orchestrator while still relevant.
RESOLVE_WINDOW_DAYS = 3

# request_payload key that carries the lead-facing recipient, per action type.
_RECIPIENT_KEY = {
    "email.send": "to",
    "sms.send": "to",
    "calendar.event.create": "attendee_email",
}

# Which leads column the recipient is matched against, per action type.
_LEAD_MATCH_COLUMN = {
    "email.send": "email",
    "sms.send": "phone",
    "calendar.event.create": "email",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_recipient(action_type: str, request_payload: dict) -> str | None:
    """Pull the lead-facing recipient out of a succeeded action's payload.

    Returns None for non-lead-targeting actions and for payloads whose
    recipient slot is empty (e.g. a calendar event with no attendee).
    """
    key = _RECIPIENT_KEY.get(action_type)
    if key is None:
        return None
    return (request_payload or {}).get(key) or None


def _settle_by(sent_at_iso: str) -> str:
    """ISO timestamp ``RESOLVE_WINDOW_DAYS`` after ``sent_at``."""
    sent = datetime.fromisoformat(sent_at_iso)
    return (sent + timedelta(days=RESOLVE_WINDOW_DAYS)).isoformat()


def _summarize_outcome(
    action_type: str,
    recipient: str | None,
    lead_name: str,
    lead_status_at_send: str | None,
    outcome: str,
) -> str:
    """Short, embeddable record of what an action led to."""
    return (
        f"Action {action_type} to {lead_name} ({recipient or 'unknown'}) "
        f"settled as {outcome}. Lead status at send was "
        f"{lead_status_at_send or 'unknown'}."
    )


def _fetch_lead(db, client_id: str, lead_id: str | None) -> dict | None:
    if not lead_id:
        return None
    result = (
        tenant_table(db, "leads", client_id)
        .select("id, name, status")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


async def record_action_outcome_pending(
    db,
    client_id: str,
    action_run_id: str,
    action_type: str,
    request_payload: dict,
    sent_at: str | None = None,
) -> dict | None:
    """Capture a pending outcome row for a just-succeeded lead-targeting action.

    Resolves the recipient to a lead by deterministic join. Returns None
    (writing nothing) when the action is not lead-targeting, the recipient
    slot is empty, or no lead matches — keeping capture scoped to leads only.
    """
    recipient = _resolve_recipient(action_type, request_payload)
    if recipient is None:
        return None

    sent_at = sent_at or _now()
    match_column = _LEAD_MATCH_COLUMN.get(action_type, "email")

    lead_row = (
        tenant_table(db, "leads", client_id)
        .select("id, name, status")
        .eq(match_column, recipient)
        .limit(1)
        .execute()
    )
    if not lead_row.data:
        return None
    lead = lead_row.data[0]

    payload = {
        "action_run_id": action_run_id,
        "action_type": action_type,
        "lead_id": lead["id"],
        "recipient": recipient,
        "lead_status_at_send": lead.get("status"),
        "sent_at": sent_at,
        "settle_by": _settle_by(sent_at),
        "status": "pending",
    }
    created = (
        tenant_table(db, "os_action_outcomes", client_id).insert(payload).execute()
    )
    return created.data[0] if created.data else payload


async def _compute_outcome(db, client_id: str, row: dict) -> str:
    """Deterministic outcome ladder: booked > converted > no_response."""
    lead_id = row.get("lead_id")
    sent_at = row.get("sent_at")

    appts = (
        tenant_table(db, "appointments", client_id)
        .select("id, created_at")
        .eq("lead_id", lead_id)
        .gt("created_at", sent_at)
        .limit(1)
        .execute()
    )
    if appts.data:
        return "booked"

    lead = _fetch_lead(db, client_id, lead_id)
    current_status = (lead or {}).get("status")
    if current_status == "closed" and row.get("lead_status_at_send") != "closed":
        return "converted"

    return "no_response"


async def _write_outcome_memory(db, client_id: str, row: dict, content: str) -> None:
    """Upsert one kind='outcome' memory entry, deduped by action_run_id."""
    source_ref = f"outcome:{row['action_run_id']}"
    try:
        embedding = await embed_text(content)
    except Exception:
        logger.warning(
            "os_learning: embed failed client_id=%s action_run_id=%s",
            client_id,
            row.get("action_run_id"),
            exc_info=True,
        )
        embedding = None

    existing = (
        tenant_table(db, "os_memory_entries", client_id)
        .select("id")
        .eq("source_ref", source_ref)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant_table(db, "os_memory_entries", client_id).update(
            {"content": content, "embedding": embedding, "updated_at": _now()}
        ).eq("id", existing.data[0]["id"]).execute()
        return

    tenant_table(db, "os_memory_entries", client_id).insert(
        {
            "kind": "outcome",
            "content": content,
            "embedding": embedding,
            "source": "learn:outcome",
            "source_ref": source_ref,
        }
    ).execute()


async def resolve_due_outcomes(client_id: str, db=None) -> list[dict]:
    """Settle every pending outcome past its window for one client.

    For each due row: compute the deterministic outcome, write one memory
    entry, mark the row resolved. Returns the resolved rows (each with an
    ``outcome`` key) for logging.
    """
    if db is None:
        db = get_service_supabase()

    now = _now()
    due = (
        tenant_table(db, "os_action_outcomes", client_id)
        .select("*")
        .eq("status", "pending")
        .lte("settle_by", now)
        .execute()
    )
    rows = due.data or []
    if not rows:
        return []

    resolved: list[dict] = []
    for row in rows:
        try:
            outcome = await _compute_outcome(db, client_id, row)
            lead = _fetch_lead(db, client_id, row.get("lead_id"))
            lead_name = (lead or {}).get("name") or "lead"
            content = _summarize_outcome(
                row.get("action_type"),
                row.get("recipient"),
                lead_name,
                row.get("lead_status_at_send"),
                outcome,
            )
            await _write_outcome_memory(db, client_id, row, content)
            tenant_table(db, "os_action_outcomes", client_id).update(
                {"status": "resolved", "outcome": outcome, "resolved_at": now}
            ).eq("id", row["id"]).execute()
            resolved.append({**row, "outcome": outcome})
        except Exception:
            logger.exception(
                "os_learning: resolve failed client_id=%s outcome_id=%s",
                client_id,
                row.get("id"),
            )
            continue
    return resolved


async def resolve_all_due_outcomes(db=None) -> list[dict]:
    """Scheduler hook: settle due outcomes across every tenant.

    Mirrors ``os_sync.run_due_syncs`` — one cross-tenant sweep for the
    distinct clients that have a due pending row, then per-client resolve.
    """
    if db is None:
        db = get_service_supabase()

    now = _now()
    pending = (
        db.table("os_action_outcomes")
        .select("client_id")
        .eq("status", "pending")
        .lte("settle_by", now)
        .execute()
    )
    client_ids = {r["client_id"] for r in (pending.data or []) if r.get("client_id")}

    outcomes: list[dict] = []
    for cid in client_ids:
        outcomes.extend(await resolve_due_outcomes(cid, db))
    return outcomes


__all__ = [
    "RESOLVE_WINDOW_DAYS",
    "record_action_outcome_pending",
    "resolve_all_due_outcomes",
    "resolve_due_outcomes",
]
