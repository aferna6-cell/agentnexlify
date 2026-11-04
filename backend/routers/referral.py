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
from backend.services.referral import (
    decide_referral_click,
    public_share_link,
    record_unrecordable_referral_click,
)
from backend.services.referral_overview import compute_referral_overview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/referral", tags=["referral"])

# Every click acknowledgment is this exact body. Valid and unknown anx_ keys
# must not be distinguishable from the HTTP response.
_CLICK_OK = {"ok": True}


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
            ref_code         str — tenant's public referral code (never the widget api key)
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
    rewards_count: int
    rewards_earned_cents: int


# NOTE: static route /my-stats MUST appear before any /{param} route.
# FastAPI matches in registration order — param routes would shadow statics otherwise.
@router.get("/my-stats", response_model=ReferralStatsResponse)
async def get_my_referral_stats(
    claims: dict = Depends(_get_current_tenant),
):
    """Return referral stats for the calling tenant.

    Resolution chain:
    1. Extract tenant_id from JWT claims (set by _get_current_tenant).
    2. Read tenants.referral_code. That public code is the only value returned.
       A widget api_key is loaded only to count legacy clicks and signups;
       it is never placed in the response.
    3. Aggregate click counts for the public code and, when present, the legacy key.
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing tenant_id")

    db = get_service_supabase()

    try:
        tenant_result = (
            db.table("tenants")
            .select("referral_code")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch referral_code for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to resolve referral code")

    raw_code = (tenant_result.data or [{}])[0].get("referral_code") if tenant_result.data else None
    # NULL or anx_ (pre-migration-202 rows) fall back to a link with no ref.
    ref_code, share_link = public_share_link(raw_code)

    legacy_key = ""
    try:
        wc_result = (
            db.table("widget_configs")
            .select("api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if wc_result.data:
            legacy_key = wc_result.data[0].get("api_key") or ""
    except Exception:
        logger.exception("Failed to fetch widget_configs for tenant_id=%s", tenant_id)
        legacy_key = ""

    if not legacy_key.startswith("anx_"):
        legacy_key = ""

    # Step 2: aggregate click counts
    now = datetime.now(timezone.utc)
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    cutoff_30d = (now - timedelta(days=30)).isoformat()

    click_ids = [ref_code] if ref_code else []
    if legacy_key and legacy_key not in click_ids:
        click_ids.append(legacy_key)

    def _click_count(since: str | None) -> int:
        total = 0
        for ident in click_ids:
            query = (
                db.table("referral_clicks")
                .select("id", count="exact")
                .eq("ref_tenant_id", ident)
            )
            if since:
                query = query.gte("created_at", since)
            result = query.execute()
            if result.count is not None:
                total += int(result.count)
            else:
                total += len(result.data or [])
        return total

    try:
        total_clicks = _click_count(None)
        clicks_last_7d = _click_count(cutoff_7d)
        clicks_last_30d = _click_count(cutoff_30d)
    except Exception:
        logger.exception("Failed to aggregate referral_clicks for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch referral stats")

    # Signups: new links set referred_by (tenant UUID). Old links stored the
    # widget key on referred_by_widget_key. Count both. Never return the key.
    try:
        by_referrer = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("referred_by", tenant_id)
            .execute()
        )
        referred_signups = (
            int(by_referrer.count)
            if by_referrer.count is not None
            else len(by_referrer.data or [])
        )
        if legacy_key:
            by_key = (
                db.table("tenants")
                .select("id", count="exact")
                .eq("referred_by_widget_key", legacy_key)
                .execute()
            )
            referred_signups += (
                int(by_key.count) if by_key.count is not None else len(by_key.data or [])
            )
    except Exception:
        logger.exception("Failed to count referred signups for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to fetch referral stats")

    # Step 4: sum the credit this tenant has earned as a referrer.
    # referral_rewards.referrer_tenant_id == this tenant's UUID; only 'granted'
    # rows count toward earned credit (pending/failed are not money in hand).
    rewards_count = 0
    rewards_earned_cents = 0
    try:
        rewards_result = (
            db.table("referral_rewards")
            .select("amount_cents")
            .eq("referrer_tenant_id", tenant_id)
            .eq("status", "granted")
            .execute()
        )
        for row in rewards_result.data or []:
            rewards_count += 1
            rewards_earned_cents += int(row.get("amount_cents") or 0)
    except Exception:
        # Non-fatal: rewards panel shows zero rather than failing the whole page.
        logger.exception(
            "Failed to aggregate referral_rewards for tenant_id=%s", tenant_id
        )

    return ReferralStatsResponse(
        ref_code=ref_code,
        share_link=share_link,
        total_clicks=total_clicks,
        clicks_last_7d=clicks_last_7d,
        clicks_last_30d=clicks_last_30d,
        referred_signups=referred_signups,
        rewards_count=rewards_count,
        rewards_earned_cents=rewards_earned_cents,
    )


@router.post("/click")
@limiter.limit("30/minute")
async def record_referral_click(
    request: Request,
    body: ReferralClickRequest,
):
    """Record a watermark click from an embedded widget.

    ``ref`` is the tenant's public referral code. Legacy widget API keys are
    rewritten to that public code. The key is never stored.

    Before migration 202, a real key can belong to a tenant whose
    ``referral_code`` is still NULL or ``anx_``. That click is stored under
    the tenant id (not the key). The handler also emits an error log and
    increments ``referral_click_unrecordable_total``. It does not drop the
    click and return ok with no record and no log. An unknown key still
    inserts nothing and returns the same ``{"ok": True}`` body.
    """
    db = get_service_supabase()
    try:
        decision = decide_referral_click(db, body.ref)
    except Exception:
        logger.exception("Failed to resolve referral click")
        return _CLICK_OK
    if decision.loud_unrecordable and decision.tenant_id:
        record_unrecordable_referral_click(decision.tenant_id)
    if not decision.store_as:
        return _CLICK_OK

    try:
        db.table("referral_clicks").insert(
            {
                "ref_tenant_id": decision.store_as,
                "path": body.path,
                "referrer": body.referrer,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to record referral click")

    return _CLICK_OK
