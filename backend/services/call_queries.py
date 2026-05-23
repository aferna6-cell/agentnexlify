"""Dashboard query helpers for the calls router.

Pulled out of `list_calls`, `get_call_stats`, and `get_call` so the router
stays focused on auth + HTTP error mapping. Functions here own the
Supabase query construction against the `calls` table.

All helpers accept `db: Any` as argument so the router's
`get_service_supabase()` patch (used by tests) still applies.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def fetch_calls_page(
    db: Any,
    *,
    tenant_id: str,
    status: str | None,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return `(calls, total)` for a paginated list query.

    Raises on DB error so the router can map to HTTP 500.
    """
    query = (
        db.table("calls")
        .select("*", count="exact")
        .eq("tenant_id", tenant_id)
    )

    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True)

    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    result = query.execute()
    total = result.count if result.count is not None else len(result.data or [])
    return result.data or [], total


def count_calls_for_tenant(db: Any, tenant_id: str) -> int:
    """Total call count for a tenant. Returns 0 on failure (logs warning)."""
    try:
        result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.count if result.count is not None else 0
    except Exception:
        logger.warning("Failed to count total calls for tenant %s", tenant_id, exc_info=True)
        return 0


def count_missed_calls(db: Any, tenant_id: str) -> int:
    """Sum of calls with status in (no-answer, busy, failed). Returns 0 on failure."""
    total = 0
    try:
        for missed_status in ("no-answer", "busy", "failed"):
            result = (
                db.table("calls")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("status", missed_status)
                .execute()
            )
            total += result.count if result.count is not None else 0
    except Exception:
        logger.warning("Failed to count missed calls for tenant %s", tenant_id, exc_info=True)
    return total


def compute_avg_call_duration(db: Any, tenant_id: str) -> float:
    """Average duration of completed calls with `duration_seconds > 0`. Returns 0.0 on failure."""
    try:
        result = (
            db.table("calls")
            .select("duration_seconds")
            .eq("tenant_id", tenant_id)
            .eq("status", "completed")
            .execute()
        )
        durations = [
            r["duration_seconds"]
            for r in (result.data or [])
            if r.get("duration_seconds") and r["duration_seconds"] > 0
        ]
        if durations:
            return round(sum(durations) / len(durations), 1)
    except Exception:
        logger.warning("Failed to compute avg duration for tenant %s", tenant_id, exc_info=True)
    return 0.0


def count_calls_today(db: Any, tenant_id: str) -> int:
    """Calls created since UTC midnight today. Returns 0 on failure."""
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", today_start)
            .execute()
        )
        return result.count if result.count is not None else 0
    except Exception:
        logger.warning("Failed to count today's calls for tenant %s", tenant_id, exc_info=True)
        return 0


def fetch_call_by_id(db: Any, *, tenant_id: str, call_id: str) -> dict[str, Any] | None:
    """Single-call lookup scoped by tenant. Returns None if not found.

    Raises on DB error so the router can map to HTTP 500.
    """
    result = (
        db.table("calls")
        .select("*")
        .eq("id", call_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]
