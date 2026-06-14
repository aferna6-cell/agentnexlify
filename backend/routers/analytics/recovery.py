"""Recovery and ROI stats analytics endpoint."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.dependencies import _get_current_tenant
from backend.routers.analytics._common import (
    _QUERY_LIMIT,
    logger,
)

router = APIRouter()


# ── Recovery & ROI Stats ──────────────────────────────────────


@router.get("/{tenant_id}/recovery-stats")
async def get_recovery_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get no-show recovery and review request stats for dashboard ROI widget."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # No-show recoveries sent
    noshow_recovered = 0
    noshow_total = 0
    try:
        ns = (
            tenant_table(db, "appointments", tenant_id)
            .select("id, noshow_recovery_sent_at, status")
            .eq("status", "no_show")
            .gte("updated_at", since)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        noshow_total = len(ns.data or [])
        noshow_recovered = sum(
            1 for a in (ns.data or []) if a.get("noshow_recovery_sent_at")
        )
    except Exception:
        logger.warning(
            "recovery-stats: noshow query failed for %s", tenant_id, exc_info=True
        )

    # Review requests sent
    reviews_requested = 0
    try:
        rv = (
            tenant_table(db, "appointments", tenant_id)
            .select("id", count="exact")
            .filter("review_request_sent_at", "not.is", "null")
            .gte("review_request_sent_at", since)
            .execute()
        )
        reviews_requested = rv.count or 0
    except Exception:
        logger.warning(
            "recovery-stats: review query failed for %s", tenant_id, exc_info=True
        )

    # Daily briefings sent
    briefings_sent = 0
    try:
        br = (
            tenant_table(db, "activity_log", tenant_id)
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("action", "daily_briefing_sent")
            .gte("created_at", since)
            .execute()
        )
        briefings_sent = br.count or 0
    except Exception:
        logger.debug("recovery-stats: briefing count failed", exc_info=True)

    return {
        "period_days": days,
        "noshow_total": noshow_total,
        "noshow_recovered": noshow_recovered,
        "reviews_requested": reviews_requested,
        "briefings_sent": briefings_sent,
    }
