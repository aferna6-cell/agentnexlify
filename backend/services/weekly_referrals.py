"""Weekly referral stats — what a tenant's referral link earned this period.

The public referral identity is ``tenants.referral_code``. Legacy clicks and
signups stored under ``widget_configs.api_key`` are still counted, but that
key is never returned.

Both reads are fault-tolerant — a partial recap beats a 500. The digest is
best-effort, so this returns zeros on any failure and never raises.
"""

import logging
from typing import Any

from backend.services.referral import is_public_referral_code

logger = logging.getLogger(__name__)


def _count(result) -> int:
    if result is None:
        return 0
    if result.count is not None:
        return int(result.count)
    return len(result.data or [])


def compute_weekly_referrals(db: Any, tenant_id: str, since: str) -> dict[str, Any]:
    """Period-bounded referral numbers for one tenant. Zeroes on failure, never raises.

    ``ref_code`` is the public referral code, or "" when the tenant has none.
    It is never the widget API key.
    """
    out: dict[str, Any] = {
        "ref_code": "",
        "referral_clicks": 0,
        "referred_signups": 0,
    }

    public = ""
    try:
        row = (
            db.table("tenants")
            .select("referral_code")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        code = (row.data or [{}])[0].get("referral_code") if row.data else ""
        if is_public_referral_code(code):
            public = code.strip()
    except Exception:
        logger.warning(
            "weekly_referrals: referral_code lookup failed for %s",
            tenant_id,
            exc_info=True,
        )

    legacy = ""
    try:
        wc = (
            db.table("widget_configs")
            .select("api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        key = (wc.data or [{}])[0].get("api_key") if wc.data else ""
        if key and key != public and not is_public_referral_code(key):
            legacy = key
    except Exception:
        logger.warning(
            "weekly_referrals: widget_configs lookup failed for %s",
            tenant_id,
            exc_info=True,
        )

    out["ref_code"] = public
    identities = [value for value in (public, legacy) if value]
    if not identities:
        return out

    for ident in identities:
        try:
            clicks = (
                db.table("referral_clicks")
                .select("id", count="exact")
                .eq("ref_tenant_id", ident)
                .gte("created_at", since)
                .limit(1)
                .execute()
            )
            out["referral_clicks"] += _count(clicks)
        except Exception:
            logger.warning(
                "weekly_referrals: referral_clicks count failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

    try:
        by_referrer = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("referred_by", tenant_id)
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["referred_signups"] += _count(by_referrer)
    except Exception:
        logger.warning(
            "weekly_referrals: referred_by count failed for %s",
            tenant_id,
            exc_info=True,
        )

    if legacy:
        try:
            by_key = (
                db.table("tenants")
                .select("id", count="exact")
                .eq("referred_by_widget_key", legacy)
                .gte("created_at", since)
                .limit(1)
                .execute()
            )
            out["referred_signups"] += _count(by_key)
        except Exception:
            logger.warning(
                "weekly_referrals: legacy signup count failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

    return out
