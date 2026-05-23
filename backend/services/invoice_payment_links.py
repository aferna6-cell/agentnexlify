"""Stripe Payment Link creation for invoices."""

import logging

import stripe

from backend.services.stripe_service import ensure_stripe_configured

logger = logging.getLogger(__name__)


async def get_or_create_stripe_payment_link(
    invoice_id: str, tenant_id: str, invoice_number: str, total: float
) -> str | None:
    """Create a Stripe Payment Link for the invoice total. Returns the URL or None on failure."""
    try:
        ensure_stripe_configured()
    except RuntimeError:
        logger.warning(
            "Stripe not configured — cannot create payment link for invoice %s",
            invoice_id,
        )
        return None

    metadata = {"invoice_id": invoice_id, "tenant_id": tenant_id}
    try:
        price = stripe.Price.create(
            unit_amount=int(round(total * 100)),
            currency="usd",
            product_data={"name": f"Invoice {invoice_number}"},
        )
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata=metadata,
            payment_intent_data={"metadata": metadata},
            restrictions={"completed_sessions": {"limit": 1}},
            inactive_message="This invoice has already been paid. Contact the business if you need help.",
        )
        return payment_link.url
    except stripe.StripeError as e:
        logger.warning(
            "Stripe error creating payment link for invoice %s: %s",
            invoice_id,
            str(e),
        )
        return None
    except Exception:
        logger.exception(
            "Unexpected error creating Stripe payment link for invoice %s",
            invoice_id,
        )
        return None
