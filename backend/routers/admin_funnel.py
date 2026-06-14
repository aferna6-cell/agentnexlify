"""Admin funnel readout — signup-wizard drop-off analytics aggregated across all tenants.

All endpoints are protected by the API secret key (internal admin only, not tenant-facing).
Table: wizard_events (tenant_id, step, action, created_at)
Step range: 0–7, where 0 = express-setup chooser, 1–7 = wizard steps.
"""

import logging
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/funnel", tags=["platform-admin"])

# Human-readable labels for each wizard step.
_STEP_LABELS: dict[int, str] = {
    0: "express chooser",
    1: "business info",
    2: "business type",
    3: "services",
    4: "knowledge base",
    5: "widget config",
    6: "team setup",
    7: "embed",
}

_MAX_DAYS = 90
_DEFAULT_DAYS = 30


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    """Verify caller has the platform admin secret. Raises 401 on failure."""
    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


@router.get("/wizard")
@limiter.limit("10/minute")
async def get_wizard_funnel(
    request: Request,
    x_api_secret: str | None = Header(None),
    days: int = Query(_DEFAULT_DAYS, ge=1),
):
    """Aggregate wizard_events into per-step distinct-tenant counts + drop-off rates.

    Returns:
        window_days: the query window actually used (capped at 90).
        steps: [{step, label, tenants}] — DISTINCT tenant count per step that
               entered that step in the window.
        dropoff: [{from_step, to_step, lost, rate}] for consecutive step pairs.
        totals: {started, completed, completion_rate}.
    """
    _verify_admin_secret(x_api_secret)

    # Cap the window at _MAX_DAYS regardless of what the caller sends.
    window_days = min(days, _MAX_DAYS)
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()

    try:
        db = get_service_supabase()

        # Fetch all enter-action events in the window.  We count DISTINCT tenants
        # per step, so we only need the tenant_id + step columns.
        result = (
            db.table("wizard_events")
            .select("tenant_id, step")
            .eq("action", "enter")
            .gte("created_at", since)
            .execute()
        )
        rows = result.data or []

    except Exception:
        logger.exception("Failed to query wizard_events for funnel")
        raise HTTPException(status_code=500, detail="Failed to load wizard funnel data")

    # Build per-step sets of distinct tenant_ids.
    step_tenants: dict[int, set[str]] = {s: set() for s in range(8)}
    for row in rows:
        step = row.get("step")
        tenant_id = row.get("tenant_id")
        if step is not None and tenant_id and 0 <= step <= 7:
            step_tenants[step].add(tenant_id)

    # Only include steps that have at least one recorded tenant.
    steps = [
        {
            "step": s,
            "label": _STEP_LABELS.get(s, f"step {s}"),
            "tenants": len(step_tenants[s]),
        }
        for s in range(8)
        if len(step_tenants[s]) > 0
    ]

    # Drop-off between consecutive populated steps.
    dropoff = []
    populated = [s["step"] for s in steps]
    for i in range(len(populated) - 1):
        from_step = populated[i]
        to_step = populated[i + 1]
        from_count = len(step_tenants[from_step])
        to_count = len(step_tenants[to_step])
        lost = from_count - to_count
        rate = round(lost / from_count, 4) if from_count > 0 else 0.0
        dropoff.append(
            {
                "from_step": from_step,
                "to_step": to_step,
                "lost": lost,
                "rate": rate,
            }
        )

    # Totals: "started" = step 0 (express chooser), "completed" = step 7 (embed).
    started = len(step_tenants[0])
    completed = len(step_tenants[7])
    completion_rate = round(completed / started, 4) if started > 0 else 0.0

    # Live-demo conversion: sessions (activity_log demo_login rows) vs
    # signups attributed via the wizard demo_referral event. Failures
    # degrade to zeros — the funnel itself must still load.
    demo_sessions = 0
    demo_signups = 0
    try:
        sessions = (
            db.table("activity_log")
            .select("id")
            .eq("activity_type", "demo_login")
            .gte("created_at", since)
            .execute()
        )
        demo_sessions = len(sessions.data or [])
        referrals = (
            db.table("wizard_events")
            .select("tenant_id")
            .eq("action", "demo_referral")
            .gte("created_at", since)
            .execute()
        )
        demo_signups = len({r.get("tenant_id") for r in (referrals.data or []) if r.get("tenant_id")})
    except Exception:
        logger.warning("Failed to load demo conversion stats", exc_info=True)

    return {
        "window_days": window_days,
        "steps": steps,
        "dropoff": dropoff,
        "totals": {
            "started": started,
            "completed": completed,
            "completion_rate": completion_rate,
        },
        "demo": {
            "sessions": demo_sessions,
            "signups": demo_signups,
            "conversion_rate": round(demo_signups / demo_sessions, 4) if demo_sessions else 0.0,
        },
    }
