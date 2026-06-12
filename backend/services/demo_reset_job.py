"""Nightly demo-tenant reset job.

Runs from the automation loop (30-minute tier). Resets all demo tenants
between 03:00–05:59 UTC, once per day, deduped via activity_log.

Dedup pattern mirrors send_weekly_intelligence_briefs in
backend/services/automation/scheduled_jobs_ext.py.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.demo_seed import ensure_demo_tenant, reset_demo_tenant

logger = logging.getLogger(__name__)

# UTC window for nightly resets: 03:00 – 05:59
_RESET_HOUR_START = 3
_RESET_HOUR_END = 5  # inclusive


async def reset_demo_tenants() -> int:
    """Reset all is_demo tenants so the public sandbox looks fresh.

    Only executes between 03:00–05:59 UTC. Deduped to once per day via
    activity_log (activity_type = 'demo_reset_YYYY-MM-DD'). Calls
    ensure_demo_tenant first so the demo tenant is created if it doesn't
    exist yet.

    Returns count of tenants reset.
    """
    now = datetime.now(timezone.utc)

    # Time-window gate: only run between 03:00–05:59 UTC
    if not (_RESET_HOUR_START <= now.hour <= _RESET_HOUR_END):
        return 0

    db = get_service_supabase()

    today_tag = f"demo_reset_{now.date().isoformat()}"
    reset_count = 0

    # Ensure demo tenant exists (idempotent)
    try:
        tenant_id = ensure_demo_tenant(db)
        if not tenant_id:
            logger.warning("reset_demo_tenants: ensure_demo_tenant returned None — skip")
            return 0
    except Exception:
        logger.exception("reset_demo_tenants: ensure_demo_tenant raised unexpectedly")
        return 0

    # Dedup: check if already reset today for this tenant
    # Mirror exactly the pattern used by send_weekly_intelligence_briefs:
    # query activity_log by tenant_id + activity_type; skip if count > 0.
    try:
        existing = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", today_tag)
            .limit(1)
            .execute()
        )
        if existing.count and existing.count > 0:
            logger.info(
                "reset_demo_tenants: already reset today (tag=%s tenant=%s) — skip",
                today_tag, tenant_id,
            )
            return 0
    except Exception:
        logger.warning(
            "reset_demo_tenants: dedup check failed for tenant %s", tenant_id,
            exc_info=True,
        )
        # Conservative: skip rather than double-reset on dedup failure
        return 0

    # Perform the reset
    try:
        summary = reset_demo_tenant(db, tenant_id)
        if "error" in summary:
            logger.error(
                "reset_demo_tenants: reset_demo_tenant returned error=%s for tenant %s",
                summary["error"], tenant_id,
            )
            return 0
        reset_count += 1
        logger.info(
            "reset_demo_tenants: reset complete for tenant=%s summary=%s",
            tenant_id, summary,
        )
    except Exception:
        logger.exception(
            "reset_demo_tenants: reset_demo_tenant raised for tenant_id=%s", tenant_id
        )
        return 0

    # Write dedup marker to activity_log
    try:
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "activity_type": today_tag,
            "description": "Demo tenant nightly reset completed",
        }).execute()
    except Exception:
        logger.warning(
            "reset_demo_tenants: failed to write dedup marker for tenant %s",
            tenant_id, exc_info=True,
        )

    return reset_count
