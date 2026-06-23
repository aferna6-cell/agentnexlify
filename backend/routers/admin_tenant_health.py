"""Admin per-tenant health endpoint — activation / dormancy report.

GET /api/v1/admin/tenant-health

Protected by the platform admin secret (x-api-secret header, HMAC constant-time
compare) — same pattern as admin_analytics.py and funnel.py.

Do NOT add `from __future__ import annotations` — breaks Pydantic on route handlers.
"""

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from backend.config import is_production, settings
from backend.limiter import limiter
from backend.services.tenant_health import compute_tenant_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])


# ---------------------------------------------------------------------------
# Admin auth — mirrors funnel.py / admin_analytics.py pattern exactly
# ---------------------------------------------------------------------------


def _admin_secret() -> str:
    """Resolve the admin secret key.

    Production: requires admin_api_secret_key to be set distinctly.
    Local/dev: falls back to api_secret_key for convenience.
    Returns "" on failure — _verify_admin_secret then rejects all requests (401).
    """
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    if is_production():
        return ""
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    """Reject with 401 if caller lacks the platform admin secret."""
    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/tenant-health")
@limiter.limit("10/minute")
async def get_tenant_health(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Return per-tenant activation and health breakdown.

    Response shape:
        tenants     list  — one object per tenant with keys:
            tenant_id           str
            business_name       str
            plan                str
            plan_status         str
            is_paid             bool  — plan != 'free' AND plan_status in (active, trialing)
            total_messages      int
            total_leads         int
            total_appointments  int
            messages_last_7d    int
            leads_last_7d       int
            last_activity_at    str | None  — ISO UTC timestamp of most recent activity
            status              str  — 'active' | 'at_risk' | 'dormant'
        computed_at str  — UTC ISO timestamp of report generation

    Status derivation:
        active  — any activity in the last 7 days
        at_risk — activity in days 8–30
        dormant — no activity in the last 30 days
    """
    _verify_admin_secret(x_api_secret)

    try:
        data = compute_tenant_health()
    except Exception:
        logger.exception("get_tenant_health: unexpected error in compute_tenant_health")
        raise HTTPException(status_code=500, detail="Failed to compute tenant health")

    return data
