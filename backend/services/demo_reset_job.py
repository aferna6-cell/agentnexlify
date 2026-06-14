"""Nightly demo-tenant reset job.

Runs from the automation loop (30-minute tier). Resets all demo tenants
between 03:00–05:59 UTC, once per day, deduped via activity_log.

Dedup pattern mirrors send_weekly_intelligence_briefs in
backend/services/automation/scheduled_jobs_ext.py.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.demo_seed import ensure_demo_tenants, reset_demo_tenant

logger = logging.getLogger(__name__)

# UTC window for nightly resets: 03:00 – 05:59
_RESET_HOUR_START = 3
_RESET_HOUR_END = 5  # inclusive


async def reset_demo_tenants() -> int:
    """Reset all is_demo tenants so the public sandbox looks fresh.

    Only executes between 03:00–05:59 UTC. Each vertical is deduped
    independently via activity_log (activity_type = 'demo_reset_<vertical>_YYYY-MM-DD').
    Calls ensure_demo_tenants first so all demo tenants are created if they
    don't exist yet.

    Returns count of tenants reset.
    """
    now = datetime.now(timezone.utc)

    # Time-window gate: only run between 03:00–05:59 UTC
    if not (_RESET_HOUR_START <= now.hour <= _RESET_HOUR_END):
        return 0

    db = get_service_supabase()

    today = now.date().isoformat()
    reset_count = 0

    # Ensure all demo tenants exist (idempotent)
    try:
        vertical_map = ensure_demo_tenants(db)
        if not vertical_map:
            logger.warning("reset_demo_tenants: ensure_demo_tenants returned empty map — skip")
            return 0
    except Exception:
        logger.exception("reset_demo_tenants: ensure_demo_tenants raised unexpectedly")
        return 0

    # Reset each vertical independently with per-vertical dedup
    for vertical, tenant_id in vertical_map.items():
        today_tag = f"demo_reset_{vertical}_{today}"

        # Dedup: check if already reset today for this vertical
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
                continue
        except Exception:
            logger.warning(
                "reset_demo_tenants: dedup check failed for vertical=%s tenant=%s",
                vertical, tenant_id,
                exc_info=True,
            )
            # Conservative: skip rather than double-reset on dedup failure
            continue

        # Perform the reset
        try:
            summary = reset_demo_tenant(db, tenant_id)
            if "error" in summary:
                logger.error(
                    "reset_demo_tenants: reset_demo_tenant returned error=%s "
                    "for vertical=%s tenant=%s",
                    summary["error"], vertical, tenant_id,
                )
                continue
            reset_count += 1
            logger.info(
                "reset_demo_tenants: reset complete for vertical=%s tenant=%s summary=%s",
                vertical, tenant_id, summary,
            )
        except Exception:
            logger.exception(
                "reset_demo_tenants: reset_demo_tenant raised for vertical=%s tenant_id=%s",
                vertical, tenant_id,
            )
            continue

        # Write dedup marker to activity_log
        try:
            db.table("activity_log").insert({
                "tenant_id": tenant_id,
                "activity_type": today_tag,
                "description": f"Demo tenant nightly reset completed ({vertical})",
            }).execute()
        except Exception:
            logger.warning(
                "reset_demo_tenants: failed to write dedup marker for vertical=%s tenant=%s",
                vertical, tenant_id,
                exc_info=True,
            )

    return reset_count
