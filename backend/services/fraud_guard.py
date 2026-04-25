"""Fraud guardrails — disposable email block, velocity limits, checkout risk checks."""

import logging
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import HTTPException, Request
from starlette.requests import Request as StarletteRequest

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Common disposable email domains. Expand via env if needed.
_DISPOSABLE_DOMAINS = frozenset({
    "10minutemail.com", "tempmail.com", "mailinator.com", "guerrillamail.com",
    "yopmail.com", "throwawaymail.com", "temp-mail.org", "fakeinbox.com",
    "sharklasers.com", "getairmail.com", "burnermail.io", "tempail.com",
    "mailnesia.com", "tempinbox.com", "dispostable.com", "mailcatch.com",
    "getnada.com", "inbox.si", "trashmail.com", "mytemp.email", "mail-temp.com",
    "emailondeck.com", "tempm.com", "throwam.com", "fakemail.net",
    "tempmailbox.com", "mailforspam.com", "tempmails.org", "throwaway.email",
    "mohmal.com", "maildrop.cc", "spamgourmet.com", "bouncr.com",
    "tempmailaddress.com", "tmpmail.org", "eyepaste.com", "gettempmail.com",
    "luxusmail.org", "mailpoof.com", "thrma.com", "tempmailo.com",
    "temporarymail.net", "tmpbox.net", "tmails.net", "trash-mail.at",
    "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org",
})


MAX_SIGNUPS_PER_IP_PER_HOUR = 10
MAX_SIGNUPS_PER_EMAIL_PER_HOUR = 3


def is_disposable_email(email: str) -> bool:
    """Return True if the email domain is a known disposable provider."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower().strip()
    return domain in _DISPOSABLE_DOMAINS


def _get_client_ip(request: Request | StarletteRequest) -> str:
    """Extract real client IP using the same logic as the rate limiter."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    return request.client.host if request.client else "127.0.0.1"


def _record_signup_attempt(ip: str, email: str, tenant_id: str | None, blocked_reason: str | None = None) -> None:
    """Write a signup attempt row for velocity tracking. Best-effort; never raises."""
    try:
        db = get_service_supabase()
        db.table("signup_attempts").insert({
            "ip_address": ip,
            "email": email.lower().strip(),
            "tenant_id": tenant_id,
            "blocked_reason": blocked_reason,
        }).execute()
    except Exception:
        logger.warning("Failed to record signup attempt", exc_info=True)


def check_registration_velocity(request: Request, email: str) -> None:
    """Raise 429 if this IP or email has exceeded signup velocity limits.

    Checks:
      - ≤ MAX_SIGNUPS_PER_IP_PER_HOUR from this IP in the last hour
      - ≤ MAX_SIGNUPS_PER_EMAIL_PER_HOUR for this email in the last hour
    """
    ip = _get_client_ip(request)
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db = get_service_supabase()

    try:
        ip_result = (
            db.table("signup_attempts")
            .select("id", count="exact")
            .eq("ip_address", ip)
            .gte("created_at", since)
            .execute()
        )
        ip_count = ip_result.count if hasattr(ip_result, "count") else len(ip_result.data)
        if ip_count >= MAX_SIGNUPS_PER_IP_PER_HOUR:
            logger.warning("Velocity block: IP %s has %s signups in last hour", ip, ip_count)
            _record_signup_attempt(ip, email, None, blocked_reason="ip_velocity")
            raise HTTPException(status_code=429, detail="Too many signups from this network. Please try again later.")

        email_result = (
            db.table("signup_attempts")
            .select("id", count="exact")
            .eq("email", email.lower().strip())
            .gte("created_at", since)
            .execute()
        )
        email_count = email_result.count if hasattr(email_result, "count") else len(email_result.data)
        if email_count >= MAX_SIGNUPS_PER_EMAIL_PER_HOUR:
            logger.warning("Velocity block: email %s has %s signups in last hour", email, email_count)
            _record_signup_attempt(ip, email, None, blocked_reason="email_velocity")
            raise HTTPException(status_code=429, detail="Too many signups for this email. Please try again later.")
    except HTTPException:
        raise
    except Exception:
        logger.warning("Signup velocity check failed; allowing through", exc_info=True)


def guard_checkout_for_fraud(session: dict) -> str | None:
    """Inspect a Stripe checkout session for fraud signals.

    Returns a human-readable reason string if the checkout looks risky,
    or None if it passes.

    Signals checked:
      - payment_status != 'paid'
      - Radar outcome == 'blocked'
      - Card country != billing country (simple CC mismatch heuristic)
    """
    payment_status = session.get("payment_status")
    if payment_status != "paid":
        return f"payment_status={payment_status}"

    payment_intent_id = session.get("payment_intent")
    if not payment_intent_id:
        return "no_payment_intent"

    try:
        pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception:
        logger.warning("Could not retrieve payment intent %s for fraud check", payment_intent_id, exc_info=True)
        return None  # Be permissive if Stripe lookup fails

    radar = pi.get("charges", {}).get("data", [{}])[0].get("outcome", {})
    radar_outcome = radar.get("type") or radar.get("network_status")
    if radar_outcome == "blocked":
        return "radar_blocked"

    # CC mismatch heuristic: card country vs billing address country
    card_country = (
        pi.get("charges", {}).get("data", [{}])[0]
        .get("payment_method_details", {})
        .get("card", {})
        .get("country")
    )
    billing_country = pi.get("charges", {}).get("data", [{}])[0].get("billing_details", {}).get("address", {}).get("country")
    if card_country and billing_country and card_country.upper() != billing_country.upper():
        logger.info(
            "CC mismatch detected: card_country=%s billing_country=%s pi=%s",
            card_country, billing_country, payment_intent_id,
        )
        return "cc_country_mismatch"

    return None
