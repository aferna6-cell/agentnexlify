"""Referral click tracking — records watermark clicks from tenant-embedded widgets.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/referral", tags=["referral"])

_SHARE_BASE = "https://agentnexlify.com?ref={ref_code}&utm_source=widget"


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
