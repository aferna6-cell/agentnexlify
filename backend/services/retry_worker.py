"""Durable retry worker (Phase 4) — drains `pending_automations`.

Background task that re-runs failed automations (e.g. missed-call text-back)
with exponential backoff: 30s, 2min, 10min — max 3 attempts. Each attempt
emits a Sentry breadcrumb. Rows that exhaust their attempts (status='failed')
or sit pending past 1h are surfaced via GET /automations/{tenant_id}/pending.

Why a durable queue (vs in-process `services/retry.py::with_retry`):
- backoffs span minutes — too long to hold a request/worker open
- production runs 4 Uvicorn workers; in-memory retries die with the process
- the queue is a single DB-backed source of truth across workers

Schema: migrations/133_pending_automations.sql (uses `tenant_id`, matching the
sibling `missed_call_texts` table — NOT `client_id`).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from backend.models.database import get_service_supabase
from backend.services import twilio_service

logger = logging.getLogger(__name__)

# Exponential backoff between attempts. Index = retry_count being scheduled.
#   enqueue       -> scheduled_for = now + BACKOFF_SECONDS[0]  (30s)
#   1st failure   -> retry_count=1 -> now + BACKOFF_SECONDS[1] (2min)
#   2nd failure   -> retry_count=2 -> now + BACKOFF_SECONDS[2] (10min)
#   3rd failure   -> retry_count=3 == MAX_ATTEMPTS -> status='failed' (stuck)
BACKOFF_SECONDS = [30, 120, 600]
MAX_ATTEMPTS = 3

_TABLE = "pending_automations"
_BATCH_LIMIT = 50
_STUCK_AFTER = timedelta(hours=1)

# Handler contract: async fn(payload: dict) -> bool. True = success.
HandlerFn = Callable[[dict], Awaitable[bool]]
_HANDLERS: dict[str, HandlerFn] = {}


def register_handler(automation_type: str, handler: HandlerFn) -> None:
    """Register an async handler for an automation_type."""
    _HANDLERS[automation_type] = handler


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sentry_breadcrumb(automation_type: str, row_id: str, attempt: int) -> None:
    """Record a retry attempt as a Sentry breadcrumb. No-op if Sentry absent."""
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="retry_worker",
            message=f"draining {automation_type} (attempt {attempt})",
            level="info",
            data={"row_id": row_id, "automation_type": automation_type},
        )
    except Exception:
        # Sentry is optional infrastructure — never let it break the drain.
        logger.debug("sentry breadcrumb skipped", exc_info=True)


def enqueue_pending_automation(
    tenant_id: str,
    automation_type: str,
    payload: dict,
    *,
    delay_seconds: int = BACKOFF_SECONDS[0],
) -> None:
    """Insert a pending automation to be drained after `delay_seconds`."""
    scheduled_for = (_now() + timedelta(seconds=delay_seconds)).isoformat()
    row = {
        "tenant_id": tenant_id,
        "automation_type": automation_type,
        "payload_json": payload,
        "status": "pending",
        "retry_count": 0,
        "scheduled_for": scheduled_for,
    }
    try:
        get_service_supabase().table(_TABLE).insert(row).execute()
        logger.info(
            "Enqueued %s for tenant %s (delay=%ss)",
            automation_type,
            tenant_id,
            delay_seconds,
        )
    except Exception:
        logger.exception(
            "Failed to enqueue %s for tenant %s", automation_type, tenant_id
        )


def _update(db, row_id: str, fields: dict) -> None:
    db.table(_TABLE).update(fields).eq("id", row_id).execute()


async def _process_row(db, row: dict) -> None:
    """Run one pending row's handler and record the outcome."""
    row_id = row["id"]
    automation_type = row.get("automation_type", "")
    retry_count = int(row.get("retry_count", 0) or 0)
    payload = row.get("payload_json") or {}

    _sentry_breadcrumb(automation_type, row_id, retry_count + 1)

    handler = _HANDLERS.get(automation_type)
    if handler is None:
        logger.warning(
            "No handler for automation_type=%s (row %s) — marking failed",
            automation_type,
            row_id,
        )
        _update(db, row_id, {"status": "failed"})
        return

    try:
        ok = await handler(payload)
    except Exception:
        logger.exception("Handler %s raised for row %s", automation_type, row_id)
        ok = False

    if ok:
        _update(db, row_id, {"status": "done"})
        return

    next_retry = retry_count + 1
    if next_retry >= MAX_ATTEMPTS:
        logger.warning(
            "Row %s (%s) exhausted %s attempts — marking failed",
            row_id,
            automation_type,
            MAX_ATTEMPTS,
        )
        _update(db, row_id, {"status": "failed", "retry_count": next_retry})
        return

    backoff = BACKOFF_SECONDS[next_retry]
    scheduled_for = (_now() + timedelta(seconds=backoff)).isoformat()
    _update(
        db,
        row_id,
        {
            "status": "pending",
            "retry_count": next_retry,
            "scheduled_for": scheduled_for,
        },
    )


async def drain_pending_automations() -> int:
    """Drain due pending automations. Returns count of rows processed.

    Called on the 60s automation tick in backend/main.py. `scheduled_for`
    gates each row, so the 60s cadence still honors 30s/2min/10min backoffs.
    """
    db = get_service_supabase()
    now_iso = _now().isoformat()
    try:
        resp = (
            db.table(_TABLE)
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now_iso)
            .order("scheduled_for")
            .limit(_BATCH_LIMIT)
            .execute()
        )
        rows = resp.data or []
    except Exception:
        logger.exception("Failed to fetch pending automations")
        return 0

    processed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            await _process_row(db, row)
            processed += 1
        except Exception:
            logger.exception("Failed to process pending row %s", row.get("id"))
    if processed:
        logger.info("Drained %s pending automation(s)", processed)
    return processed


def filter_stuck_pending(rows: list[dict], now: datetime | None = None) -> list[dict]:
    """Return rows that need operator attention: failed, or pending >1h.

    Used by GET /automations/{tenant_id}/pending to surface automations that
    silently stopped retrying.
    """
    now = now or _now()
    cutoff = now - _STUCK_AFTER
    stuck = []
    for row in rows:
        status = row.get("status")
        if status == "failed":
            stuck.append(row)
            continue
        if status == "pending":
            created = row.get("created_at")
            if created and _parse(created) <= cutoff:
                stuck.append(row)
    return stuck


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------
async def _handle_missed_call_text(payload: dict) -> bool:
    """Re-send a missed-call text-back SMS via Twilio."""
    to_phone = payload.get("to_phone")
    body = payload.get("body")
    if not to_phone or not body:
        logger.warning("missed_call_text payload missing to_phone/body")
        return False
    return await twilio_service.send_sms(
        to=to_phone, body=body, from_number=payload.get("from_number")
    )


register_handler("missed_call_text", _handle_missed_call_text)
