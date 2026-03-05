"""Stripe webhook endpoint at /api/v1/webhooks/stripe.

Delegates to the same handlers in billing.py. This gives Stripe a
dedicated /webhooks/ URL while keeping the logic in one place.
"""


import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.billing import (
    _handle_checkout_completed,
    _handle_payment_failed,
    _handle_subscription_deleted,
    _handle_subscription_updated,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events via /api/v1/webhooks/stripe."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except (stripe.SignatureVerificationError, Exception) as exc:
        if "SignatureVerification" in type(exc).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature")
        raise

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook received: type=%s, id=%s", event_type, event.get("id"))
    db = get_supabase()

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(db, data)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            _handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            _handle_payment_failed(db, data)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Stripe webhook handler failed for event %s", event_type)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    return {"status": "ok"}
