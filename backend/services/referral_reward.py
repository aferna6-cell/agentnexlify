"""Referral reward service — grant a referrer a Stripe balance credit.

Fires when a tenant pays their FIRST invoice (subscription activation). The
referrer who brought them in earns a flat $20 credit, applied as a negative
Stripe customer balance that auto-deducts from the referrer's next invoice.

Design (locked 2026-06-23):
  - $20 flat (REFERRAL_REWARD_CENTS), referrer only, on first paid invoice.
  - Delivery: stripe.Customer.create_balance_transaction(amount=-2000) —
    a negative balance is a credit Stripe applies to the next invoice.

Attribution resolves from the existing tracking columns on tenants:
  - referred_by             UUID → promo-code channel (migration 135)
  - referred_by_widget_key  TEXT → widget-watermark channel (migration 159)
                                   resolves api_key → widget_configs.tenant_id

Idempotency contract:
  - referral_rewards.referred_tenant_id is UNIQUE (migration 160).
  - We claim the row FIRST (status='pending'); a duplicate insert means the
    reward was already handled — we skip. This makes the grant safe against
    Stripe webhook redeliveries AND the two parallel webhook endpoints.

Failure contract: NEVER raises. A failed reward must not 500 a Stripe webhook
(that would make Stripe retry the whole event, re-running the whole handler).
On any error the row is marked status='failed' with the error captured.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Flat reward, in cents. Negative when applied to a Stripe balance.
REFERRAL_REWARD_CENTS = 2000  # $20.00
REFERRAL_REWARD_CURRENCY = "usd"


def reward_enabled() -> bool:
    """Kill-switch for the reward grant. Default OFF: granting real Stripe
    credits is an owner decision — a platform_settings row for
    'referral_reward_enabled' (migration 175) or REFERRAL_REWARD_ENABLED=1
    in Railway launches the program. Tracking/attribution stays on either
    way; only the money grant is gated."""
    from backend.services.platform_flags import flag_enabled

    env_on = os.environ.get("REFERRAL_REWARD_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    return flag_enabled("referral_reward_enabled", env_default=env_on)


def _resolve_referrer(db, referred_tenant_id):
    """Resolve who referred `referred_tenant_id`.

    Returns (referrer_tenant_id, channel) or None if there's no referrer.
    channel is 'promo_code' or 'widget_watermark'. Self-referrals return None.
    """
    tenant_result = (
        db.table("tenants")
        .select("referred_by, referred_by_widget_key")
        .eq("id", referred_tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        return None

    row = tenant_result.data[0]

    # Promo-code channel wins when both are set — it's the explicit, validated
    # attribution (referred_by is a real tenant UUID FK).
    referred_by = row.get("referred_by")
    if referred_by:
        referrer_tenant_id = str(referred_by)
        if referrer_tenant_id == str(referred_tenant_id):
            logger.warning(
                "referral_reward: self-referral (promo) for tenant %s — skipping",
                referred_tenant_id,
            )
            return None
        return referrer_tenant_id, "promo_code"

    # Widget-watermark channel: stored value is the referrer's widget api_key.
    widget_key = (row.get("referred_by_widget_key") or "").strip()
    if widget_key:
        wc_result = (
            db.table("widget_configs")
            .select("tenant_id")
            .eq("api_key", widget_key)
            .limit(1)
            .execute()
        )
        if not wc_result.data:
            logger.debug(
                "referral_reward: widget_key not resolvable to a tenant — no referrer"
            )
            return None
        referrer_tenant_id = str(wc_result.data[0]["tenant_id"])
        if referrer_tenant_id == str(referred_tenant_id):
            logger.warning(
                "referral_reward: self-referral (widget) for tenant %s — skipping",
                referred_tenant_id,
            )
            return None
        return referrer_tenant_id, "widget_watermark"

    return None


def _claim_reward_row(db, *, referrer_tenant_id, referred_tenant_id, channel):
    """Insert the pending reward row. Return its id, or None if already claimed.

    The UNIQUE(referred_tenant_id) index makes the second insert fail — that's
    how we detect "already rewarded" and stay idempotent.
    """
    try:
        result = (
            db.table("referral_rewards")
            .insert(
                {
                    "referrer_tenant_id": referrer_tenant_id,
                    "referred_tenant_id": referred_tenant_id,
                    "amount_cents": REFERRAL_REWARD_CENTS,
                    "currency": REFERRAL_REWARD_CURRENCY,
                    "attribution_channel": channel,
                    "status": "pending",
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception:
        # Unique-violation (already rewarded) lands here, as does any insert
        # failure. Either way we must not grant — log and bail.
        logger.info(
            "referral_reward: reward already claimed (or insert failed) for "
            "referred tenant %s — skipping grant",
            referred_tenant_id,
        )
        return None


def _grant_sync(referred_tenant_id):
    """Synchronous grant flow. Network + DB work; called via a thread.

    Steps: resolve referrer → claim idempotency row → ensure referrer Stripe
    customer → apply -$20 balance → record outcome. Never raises.
    """
    from backend.models.database import get_service_supabase

    db = get_service_supabase()

    try:
        resolved = _resolve_referrer(db, referred_tenant_id)
    except Exception:
        logger.warning(
            "referral_reward: referrer resolution failed for tenant %s — skipping",
            referred_tenant_id,
            exc_info=True,
        )
        return

    if not resolved:
        logger.debug(
            "referral_reward: no referrer for tenant %s — nothing to grant",
            referred_tenant_id,
        )
        return

    referrer_tenant_id, channel = resolved

    reward_id = _claim_reward_row(
        db,
        referrer_tenant_id=referrer_tenant_id,
        referred_tenant_id=referred_tenant_id,
        channel=channel,
    )
    if not reward_id:
        return  # already rewarded or claim failed — idempotent no-op

    # From here, any failure marks the claimed row 'failed' so it's visible /
    # retryable out of band, and never bubbles into the webhook handler.
    try:
        tenant_result = (
            db.table("tenants")
            .select("owner_email, business_name")
            .eq("id", referrer_tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            _mark_failed(db, reward_id, "referrer tenant not found")
            return

        referrer = tenant_result.data[0]
        owner_email = (referrer.get("owner_email") or "").strip()
        if not owner_email:
            _mark_failed(db, reward_id, "referrer has no owner_email")
            return

        from backend.services.stripe_service import get_or_create_customer
        import stripe

        customer = get_or_create_customer(
            email=owner_email,
            tenant_id=referrer_tenant_id,
            business_name=referrer.get("business_name"),
        )

        txn = stripe.Customer.create_balance_transaction(
            customer.id,
            amount=-REFERRAL_REWARD_CENTS,  # negative = credit toward next invoice
            currency=REFERRAL_REWARD_CURRENCY,
            description=(
                f"AgentNexLiFy referral reward — referred tenant {referred_tenant_id}"
            ),
            metadata={
                "kind": "referral_reward",
                "referred_tenant_id": str(referred_tenant_id),
                "referrer_tenant_id": str(referrer_tenant_id),
                "channel": channel,
            },
        )

        db.table("referral_rewards").update(
            {
                "status": "granted",
                "stripe_customer_id": customer.id,
                "stripe_balance_txn_id": txn.id,
                "granted_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", reward_id).execute()

        logger.info(
            "referral_reward: granted $%.2f to referrer %s for referred %s (channel=%s, txn=%s)",
            REFERRAL_REWARD_CENTS / 100,
            referrer_tenant_id,
            referred_tenant_id,
            channel,
            txn.id,
        )

        # GH #413: tell the referrer their credit landed. Own try/except so
        # NOTHING in the email path can reach the outer handler and flip the
        # already-granted row to failed.
        try:
            referred_name = ""
            referred_result = (
                db.table("tenants")
                .select("business_name")
                .eq("id", referred_tenant_id)
                .limit(1)
                .execute()
            )
            if referred_result.data:
                referred_name = referred_result.data[0].get("business_name") or ""
            from backend.services.referral_reward_email import (
                notify_reward_granted_sync,
            )

            notify_reward_granted_sync(
                recipient=owner_email,
                referrer_name=referrer.get("business_name") or "",
                referred_name=referred_name,
                amount_cents=REFERRAL_REWARD_CENTS,
            )
        except Exception:
            logger.warning(
                "referral_reward: reward email failed — credit stays granted",
                exc_info=True,
            )
    except Exception as exc:
        _mark_failed(db, reward_id, f"{type(exc).__name__}: {exc}")
        logger.warning(
            "referral_reward: grant failed for referrer %s (referred %s) — row marked failed",
            referrer_tenant_id,
            referred_tenant_id,
            exc_info=True,
        )


def _mark_failed(db, reward_id, reason):
    """Best-effort mark of a reward row as failed. Swallows its own errors."""
    try:
        db.table("referral_rewards").update(
            {"status": "failed", "error": str(reason)[:500]}
        ).eq("id", reward_id).execute()
    except Exception:
        logger.warning(
            "referral_reward: could not mark reward %s failed", reward_id, exc_info=True
        )


async def grant_referral_reward_for_signup(*, referred_tenant_id):
    """Award the referrer when `referred_tenant_id` pays their first invoice.

    Awaitable, never raises. Runs the blocking Stripe/DB work in a thread so it
    doesn't stall the webhook event loop. Mirrors owner_alerts.notify_* shape.
    """
    if not referred_tenant_id:
        return
    if not reward_enabled():
        logger.info(
            "referral_reward: REFERRAL_REWARD_ENABLED is off — skipping grant for %s",
            referred_tenant_id,
        )
        return
    try:
        await asyncio.to_thread(_grant_sync, str(referred_tenant_id))
    except Exception:
        logger.warning(
            "referral_reward: background grant failed for tenant %s",
            referred_tenant_id,
            exc_info=True,
        )
