"""Referral attribution service.

Two independent attribution paths:

1. apply_referral_attribution — promo-code path (existing).
   Validates ?ref=CODE against admin_promotions (promotion_type='referral').
   Stores referring tenant UUID in tenants.referred_by (UUID FK) and
   discount in tenants.referral_discount_pct.

2. apply_widget_referral_attribution — widget-watermark path (new).
   Validates ?ref=<api_key> against widget_configs.api_key.
   Stores the raw api_key in tenants.referred_by_widget_key (TEXT).
   Used by the referral stats endpoint to count referred_signups.

3. notify_referrer_of_signup — fire-and-forget email to the referrer.
   Called after apply_widget_referral_attribution succeeds.
   Resolves the referrer's owner_email and sends a short plain notification.

Security contract for all:
- Invalid / expired / unknown code → silently ignored, signup proceeds.
- Never log the raw code alongside PII (email/business_name).
- Validation is entirely server-side.
"""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_MAX_CODE_LEN = 200  # guard against oversized input
# Public share codes are short alphanumeric tokens minted at signup
# (secrets.token_hex) or by migration 202. Widget API keys start with anx_
# and must never be treated as a public code.
_PUBLIC_CODE_RE = re.compile(r"^[A-Za-z0-9]{6,32}$")


def is_public_referral_code(code: str | None) -> bool:
    """True when ``code`` is safe to put in a URL or API response."""
    if not code:
        return False
    text = code.strip()
    if text.startswith("anx_"):
        return False
    return _PUBLIC_CODE_RE.match(text) is not None


# Before migration 202, referral_code may be NULL or still equal the widget
# key. Those tenants get a link with no ref= parameter. The key is never used.
SHARE_LINK_NO_REF = "https://agentnexlify.com?utm_source=widget"
SHARE_LINK_WITH_REF = "https://agentnexlify.com?ref={ref_code}&utm_source=widget"


def public_share_link(code: str | None) -> tuple[str, str]:
    """Return ``(public_code, share_link)``.

    A NULL or ``anx_`` code yields an empty code and a link with no ``ref``.
    """
    if is_public_referral_code(code):
        public = code.strip()
        return public, SHARE_LINK_WITH_REF.format(ref_code=public)
    return "", SHARE_LINK_NO_REF


