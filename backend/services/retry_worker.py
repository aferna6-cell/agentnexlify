"""pending_automations retry drainer (#118).

Background drainer for the ``pending_automations`` queue. The enqueue side ships
in ``missed_call_gate.py`` (#117) and ``booking_gcal.py`` (#119): when a live
outbound (Twilio text-back, Google Calendar sync, confirmation SMS) fails, those
modules insert a ``pending`` row with a short first-retry delay. This module
drains due rows on the 60s automation tick, re-dispatches them, and applies the
exponential backoff (30s enqueue / 2min / 10min, max 3 attempts) from the
ops-automation spec §8.

Column contract matches the shipped enqueuers (authority over the #118 issue
text, which predates them): the queue is ``tenant_id``-scoped and the retry
counter column is ``attempts`` (NOT ``client_id`` / ``retry_count``). The table
is created by migration 186 and is not auto-applied, so every DB touch here is
fail-open: a missing table logs and no-ops rather than raising into the loop.

Dispatch is registry-based (``register_dispatcher``) so the concrete re-fire
handlers stay in their own modules and this drainer stays unit-testable with an
injected dispatcher map. Pure/injectable ``db`` + ``now`` for the same reason.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Wait before attempt N (1-indexed): attempt 1 = 30s (set by the enqueuer),
# attempt 2 = 2min, attempt 3 = 10min. Matches _RETRY_BACKOFF_SECONDS in the
# enqueuers so the whole retry cadence is one schedule.
RETRY_BACKOFF_SECONDS = (30, 120, 600)
MAX_ATTEMPTS = 3

# automation_type -> callable(tenant_id, payload) -> bool (True == delivered).
# Handler modules register their re-fire entry point here at import time.
_DISPATCHERS: dict = {}


def register_dispatcher(automation_type: str, fn) -> None:
    """Register the re-fire handler for one ``automation_type``."""
    _DISPATCHERS[automation_type] = fn


def _get_db(db):
    if db is not None:
        return db
    from backend.models.database import get_service_supabase

    return get_service_supabase()


def _breadcrumb(message: str, data: dict) -> None:
    """Emit a Sentry breadcrumb, tolerating Sentry being absent/unconfigured."""
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="automation.retry", message=message, data=data, level="info"
        )
    except Exception:
        logger.debug("retry_worker: sentry breadcrumb skipped", exc_info=True)


def _update(db, row_id, fields: dict) -> None:
    try:
        db.table("pending_automations").update(fields).eq("id", row_id).execute()
    except Exception:
        logger.warning("retry_worker: update failed for pending_automation %s", row_id)


def _process_one(row: dict, now: datetime, db, registry: dict) -> None:
    atype = row.get("automation_type")
    tenant_id = row.get("tenant_id")
    attempts = int(row.get("attempts") or 0)
    _breadcrumb(
        f"drain {atype}", {"id": row.get("id"), "attempt": attempts + 1, "tenant_id": tenant_id}
    )

    dispatcher = registry.get(atype)
    ok = False
    if dispatcher is None:
        logger.warning("retry_worker: no dispatcher for automation_type %r", atype)
    else:
        try:
            ok = bool(dispatcher(tenant_id, row.get("payload") or {}))
        except Exception:
            logger.warning("retry_worker: dispatcher for %r raised", atype, exc_info=True)
            ok = False

    if ok:
        _update(db, row.get("id"), {"status": "done"})
        return

    new_attempts = attempts + 1
    if new_attempts >= MAX_ATTEMPTS:
        _update(db, row.get("id"), {"status": "failed", "attempts": new_attempts})
        _breadcrumb(
            f"{atype} failed after {new_attempts} attempts",
            {"id": row.get("id"), "tenant_id": tenant_id},
        )
        return

    wait = RETRY_BACKOFF_SECONDS[min(new_attempts, len(RETRY_BACKOFF_SECONDS) - 1)]
    next_at = (now + timedelta(seconds=wait)).isoformat()
    _update(db, row.get("id"), {"attempts": new_attempts, "scheduled_for": next_at})


def drain_pending_automations(
    tenant_id: str = None,
    *,
    db=None,
    now: datetime = None,
    dispatchers: dict = None,
) -> int:
    """Drain due ``pending_automations`` rows. Returns the number processed.

    Selects ``status='pending'`` rows whose ``scheduled_for`` is due, dispatches
    each by ``automation_type``, and either marks it ``done`` or reschedules with
    backoff (``failed`` after ``MAX_ATTEMPTS``). Fail-open: a select error (e.g.
    the table not yet migrated) logs and returns 0. Optional ``tenant_id`` scopes
    the drain to one tenant; ``dispatchers`` overrides the module registry (tests).
    """
    now = now or datetime.now(timezone.utc)
    db = _get_db(db)
    registry = dispatchers if dispatchers is not None else _DISPATCHERS

    try:
        query = (
            db.table("pending_automations")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now.isoformat())
        )
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        rows = query.execute().data or []
    except Exception:
        logger.warning(
            "retry_worker: drain select failed (pending_automations may be unapplied)"
        )
        return 0

    processed = 0
    for row in rows:
        try:
            _process_one(row, now, db, registry)
        except Exception:
            logger.exception("retry_worker: unexpected error draining row %s", row.get("id"))
        processed += 1
    return processed
