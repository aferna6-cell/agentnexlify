"""Invoice delivery flows (issue #473 split): single send and bulk send via
email/SMS with Stripe Payment Links. Moved verbatim from routers/invoices.py;
raises HTTPException like the routes it backs (established services pattern —
see auth_service, faq_service).

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from backend.services.email_sender import send_email
from backend.services.invoice_email import (
    build_bulk_invoice_email_html,
    build_invoice_email_html,
)
from backend.services.invoice_helpers import get_or_create_stripe_payment_link
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


async def send_invoice_flow(db, tenant_id: str, invoice_id: str, method: str) -> dict:
    """Send one invoice via email, SMS, or both; returns the send report."""
    # Fetch invoice
    try:
        inv_result = (
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

    if not inv_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv_result.data[0]

    if invoice["status"] in ("paid", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send an invoice with status '{invoice['status']}'",
        )

    # Fetch tenant (business) info
    business: dict = {}
    try:
        tenant_result = (
            tenant_table(db, "tenants", tenant_id)
            .select("business_name, owner_email, phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            business = tenant_result.data[0]
    except Exception:
        logger.warning("Could not fetch tenant info for invoice send, tenant %s", tenant_id, exc_info=True)

    # Fetch lead contact details — leads table uses client_id
    lead: dict = {}
    lead_id = invoice.get("lead_id")
    if lead_id:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id)
                .select("id, name, email, phone")
                .eq("id", lead_id)
                .eq("client_id", tenant_id)
                .limit(1)
                .execute()
            )
            if lead_result.data:
                lead = lead_result.data[0]
        except Exception:
            logger.warning("Could not fetch lead %s for invoice send", lead_id, exc_info=True)

    # Create Stripe Payment Link if not already present
    payment_link_url = invoice.get("stripe_payment_link") or ""
    if not payment_link_url and invoice.get("total", 0) > 0:
        payment_link_url = await get_or_create_stripe_payment_link(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            invoice_number=invoice.get("invoice_number", invoice_id),
            total=float(invoice.get("total", 0)),
        ) or ""

    # Build enriched invoice dict for email rendering
    invoice_for_email = {**invoice, "stripe_payment_link": payment_link_url}

    # Send via requested channel(s)
    email_sent = False
    sms_sent = False
    errors: list[str] = []

    if method in ("email", "both"):
        recipient_email = lead.get("email") or ""
        if not recipient_email:
            errors.append("No email address on file for this lead")
        else:
            subject = f"Invoice {invoice.get('invoice_number', '')} from {business.get('business_name', 'Your Service Provider')}"
            body_html = build_invoice_email_html(invoice_for_email, business, lead)
            try:
                result = await send_email(
                    to=recipient_email,
                    subject=subject,
                    body_html=body_html,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    email_sent = True
                else:
                    errors.append(f"Email failed: {result.get('detail', 'unknown error')}")
            except Exception:
                logger.exception("Unexpected error sending invoice email for invoice %s", invoice_id)
                errors.append("Email delivery failed unexpectedly")

    if method in ("sms", "both"):
        recipient_phone = lead.get("phone") or ""
        if not recipient_phone:
            errors.append("No phone number on file for this lead")
        else:
            invoice_number = invoice.get("invoice_number", "")
            total = float(invoice.get("total", 0))
            biz_name = business.get("business_name") or "Your Service Provider"
            if payment_link_url:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {invoice_number} for ${total:,.2f} "
                    f"from {biz_name} is ready. Pay online: {payment_link_url}"
                )
            else:
                sms_body = (
                    f"Hi {lead.get('name', 'there')}! Invoice {invoice_number} for ${total:,.2f} "
                    f"from {biz_name} is ready. Please contact us to complete payment."
                )
            try:
                ok = await send_sms(to=recipient_phone, body=sms_body, tenant_id=tenant_id)
                if ok:
                    sms_sent = True
                else:
                    errors.append("SMS delivery failed")
            except Exception:
                logger.exception("Unexpected error sending invoice SMS for invoice %s", invoice_id)
                errors.append("SMS delivery failed unexpectedly")

    # Update invoice record: status, sent_at, sent_via, stripe_payment_link
    update_data: dict = {
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_via": method,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payment_link_url:
        update_data["stripe_payment_link"] = payment_link_url

    try:
        tenant_table(db, "invoices", tenant_id).update(update_data).eq("id", invoice_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to update invoice %s status after send", invoice_id)
        # Don't raise here — the send may have succeeded, we just failed to update status

    return {
        "sent": True,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "payment_link": payment_link_url,
        "errors": errors,
    }


async def bulk_send_flow(db, tenant_id: str, invoice_ids: list[str], channel: str) -> dict:
    """Send up to 50 invoices at once; returns {sent, failed, errors[:10]}."""
    sent = 0
    failed = 0
    errors = []

    # Fetch tenant info once
    business = {}
    try:
        t = tenant_table(db, "tenants", tenant_id).select("business_name").eq("id", tenant_id).limit(1).execute()
        business = t.data[0] if t.data else {}
    except Exception:
        logger.warning("Failed to fetch tenant business name for invoice send (tenant %s)", tenant_id, exc_info=True)
    biz_name = business.get("business_name") or "Your Service Provider"

    # Batch-fetch all requested invoices in one query (was one query per invoice)
    inv_result = (
        tenant_table(db, "invoices", tenant_id)
        .select("*")
        .in_("id", invoice_ids)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    invoices_by_id = {row["id"]: row for row in (inv_result.data or [])}

    # Batch-fetch all linked leads in one query (was one query per invoice)
    lead_ids = {inv.get("lead_id") for inv in invoices_by_id.values() if inv.get("lead_id")}
    leads_by_id = {}
    if lead_ids:
        try:
            lead_result = (
                tenant_table(db, "leads", tenant_id)
                .select("id, name, email, phone")
                .in_("id", list(lead_ids))
                .eq("client_id", tenant_id)
                .execute()
            )
            leads_by_id = {row["id"]: row for row in (lead_result.data or [])}
        except Exception:
            logger.warning("Bulk send: failed to fetch leads for tenant %s", tenant_id, exc_info=True)

    sent_invoice_ids = []
    for invoice_id in invoice_ids:
        try:
            invoice = invoices_by_id.get(invoice_id)
            if not invoice:
                failed += 1
                errors.append(f"{invoice_id}: not found")
                continue

            if invoice["status"] in ("paid", "cancelled"):
                failed += 1
                errors.append(f"{invoice.get('invoice_number', invoice_id)}: already {invoice['status']}")
                continue

            lead_id = invoice.get("lead_id")
            lead = leads_by_id.get(lead_id) if lead_id else None

            if not lead or (not lead.get("email") and not lead.get("phone")):
                failed += 1
                errors.append(f"{invoice.get('invoice_number', invoice_id)}: no contact info")
                continue

            total = float(invoice.get("total") or 0)
            payment_link = invoice.get("stripe_payment_link")
            if not payment_link and total > 0:
                try:
                    payment_link = await get_or_create_stripe_payment_link(
                        invoice_id, tenant_id, invoice.get("invoice_number", ""), total
                    )
                except Exception:
                    logger.warning("Could not create payment link for invoice %s", invoice_id, exc_info=True)

            inv_num = invoice.get("invoice_number", "")

            if channel in ("email", "both") and lead.get("email"):
                try:
                    subject = f"Invoice {inv_num} from {biz_name}"
                    html_body = build_bulk_invoice_email_html(inv_num, lead, biz_name, total, payment_link)
                    await send_email(to=lead["email"], subject=subject, body_html=html_body, tenant_id=tenant_id)
                except Exception:
                    logger.warning("Failed to email invoice %s", invoice_id, exc_info=True)

            if channel in ("sms", "both") and lead.get("phone"):
                try:
                    msg = f"Hi {lead.get('name', 'there')}! Invoice {inv_num} for ${total:,.2f} from {biz_name}."
                    if payment_link:
                        msg += f" Pay here: {payment_link}"
                    await send_sms(to=lead["phone"], body=msg, tenant_id=tenant_id)
                except Exception:
                    logger.warning("Failed to SMS invoice %s", invoice_id, exc_info=True)

            sent_invoice_ids.append(invoice_id)
            sent += 1

        except Exception:
            failed += 1
            errors.append(f"{invoice_id}: unexpected error")
            logger.exception("Bulk send failed for invoice %s", invoice_id)

    # Single status update for everything that went out (was one update per invoice)
    if sent_invoice_ids:
        try:
            tenant_table(db, "invoices", tenant_id).update({
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_via": channel,
            }).in_("id", sent_invoice_ids).execute()
        except Exception:
            logger.exception(
                "Bulk send: messages dispatched but failed to mark %d invoices sent for tenant %s",
                len(sent_invoice_ids), tenant_id,
            )

    return {"sent": sent, "failed": failed, "errors": errors[:10]}
