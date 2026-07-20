"""Invoice derivation helpers (issue #473 split): totals, numbering, Stripe
payment links, and stats aggregation. Moved verbatim from routers/invoices.py.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime

import stripe

from backend.services.stripe_service import ensure_stripe_configured
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def compute_invoice_totals(items: list[dict], tax_rate: float) -> tuple[float, float, float]:
    """Return (subtotal, tax_amount, total) from line items and a tax_rate percentage."""
    subtotal = round(sum(
        item.get("quantity", 1) * item.get("unit_price", 0)
        for item in items
    ), 2)
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total


async def get_next_invoice_number(db, tenant_id: str, attempt: int = 0) -> str:
    """Generate a sequential invoice number: INV-{tenant_id[:4].upper()}-{NNN}.

    The `attempt` param offsets the sequence to handle retry on uniqueness conflict.
    """
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("invoice_number")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last_num = result.data[0].get("invoice_number", "INV-XXXX-000")
            # Extract sequential portion after the last dash
            parts = last_num.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                seq = int(parts[1]) + 1 + attempt
            else:
                seq = 1 + attempt
        else:
            seq = 1 + attempt
    except Exception:
        logger.warning("Could not determine next invoice number for tenant %s", tenant_id, exc_info=True)
        seq = 1 + attempt
    prefix = tenant_id[:4].upper()
    return f"INV-{prefix}-{seq:03d}"


async def get_or_create_stripe_payment_link(invoice_id: str, tenant_id: str, invoice_number: str, total: float) -> str | None:
    """Create a Stripe Payment Link for the invoice total. Returns the URL or None on failure."""
    try:
        ensure_stripe_configured()
    except RuntimeError:
        logger.warning("Stripe not configured — cannot create payment link for invoice %s", invoice_id)
        return None

    metadata = {"invoice_id": invoice_id, "tenant_id": tenant_id}
    try:
        price = stripe.Price.create(
            unit_amount=int(round(total * 100)),  # cents
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
        logger.warning("Stripe error creating payment link for invoice %s: %s", invoice_id, str(e))
        return None
    except Exception:
        logger.exception("Unexpected error creating Stripe payment link for invoice %s", invoice_id)
        return None


def compute_invoice_stats(invoices: list[dict]) -> dict:
    """Aggregate invoice rows into the /stats response payload."""
    total_outstanding = round(
        sum(float(i.get("total", 0)) for i in invoices if i.get("status") in ("sent", "viewed")),
        2,
    )
    total_paid = round(
        sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "paid"),
        2,
    )
    overdue_count = sum(1 for i in invoices if i.get("status") == "overdue")
    paid_count = sum(1 for i in invoices if i.get("status") == "paid")

    # Average days from sent_at to paid_at for paid invoices
    avg_days_to_payment: float | None = None
    days_list = []
    for inv in invoices:
        if inv.get("status") == "paid" and inv.get("sent_at") and inv.get("paid_at"):
            try:
                sent = datetime.fromisoformat(inv["sent_at"].replace("Z", "+00:00"))
                paid = datetime.fromisoformat(inv["paid_at"].replace("Z", "+00:00"))
                delta_days = (paid - sent).total_seconds() / 86400
                if delta_days >= 0:
                    days_list.append(delta_days)
            except Exception:
                logger.warning("Could not parse dates for invoice stats", exc_info=True)
    if days_list:
        avg_days_to_payment = round(sum(days_list) / len(days_list), 1)

    return {
        "total_outstanding": total_outstanding,
        "total_paid": total_paid,
        "overdue_count": overdue_count,
        "paid_count": paid_count,
        "total_invoices": len(invoices),
        "avg_days_to_payment": avg_days_to_payment,
    }