def resolve_public_click_ref(db, ref: str | None) -> str | None:
    """Map a click or share ``ref`` to the public referral code.

    A legacy ``anx_`` widget key still resolves, but the returned value is
    the tenant's public code. The key itself is never returned or stored.
    Unknown refs return None.
    """
    if not ref:
        return None
    raw = ref.strip()[:_MAX_CODE_LEN]
    if not raw:
        return None

    if is_public_referral_code(raw):
        try:
            found = (
                db.table("tenants")
                .select("id")
                .eq("referral_code", raw)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning("referral: public code lookup failed", exc_info=True)
            return None
        return raw if found.data else None

    if not raw.startswith("anx_"):
        return None

    try:
        wc = (
            db.table("widget_configs")
            .select("tenant_id")
            .eq("api_key", raw)
            .limit(1)
            .execute()
        )
        if not wc.data:
            return None
        tenant_id = wc.data[0].get("tenant_id")
        if not tenant_id:
            return None
        tenant = (
            db.table("tenants")
            .select("referral_code")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("referral: legacy key resolution failed", exc_info=True)
        return None
    if not tenant.data:
        return None
    code = tenant.data[0].get("referral_code")
    return code if is_public_referral_code(code) else None


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


def apply_widget_referral_attribution(
    db,
    *,
    new_tenant_id: str,
    ref: str | None,
) -> None:
    """Attribute a new tenant to the widget-watermark referral channel.

    Args:
        db: Supabase service client.
        new_tenant_id: UUID string of the freshly-created tenant row.
        ref: Raw value from the ?ref= query param (expected to be a
             widget_configs.api_key), or None.

    Side-effects on success:
        - Sets tenants.referred_by_widget_key = ref  (the referrer's api_key)

    Silently returns on any error so signup is never blocked.
    This is intentionally lenient: an unrecognised ref is silently dropped.
    """
    if not ref:
        return

    # Sanitise: strip whitespace, enforce max length, reject empty
    ref = ref.strip()[:_MAX_CODE_LEN]
    if not ref:
        return

    try:
        # Validate the ref is a real widget_configs.api_key
        wc_result = (
            db.table("widget_configs")
            .select("tenant_id")
            .eq("api_key", ref)
            .limit(1)
            .execute()
        )
        if not wc_result.data:
            logger.debug(
                "widget-referral: api_key not found in widget_configs — ignored"
            )
            return

        referring_tenant_id = str(wc_result.data[0]["tenant_id"])

        # Avoid self-referral (same tenant signing up with their own widget key)
        if referring_tenant_id == new_tenant_id:
            logger.warning(
                "widget-referral: self-referral attempt blocked for tenant %s",
                new_tenant_id,
            )
            return

        db.table("tenants").update(
            {"referred_by_widget_key": ref}
        ).eq("id", new_tenant_id).execute()

        logger.info(
            "widget-referral: tenant %s attributed to referrer tenant %s via api_key",
            new_tenant_id,
            referring_tenant_id,
        )

    except Exception:
        # Never block signup on referral lookup failure
        logger.warning(
            "widget-referral: attribution failed for new tenant %s — ignored",
            new_tenant_id,
            exc_info=True,
        )


async def notify_referrer_of_signup(
    db,
    *,
    widget_key: str,
) -> None:
    """Send a short email to the referrer when someone signs up via their link.

    Fire-and-forget — never raises.  Silently skips if the widget_key is
    unresolvable or the referrer has no owner_email configured.

    Args:
        db: Supabase service client.
        widget_key: The raw api_key stored in tenants.referred_by_widget_key.
    """
    if not widget_key:
        return

    try:
        from backend.services.platform_mailer import send_platform_email
        from backend.config import settings as _settings

        # Public codes resolve on tenants.referral_code. Legacy widget keys
        # still resolve through widget_configs, but the key is not emailed.
        if is_public_referral_code(widget_key):
            public_result = (
                db.table("tenants")
                .select("id, owner_email")
                .eq("referral_code", widget_key.strip())
                .limit(1)
                .execute()
            )
            if public_result.data and public_result.data[0].get("id"):
                referring_tenant_id = str(public_result.data[0]["id"])
                owner_email = (public_result.data[0].get("owner_email") or "").strip()
                if owner_email:
                    frontend_url = (_settings.frontend_url or "").rstrip("/")
                    referral_dashboard_url = f"{frontend_url}/dashboard/referral"
                    body_html = (
                        "<p>Good news — someone just signed up for AgentNexLiFy through "
                        "your referral link.</p>"
                        f'<p>View your referral stats: <a href="{referral_dashboard_url}">'
                        f"{referral_dashboard_url}</a></p>"
                    )
                    await send_platform_email(
                        subject="Someone signed up through your referral link",
                        body_html=body_html,
                        recipient=owner_email,
                    )
                    logger.info(
                        "referral-notify: email sent to referrer tenant %s",
                        referring_tenant_id,
                    )
                return

        # Resolve widget_key → referrer tenant_id
        wc_result = (
            db.table("widget_configs")
            .select("tenant_id")
            .eq("api_key", widget_key)
            .limit(1)
            .execute()
        )
        if not wc_result.data:
            logger.debug("referral-notify: widget_key not found — skipping email")
            return

        referring_tenant_id = str(wc_result.data[0]["tenant_id"])

        # Resolve tenant_id → owner_email
        tenant_result = (
            db.table("tenants")
            .select("owner_email")
            .eq("id", referring_tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            logger.debug(
                "referral-notify: referrer tenant %s not found — skipping email",
                referring_tenant_id,
            )
            return

        owner_email = (tenant_result.data[0].get("owner_email") or "").strip()
        if not owner_email:
            logger.debug(
                "referral-notify: referrer tenant %s has no owner_email — skipping",
                referring_tenant_id,
            )
            return

        frontend_url = (_settings.frontend_url or "").rstrip("/")
        referral_dashboard_url = f"{frontend_url}/dashboard/referral"

        body_html = (
            "<p>Good news — someone just signed up for AgentNexLiFy through "
            "your referral link.</p>"
            f'<p>View your referral stats: <a href="{referral_dashboard_url}">'
            f"{referral_dashboard_url}</a></p>"
        )

        await send_platform_email(
            subject="Someone signed up through your referral link",
            body_html=body_html,
            recipient=owner_email,
        )
        logger.info(
            "referral-notify: email sent to referrer tenant %s", referring_tenant_id
        )

    except Exception:
        # Never let notification failure affect the caller
        logger.warning(
            "referral-notify: failed for widget_key (redacted) — ignored",
            exc_info=True,
        )
