"""pending_automations retry worker (issue #118).

Drains the ``pending_automations`` queue with exponential backoff
(30s / 2min / 10min, max 3 attempts), dispatching each row by
``automation_type``. This is the no-silent-loss guarantee (spec G6) behind
missed-call SMS retries and GCal-sync retries.

SCHEMA NOTE (contract §7): ``pending_automations`` is ``tenant_id``-scoped
(migration 180 — the corrected ops-automation schema; the issue's ``client_id``
wording predates that correction). All queue operations use ``tenant_id``.

Fail-open: if the table is absent (migration 180 not yet applied) or any query
errors, ``drain_pending_automations`` returns 0 and never raises — so it is safe
to schedule (every 60s) before the migration lands.

Dispatch handlers are registered per ``automation_type`` via
``register_dispatcher`` so the concrete Twilio/GCal re-fire handlers (issues
#117 / #119) wire in without changing this drainer.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Backoff after the Nth failed attempt: 1st -> 30s, 2nd -> 2min. A row that has
# already failed MAX_ATTEMPTS times is marked 'failed' and not rescheduled.
BACKOFF_SECONDS = (30, 120, 600)
MAX_ATTEMPTS = 3

# automation_type -> async handler(tenant_id, payload) -> bool (True = success).
Dispatcher = Callable[[str, dict], Awaitable[bool]]
_DISPATCHERS: Dict[str, Dispatcher] = {}


def register_dispatcher(automation_type: str, handler: Dispatcher) -> None:
    """Register the re-fire handler for an automation_type (idempotent)."""
    _DISPATCHERS[automation_type] = handler


def _breadcrumb(**data) -> None:
    """Best-effort Sentry breadcrumb; never raises if sentry_sdk is absent."""
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(category="retry_worker", data=data)
    except Exception:
        pass


def next_scheduled_for(new_retry_count: int, now: datetime) -> datetime:
    """When to retry next, given the just-incremented retry_count."""
    idx = min(max(new_retry_count - 1, 0), len(BACKOFF_SECONDS) - 1)
    return now + timedelta(seconds=BACKOFF_SECONDS[idx])


async def drain_pending_automations(
    tenant_id: Optional[str] = None,
    *,
    now: Optional[datetime] = None,
    db=None,
    dispatchers: Optional[Dict[str, Dispatcher]] = None,
) -> int:
    """Drain due ``pending_automations`` rows. Returns the number processed.

    A row is due when ``status='pending'`` and ``scheduled_for <= now``. Each is
    dispatched by ``automation_type``; on success it is marked ``done``, on
    failure its ``retry_count`` is incremented and it is either rescheduled with
    backoff or marked ``failed`` after ``MAX_ATTEMPTS``.
    """
    now = now or datetime.now(timezone.utc)
    dispatchers = dispatchers if dispatchers is not None else _DISPATCHERS
    if db is None:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()

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
            "retry_worker: pending_automations query failed (table may be unapplied) "
            "— draining nothing",
            exc_info=True,
        )
        return 0

    processed = 0
    for row in rows:
        processed += 1
        row_id = row.get("id")
        automation_type = row.get("automation_type")
        row_tenant = row.get("tenant_id")
        _breadcrumb(
            id=row_id, automation_type=automation_type, retry_count=row.get("retry_count")
        )

        handler = dispatchers.get(automation_type)
        succeeded = False
        if handler is None:
            logger.warning(
                "retry_worker: no dispatcher for automation_type=%s (id=%s)",
                automation_type,
                row_id,
            )
        else:
            try:
                succeeded = bool(await handler(row_tenant, row.get("payload_json") or {}))
            except Exception:
                logger.warning(
                    "retry_worker: dispatch raised for id=%s type=%s",
                    row_id,
                    automation_type,
                    exc_info=True,
                )
                succeeded = False

        try:
            if succeeded:
                db.table("pending_automations").update({"status": "done"}).eq(
                    "id", row_id
                ).execute()
            else:
                new_count = (row.get("retry_count") or 0) + 1
                if new_count >= MAX_ATTEMPTS:
                    db.table("pending_automations").update(
                        {"status": "failed", "retry_count": new_count}
                    ).eq("id", row_id).execute()
                    _breadcrumb(id=row_id, event="failed_permanently", retry_count=new_count)
                else:
                    db.table("pending_automations").update(
                        {
                            "status": "pending",
                            "retry_count": new_count,
                            "scheduled_for": next_scheduled_for(new_count, now).isoformat(),
                        }
                    ).eq("id", row_id).execute()
        except Exception:
            logger.warning(
                "retry_worker: status update failed for id=%s", row_id, exc_info=True
            )

    return processed
