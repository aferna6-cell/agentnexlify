"""Invoice channel dispatch — sends an invoice via email and/or SMS."""

import logging

from backend.services.email_sender import send_email
from backend.services.invoice_email_template import build_invoice_email_html
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


def build_invoice_sms_body(
    invoice: dict, business: dict, lead: dict, payment_link_url: str
) -> str:
    invoice_number = invoice.get("invoice_number", "")
    total = float(invoice.get("total", 0))
    biz_name = business.get("business_name") or "Your Service Provider"
    name = lead.get("name", "there")
    if payment_link_url:
        return (
            f"Hi {name}! Invoice {invoice_number} for ${total:,.2f} "
            f"from {biz_name} is ready. Pay online: {payment_link_url}"
        )
    return (
        f"Hi {name}! Invoice {invoice_number} for ${total:,.2f} "
        f"from {biz_name} is ready. Please contact us to complete payment."
    )


async def dispatch_invoice_channels(
    invoice: dict,
    business: dict,
    lead: dict,
    method: str,
    payment_link_url: str,
    tenant_id: str,
    invoice_id: str,
) -> tuple[bool, bool, list[str]]:
    """Dispatch invoice via email and/or SMS. Returns (email_sent, sms_sent, errors)."""
    email_sent = False
    sms_sent = False
    errors: list[str] = []

    invoice_for_email = {**invoice, "stripe_payment_link": payment_link_url}

    if method in ("email", "both"):
        recipient_email = lead.get("email") or ""
        if not recipient_email:
            errors.append("No email address on file for this lead")
        else:
            biz_name = business.get("business_name", "Your Service Provider")
            subject = (
                f"Invoice {invoice.get('invoice_number', '')} from {biz_name}"
            )
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
                    errors.append(
                        f"Email failed: {result.get('detail', 'unknown error')}"
                    )
            except Exception:
                logger.exception(
                    "Unexpected error sending invoice email for invoice %s",
                    invoice_id,
                )
                errors.append("Email delivery failed unexpectedly")

    if method in ("sms", "both"):
        recipient_phone = lead.get("phone") or ""
        if not recipient_phone:
            errors.append("No phone number on file for this lead")
        else:
            sms_body = build_invoice_sms_body(
                invoice, business, lead, payment_link_url
            )
            try:
                ok = await send_sms(to=recipient_phone, body=sms_body)
                if ok:
                    sms_sent = True
                else:
                    errors.append("SMS delivery failed")
            except Exception:
                logger.exception(
                    "Unexpected error sending invoice SMS for invoice %s",
                    invoice_id,
                )
                errors.append("SMS delivery failed unexpectedly")

    return email_sent, sms_sent, errors
