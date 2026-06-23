"""Referral click tracking — records watermark clicks from tenant-embedded widgets.

Also exposes an admin endpoint for cross-tenant referral performance ranking:
  GET /api/v1/referral/admin/overview  (x-api-secret gated)

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from backend.config import is_production, settings
from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.referral_overview import compute_referral_overview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/referral", tags=["referral"])

_SHARE_BASE = "https://agentnexlify.com?ref={ref_code}&utm_source=widget"


# ---------------------------------------------------------------------------
# Admin auth — mirrors funnel.py pattern exactly
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
# Pydantic models for admin overview
# ---------------------------------------------------------------------------


class TenantReferralRow(BaseModel):
    tenant_id: str
    business_name: str
    ref_code: str
    total_clicks: int
    referred_signups: int


class ReferralOverviewTotals(BaseModel):
    total_clicks: int
    total_referred_signups: int


class ReferralOverviewResponse(BaseModel):
    tenants: list[TenantReferralRow]
    totals: ReferralOverviewTotals
    computed_at: str


# ---------------------------------------------------------------------------
# Admin route — MUST appear before any /{param} route (FastAPI order matters)
# ---------------------------------------------------------------------------


@router.get("/admin/overview", response_model=ReferralOverviewResponse)
@limiter.limit("10/minute")
async def get_referral_overview(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Return per-tenant referral performance ranked by referred_signups desc.

    Admin-secret gated (x-api-secret header, HMAC constant-time compare).

    Response shape:
        tenants[]:
            tenant_id        str — tenant UUID
            business_name    str — tenant's business name
            ref_code         str — tenant's widget api_key (their referral identity)
            total_clicks     int — clicks on their watermark (referral_clicks table)
            referred_signups int — tenants who signed up via their ref link
        totals:
            total_clicks           int — platform-wide click sum
            total_referred_signups int — platform-wide signup sum
        computed_at str — UTC ISO timestamp
    """
    _verify_admin_secret(x_api_secret)

    try:
        data = compute_referral_overview()
    except Exception:
        logger.exception("get_referral_overview: unexpected error in compute_referral_overview")
        raise HTTPException(
            status_code=500,
            detail="Failed to compute referral overview",
        )

    return data


# ---------------------------------------------------------------------------
# Pydantic models for tenant-facing endpoints (existing)
# ---------------------------------------------------------------------------


class ReferralClickRequest(BaseModel):
    ref: str
    path: str | None = None
    referrer: str | None = None


class ReferralStatsResponse(BaseModel):
    ref_code: str
    share_link: str
    total_clicks: int
    clicks_last_7d: int
    clicks_last_30d: int
    referred_signups: int


# NOTE: static route /my-stats MUST appear before any /{param} route.
# FastAPI matches in registration order — param routes would shadow statics otherwise.
@router.get("/my-stats", response_model=ReferralStatsResponse)
async def get_my_referral_stats(
    claims: dict = Depends(_get_current_tenant),
):
    """Return referral stats for the calling tenant.

    Resolution chain:
    1. Extract tenant_id from JWT claims (set by _get_current_tenant).
    2. Look up widget_configs.api_key for that tenant_id — this is the
       public embed key stored in referral_clicks.ref_tenant_id.
    3. Aggregate click counts from referral_clicks.
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing tenant_id")

    db = get_service_supabase()

    # Step 1: resolve ref_code from widget_configs
    try:
        wc_result = (
            db.table("widget_configs")
            .select("api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch widget_configs for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to resolve referral code")

    if not wc_result.data:
        raise HTTPException(
            status_code=404,
            detail="No widget config found — complete widget setup first",
        )

    ref_code: str = wc_result.data[0]["api_key"]

    # Step 2: aggregate click counts
    now = datetime.now(timezone.utc)
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    cutoff_30d = (now - timedelta(days=30)).isoformat()

    try:
        total_result = (
            db.table("referral_clicks")
            .select("id", count="exact")
            .eq("ref_tenant_id", ref_code)
            .execute()
        )
        last_7d_result = (
            db.table("referral_clicks")
            .select("id", count="exact")
            .eq("ref_tenant_id", ref_code)
            .gte("created_at", cutoff_7d)
            .execute()
        )
        last_30d_result = (
            db.table("referral_clicks")
            .select("id", count="exact")
            .eq("ref_tenant_id", ref_code)
            .gte("created_at", cutoff_30d)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to aggregate referral_clicks for ref_code=%s", ref_code
        )
        raise HTTPException(status_code=500, detail="Failed to fetch referral stats")

    # Step 3: count tenants that signed up via this widget's referral link
    try:
        signups_result = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("referred_by_widget_key", ref_code)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to count referred signups for ref_code=%s", ref_code
        )
        raise HTTPException(status_code=500, detail="Failed to fetch referral stats")

    # Supabase count= returns count on the result object; data length as fallback
    def _count(result) -> int:
        if result.count is not None:
            return int(result.count)
        return len(result.data) if result.data else 0

    return ReferralStatsResponse(
        ref_code=ref_code,
        share_link=_SHARE_BASE.format(ref_code=ref_code),
        total_clicks=_count(total_result),
        clicks_last_7d=_count(last_7d_result),
        clicks_last_30d=_count(last_30d_result),
        referred_signups=_count(signups_result),
    )


@router.post("/click")
@limiter.limit("30/minute")
async def record_referral_click(
    request: Request,
    body: ReferralClickRequest,
):
    """Record a watermark click from an embedded widget.

    `ref` is the tenant's API key (from the widget's data-api-key attribute).
    `path` is the page path on the tenant's site where the click happened.
    `referrer` is the HTTP Referer header captured by the widget.
    """
    db = get_service_supabase()

    try:
        db.table("referral_clicks").insert(
            {
                "ref_tenant_id": body.ref,
                "path": body.path,
                "referrer": body.referrer,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to record referral click for ref=%s", body.ref)

    # Always return 204-equivalent OK — don't leak errors to the browser
    return {"ok": True}
