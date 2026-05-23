"""Bulk invoice send — fan out send across up to 50 invoices in one request.

Pulled out of ``backend/routers/invoices.py``. Preserves the original semantics:
an invoice that fails contact lookup or status check is reported as failed; any
invoice for which at least dispatch was attempted is marked ``sent`` regardless
of email/SMS delivery outcome (matches prior bulk behaviour).
"""

import logging
from datetime import datetime, timezone

from backend.services.invoice_dispatch import dispatch_invoice_channels
from backend.services.invoice_payment_links import get_or_create_stripe_payment_link
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

MAX_BULK_SEND = 50
MAX_ERRORS_RETURNED = 10


def _fetch_business(db, tenant_id: str) -> dict:
    try:
        t = (
            tenant_table(db, "tenants", tenant_id)
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        return t.data[0] if t.data else {}
    except Exception:
        logger.warning(
            "Failed to fetch tenant business name for bulk invoice send (tenant %s)",
            tenant_id,
            exc_info=True,
        )
        return {}


def _fetch_invoice(db, tenant_id: str, invoice_id: str) -> dict | None:
    inv = (
        tenant_table(db, "invoices", tenant_id)
        .select("*")
        .eq("id", invoice_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    return inv.data[0] if inv.data else None


def _fetch_lead(db, tenant_id: str, lead_id: str | None) -> dict | None:
    if not lead_id:
        return None
    lead_row = (
        tenant_table(db, "leads", tenant_id)
        .select("name, email, phone")
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    return lead_row.data[0] if lead_row.data else None


async def _resolve_payment_link(invoice: dict, tenant_id: str, invoice_id: str) -> str:
    payment_link = invoice.get("stripe_payment_link") or ""
    total = float(invoice.get("total") or 0)
    if payment_link or total <= 0:
        return payment_link
    try:
        link = await get_or_create_stripe_payment_link(
            invoice_id, tenant_id, invoice.get("invoice_number", ""), total
        )
        return link or ""
    except Exception:
        logger.warning(
            "Could not create payment link for invoice %s",
            invoice_id,
            exc_info=True,
        )
        return ""


def _mark_invoice_sent(db, tenant_id: str, invoice_id: str, channel: str) -> None:
    tenant_table(db, "invoices", tenant_id).update(
        {
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sent_via": channel,
        }
    ).eq("id", invoice_id).execute()


async def bulk_send_invoices_for_tenant(
    db, tenant_id: str, invoice_ids: list[str], channel: str
) -> dict:
    """Send a batch of invoices for a tenant. Returns aggregate counts + errors."""
    sent = 0
    failed = 0
    errors: list[str] = []

    business = _fetch_business(db, tenant_id)

    for invoice_id in invoice_ids:
        try:
            invoice = _fetch_invoice(db, tenant_id, invoice_id)
            if not invoice:
                failed += 1
                errors.append(f"{invoice_id}: not found")
                continue

            if invoice["status"] in ("paid", "cancelled"):
                failed += 1
                label = invoice.get("invoice_number") or invoice_id
                errors.append(f"{label}: already {invoice['status']}")
                continue

            lead = _fetch_lead(db, tenant_id, invoice.get("lead_id"))
            if not lead or (not lead.get("email") and not lead.get("phone")):
                failed += 1
                label = invoice.get("invoice_number") or invoice_id
                errors.append(f"{label}: no contact info")
                continue

            payment_link_url = await _resolve_payment_link(
                invoice, tenant_id, invoice_id
            )

            await dispatch_invoice_channels(
                invoice=invoice,
                business=business,
                lead=lead,
                method=channel,
                payment_link_url=payment_link_url,
                tenant_id=tenant_id,
                invoice_id=invoice_id,
            )

            try:
                _mark_invoice_sent(db, tenant_id, invoice_id, channel)
            except Exception:
                logger.warning(
                    "Failed to update sent status for invoice %s",
                    invoice_id,
                    exc_info=True,
                )

            sent += 1
        except Exception:
            failed += 1
            errors.append(f"{invoice_id}: unexpected error")
            logger.exception("Bulk send failed for invoice %s", invoice_id)

    return {"sent": sent, "failed": failed, "errors": errors[:MAX_ERRORS_RETURNED]}
