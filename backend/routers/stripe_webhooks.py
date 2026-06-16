"""Stripe webhook endpoint at /api/v1/webhooks/stripe.

Delegates to the same handlers in billing.py. This gives Stripe a
dedicated /webhooks/ URL while keeping the logic in one place.
"""


import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.idempotency import check_and_record, record_response
from backend.routers.billing import (
    _handle_checkout_completed,
    _handle_payment_failed,
    _handle_payment_succeeded,
    _handle_subscription_deleted,
    _handle_subscription_updated,
    _is_legacy_marketing_addon,
)
from backend.services.webhook_dispatcher import fire_event_background

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
    except stripe.SignatureVerificationError:
        # Bad signature is a client error (or a spoof attempt): 400, no retry.
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception:
        # An unexpected error constructing the event (misconfigured secret,
        # SDK fault) is a server problem: 500 so Stripe retries, and it is
        # logged distinctly from bad-signature attempts. (GH #99: the old
        # `except (SignatureVerificationError, Exception)` union collapsed to
        # Exception and bare-re-raised everything else as an opaque 500.)
        logger.exception("Stripe webhook event construction failed")
        raise HTTPException(status_code=500, detail="Webhook verification failed")

    event_type = event["type"]
    data = event["data"]["object"]
    event_id = event.get("id", "")
    logger.info("Stripe webhook received: type=%s, id=%s", event_type, event_id)
    db = get_service_supabase()

    # Idempotency: skip redeliveries
    is_new, cached = await check_and_record(db, "stripe", event_id)
    if not is_new:
        logger.info("Stripe duplicate event %s — returning cached response", event_id)
        return {"status": "ok"}

    idempotency_key = f"stripe:{event_id}"

    try:
        if event_type == "checkout.session.completed":
            # Check if this is an invoice payment (has invoice_id in metadata)
            metadata = data.get("metadata") or {}
            if metadata.get("invoice_id") and metadata.get("tenant_id"):
                _handle_invoice_payment(db, data)
            elif _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on checkout event (add-on retired 2026-06-10)")
            else:
                activation = _handle_checkout_completed(db, data)
                if activation:
                    from backend.services.owner_alerts import notify_new_paid_signup
                    await notify_new_paid_signup(
                        plan=activation["plan"],
                        amount_total=activation["amount_total"],
                        tenant_id=activation["tenant_id"],
                        customer_email=activation.get("customer_email"),
                    )
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            if _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on subscription event (add-on retired 2026-06-10)")
            else:
                _handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            if _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on subscription event (add-on retired 2026-06-10)")
            else:
                _handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(db, data)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Stripe webhook handler failed for event %s", event_type)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    response_body = {"status": "ok"}
    await record_response(db, idempotency_key, 200, response_body)
    return response_body


def _handle_invoice_payment(db, session: dict) -> None:
    """Handle payment for an AgentNexLiFy invoice (via Stripe Payment Link).

    Updates the invoice status to 'paid', records payment details,
    fires an invoice.paid webhook event, and logs the activity.
    """
    metadata = session.get("metadata") or {}
    invoice_id = metadata.get("invoice_id")
    tenant_id = metadata.get("tenant_id")
    amount_total = session.get("amount_total", 0)  # in cents
    payment_intent = session.get("payment_intent")

    if not invoice_id or not tenant_id:
        logger.warning("_handle_invoice_payment: missing invoice_id or tenant_id in metadata")
        return

    logger.info("Invoice payment received: invoice_id=%s, tenant_id=%s, amount=%s",
                invoice_id, tenant_id, amount_total)

    try:
        existing = db.table("invoices").select(
            "status, stripe_payment_id"
        ).eq("id", invoice_id).eq("tenant_id", tenant_id).limit(1).execute()
    except Exception:
        logger.exception("Failed to load invoice %s before payment update", invoice_id)
        return

    if not existing.data:
        logger.warning("Invoice %s not found for tenant %s", invoice_id, tenant_id)
        return

    current_invoice = existing.data[0]
    if current_invoice.get("status") == "paid":
        logger.info(
            "Invoice %s already marked paid; ignoring duplicate Stripe webhook "
            "(existing_payment=%s, incoming_payment=%s)",
            invoice_id,
            current_invoice.get("stripe_payment_id"),
            payment_intent,
        )
        return

    # Update the invoice to 'paid'
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        result = db.table("invoices").update({
            "status": "paid",
            "paid_at": now_iso,
            "amount_paid": round(amount_total / 100, 2),
            "payment_method": "stripe",
            "stripe_payment_id": payment_intent,
        }).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()

        if not result.data:
            logger.warning("Invoice %s not found for tenant %s", invoice_id, tenant_id)
            return

        invoice = result.data[0]
        logger.info("Invoice %s marked as paid (amount: $%.2f)",
                     invoice.get("invoice_number", invoice_id), round(amount_total / 100, 2))
    except Exception:
        logger.exception("Failed to update invoice %s to paid", invoice_id)
        return

    # Fire webhook event
    try:
        fire_event_background(tenant_id, "invoice.paid", {
            "invoice_id": invoice_id,
            "invoice_number": invoice.get("invoice_number"),
            "total": float(invoice.get("total", 0)),
            "amount_paid": round(amount_total / 100, 2),
            "payment_method": "stripe",
            "lead_id": invoice.get("lead_id"),
            "paid_at": now_iso,
        })
    except Exception:
        logger.warning("Failed to fire invoice.paid webhook for %s", invoice_id, exc_info=True)

    # Log activity
    try:
        from backend.services.activity import log_activity
        lead_id = invoice.get("lead_id")
        log_activity(
            tenant_id=tenant_id,
            activity_type="invoice_paid",
            description=f"Invoice {invoice.get('invoice_number', '')} paid (${round(amount_total / 100, 2):.2f})",
            lead_id=lead_id,
            metadata={"invoice_id": invoice_id, "amount": round(amount_total / 100, 2)},
        )
    except Exception:
        logger.warning("Failed to log invoice.paid activity for %s", invoice_id, exc_info=True)
