"""Weekly referral stats — what a tenant's referral link earned this period.

Cross-pollinates the existing referral measurement (routers/referral.py +
services/referral.py) into the Friday weekly value digest so tenants see
"you referred N signups this week" in an email they already open.

Schema notes
------------
A tenant's referral identity is their widget embed key: ``widget_configs.api_key``.
- ``referral_clicks.ref_tenant_id`` stores that key (set when a visitor clicks a
  ?ref=<key> share link).
- ``tenants.referred_by_widget_key`` stores that key on a newly-signed-up tenant
  (set at auth signup, migration 159).

Both reads are fault-tolerant — a partial recap beats a 500. The digest is
best-effort, so this returns zeros on any failure and never raises.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_weekly_referrals(db: Any, tenant_id: str, since: str) -> dict[str, Any]:
    """Period-bounded referral numbers for one tenant. Zeroes on failure, never raises.

    Parameters
    ----------
    db:        Supabase client (service role).
    tenant_id: The referring tenant's id (``tenants.id`` / ``widget_configs.tenant_id``).
    since:     ISO-8601 timestamp lower bound (inclusive). Same ``since`` the
               weekly value recap uses, so clicks/signups align to one window.

    Returns
    -------
    dict with keys:
        ref_code         str  — the tenant's widget api_key (referral identity), or "".
        referral_clicks  int  — share-link clicks attributed to this tenant in window.
        referred_signups int  — tenants that signed up via this link in window.
    """
    out: dict[str, Any] = {
        "ref_code": "",
        "referral_clicks": 0,
        "referred_signups": 0,
    }

    # Resolve the tenant's referral identity (their widget embed key).
    ref_code = ""
    try:
        wc = (
            db.table("widget_configs")
            .select("api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
        if wc:
            ref_code = wc[0].get("api_key") or ""
    except Exception:
        logger.warning(
            "weekly_referrals: widget_configs lookup failed for %s", tenant_id, exc_info=True
        )

    # No embed key → tenant has no referral identity yet; nothing to count.
    if not ref_code:
        return out
    out["ref_code"] = ref_code

    # Share-link clicks in window.
    try:
        r = (
            db.table("referral_clicks")
            .select("id", count="exact")
            .eq("ref_tenant_id", ref_code)
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["referral_clicks"] = r.count or 0
    except Exception:
        logger.warning(
            "weekly_referrals: referral_clicks count failed for %s", ref_code, exc_info=True
        )

    # Tenants who signed up via this link in window.
    try:
        r = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("referred_by_widget_key", ref_code)
            .gte("created_at", since)
            .limit(1)
            .execute()
        )
        out["referred_signups"] = r.count or 0
    except Exception:
        logger.warning(
            "weekly_referrals: referred signups count failed for %s", ref_code, exc_info=True
        )

    return out
