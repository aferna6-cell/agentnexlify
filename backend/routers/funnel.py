"""Platform product funnel endpoint — signup → activation → lead → paid.

GET /api/v1/admin/product-funnel

Protected by the same admin secret used by admin_analytics, admin_health,
and admin_funnel (x-api-secret header, HMAC constant-time compare).

This router does NOT use `from __future__ import annotations` — per project
rules that annotation would break Pydantic model resolution on route handlers.
"""

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from backend.config import is_production, settings
from backend.limiter import limiter
from backend.services.funnel_metrics import compute_funnel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])


# ---------------------------------------------------------------------------
# Admin auth — mirrors admin_analytics.py pattern exactly
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


@router.get("/product-funnel")
@limiter.limit("10/minute")
async def get_product_funnel(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Return platform-wide funnel counts: signups → activated → with_lead → paid.

    Response shape:
        total_tenants         int   — all registered tenants
        activated             int   — tenants with >=1 chat_message (widget used)
        with_leads            int   — tenants that have captured >=1 lead
        paid                  int   — tenants on an active/trialing paid plan
        new_signups_week      int   — signups since Monday 00:00 UTC
        new_leads_week        int   — leads created since Monday 00:00 UTC
        new_appointments_week int   — appointments since Monday 00:00 UTC
        errors                list  — metric names that hit a DB error (degraded)
        computed_at           str   — UTC ISO timestamp of computation
    """
    _verify_admin_secret(x_api_secret)

    try:
        data = compute_funnel()
    except Exception:
        logger.exception("get_product_funnel: unexpected error in compute_funnel")
        raise HTTPException(status_code=500, detail="Failed to compute funnel metrics")

    return data
