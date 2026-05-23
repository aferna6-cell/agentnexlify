"""Single-invoice send — dispatch one invoice to the customer's contact channels.

Extracted from ``backend/routers/invoices.py`` to keep the router thin and to
make the send pipeline independently testable. Bulk send lives next door in
``backend/services/invoice_bulk_send.py`` and uses the same dispatch primitive.

Semantics differ slightly from bulk send: this path raises 404/400 for missing
or non-sendable invoices, whereas bulk send aggregates those into the failed
bucket. Missing lead contact info does NOT fail the single send (dispatch
returns an error string in the response), matching the original handler.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.services.invoice_dispatch import dispatch_invoice_channels
from backend.services.invoice_payment_links import get_or_create_stripe_payment_link
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _fetch_invoice(db, tenant_id: str, invoice_id: str) -> dict:
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("*")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch invoice %s for sending", invoice_id)
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")

    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return result.data[0]


def _fetch_business(db, tenant_id: str) -> dict:
    try:
        result = (
            tenant_table(db, "tenants", tenant_id)
            .select("business_name, owner_email, phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception:
        logger.warning(
            "Could not fetch tenant info for invoice send, tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {}


def _fetch_lead(db, tenant_id: str, lead_id: str | None) -> dict:
    if not lead_id:
        return {}
    try:
        result = (
            tenant_table(db, "leads", tenant_id)
            .select("id, name, email, phone")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception:
        logger.warning(
            "Could not fetch lead %s for invoice send", lead_id, exc_info=True
        )
        return {}


async def _resolve_payment_link(
    invoice: dict, tenant_id: str, invoice_id: str
) -> str:
    existing = invoice.get("stripe_payment_link") or ""
    total = float(invoice.get("total", 0) or 0)
    if existing or total <= 0:
        return existing
    link = await get_or_create_stripe_payment_link(
        invoice_id=invoice_id,
        tenant_id=tenant_id,
        invoice_number=invoice.get("invoice_number", invoice_id),
        total=total,
    )
    return link or ""


def _update_invoice_after_send(
    db,
    tenant_id: str,
    invoice_id: str,
    method: str,
    payment_link_url: str,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    update_data: dict = {
        "status": "sent",
        "sent_at": now_iso,
        "sent_via": method,
        "updated_at": now_iso,
    }
    if payment_link_url:
        update_data["stripe_payment_link"] = payment_link_url

    try:
        tenant_table(db, "invoices", tenant_id).update(update_data).eq(
            "id", invoice_id
        ).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception(
            "Failed to update invoice %s status after send", invoice_id
        )


async def send_invoice_for_tenant(
    db, tenant_id: str, invoice_id: str, method: str
) -> dict:
    """Send a single invoice. Raises HTTPException on non-sendable state.

    Returns the response payload the route handler hands back to the client.
    """
    invoice = _fetch_invoice(db, tenant_id, invoice_id)

    if invoice["status"] in ("paid", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send an invoice with status '{invoice['status']}'",
        )

    business = _fetch_business(db, tenant_id)
    lead = _fetch_lead(db, tenant_id, invoice.get("lead_id"))
    payment_link_url = await _resolve_payment_link(invoice, tenant_id, invoice_id)

    email_sent, sms_sent, errors = await dispatch_invoice_channels(
        invoice=invoice,
        business=business,
        lead=lead,
        method=method,
        payment_link_url=payment_link_url,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )

    _update_invoice_after_send(
        db, tenant_id, invoice_id, method, payment_link_url
    )

    return {
        "sent": True,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "payment_link": payment_link_url,
        "errors": errors,
    }
