"""Referral attribution service.

Validates ?ref=CODE at signup against the admin_promotions table (promotion_type='referral').
Stores attribution on the new tenant row via tenants.referred_by (FK) and
tenants.referral_discount_pct when a matching active referral promo exists.

Security contract:
- Invalid / expired code → silently ignored, signup proceeds normally.
- Never log the code alongside any PII (email/business_name).
- Validation is entirely server-side; client never receives discount details.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_MAX_CODE_LEN = 200  # guard against oversized input


def apply_referral_attribution(
    db,
    *,
    new_tenant_id: str,
    ref_code: str | None,
) -> None:
    """Attempt to attribute the new tenant to a referral promo code.

    Args:
        db: Supabase service client.
        new_tenant_id: UUID string of the freshly-created tenant row.
        ref_code: Raw value from the ?ref= query param, or None.

    Side-effects on success:
        - Sets tenants.referred_by = referring_tenant_id
        - Sets tenants.referral_discount_pct = promo.discount_pct  (if > 0)

    Silently returns on any error so signup is never blocked.
    """
    if not ref_code:
        return

    # Sanitise: strip whitespace, enforce max length, reject empty
    ref_code = ref_code.strip()[:_MAX_CODE_LEN]
    if not ref_code:
        return

    try:
        # Look up tenant whose referral_code matches
        tenant_result = (
            db.table("tenants")
            .select("id")
            .eq("referral_code", ref_code)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            logger.debug("referral: code not found — ignoring (no PII logged)")
            return

        referring_tenant_id = str(tenant_result.data[0]["id"])

        # Avoid self-referral
        if referring_tenant_id == new_tenant_id:
            logger.warning(
                "referral: self-referral attempt blocked for tenant %s", new_tenant_id
            )
            return

        # Check for an active referral promotion for the referring tenant
        now_iso = datetime.now(timezone.utc).isoformat()
        promo_result = (
            db.table("admin_promotions")
            .select("id, discount_pct, expires_at")
            .eq("tenant_id", referring_tenant_id)
            .eq("promotion_type", "referral")
            .execute()
        )
        promos = promo_result.data or []

        # Pick the first non-expired promo (or any promo if no expires_at check fails)
        active_promo = None
        for promo in promos:
            expires_at = promo.get("expires_at")
            if expires_at is None:
                active_promo = promo
                break
            try:
                if expires_at > now_iso:
                    active_promo = promo
                    break
            except Exception:
                active_promo = promo
                break

        # Write attribution to the new tenant row
        updates: dict = {"referred_by": referring_tenant_id}
        if active_promo and (active_promo.get("discount_pct") or 0) > 0:
            updates["referral_discount_pct"] = active_promo["discount_pct"]

        db.table("tenants").update(updates).eq("id", new_tenant_id).execute()
        logger.info(
            "referral: tenant %s attributed to referrer %s (promo=%s)",
            new_tenant_id,
            referring_tenant_id,
            active_promo.get("id") if active_promo else "none",
        )

    except Exception:
        # Never block signup on referral lookup failure
        logger.warning(
            "referral: attribution lookup failed for new tenant %s — ignored",
            new_tenant_id,
            exc_info=True,
        )
