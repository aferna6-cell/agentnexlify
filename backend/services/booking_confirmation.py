"""Customer-facing appointment confirmation messaging (email + SMS)."""


import html as html_mod
import logging
from datetime import datetime

from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _reschedule_link_html(appointment: dict) -> str:
    """Generate a reschedule link HTML fragment for the confirmation email."""
    from backend.services import booking as _b

    try:
        url = _b.build_reschedule_url(appointment["id"])
        return f'<a href="{url}" style="color: #2563eb; text-decoration: underline;">click here to reschedule</a>'
    except Exception:
        return "please contact us"


async def _send_appointment_confirmation(tenant_id: str, appointment: dict) -> None:
    """Send booking confirmation via email and/or SMS to the customer."""
    from backend.services import booking as _b
    from backend.services.email_sender import send_email
    from backend.services.twilio_service import send_sms

    db = _b.get_service_supabase() if hasattr(_b, "get_service_supabase") else get_service_supabase()
    tenant = (
        tenant_table(db, "tenants", tenant_id)
        .select("business_name, business_phone")
        .limit(1)
        .execute()
    )
    business_name = tenant.data[0]["business_name"] if tenant.data else "Our business"
    business_phone = (tenant.data[0].get("business_phone") or "") if tenant.data else ""

    customer_name = appointment.get("customer_name", "Customer")
    customer_email = appointment.get("customer_email")
    customer_phone = appointment.get("customer_phone")
    start_time = appointment.get("start_time", "")

    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        display_date = dt.strftime("%A, %B %d, %Y")
        display_time = dt.strftime("%I:%M %p")
    except Exception:
        display_date = start_time
        display_time = ""

    if customer_email:
        try:
            safe_name = html_mod.escape(customer_name)
            safe_biz = html_mod.escape(business_name)
            safe_phone = html_mod.escape(business_phone)
            safe_notes = html_mod.escape(appointment.get("notes", ""))
            html_body = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Appointment Confirmed!</h2>
                <p>Hi {safe_name},</p>
                <p>Your appointment has been booked with <strong>{safe_biz}</strong>.</p>
                <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0;"><strong>Date:</strong> {display_date}</p>
                    <p style="margin: 4px 0;"><strong>Time:</strong> {display_time}</p>
                    {f'<p style="margin: 4px 0;"><strong>Notes:</strong> {safe_notes}</p>' if appointment.get("notes") else ""}
                </div>
                <p>If you need to reschedule or cancel, {_b._reschedule_link_html(appointment)}{f" or contact us at {safe_phone}" if business_phone else " please use the link above or contact us"}.</p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">— {safe_biz}</p>
            </div>
            """
            await send_email(
                to=customer_email,
                subject=f"Appointment Confirmed - {business_name}",
                body_html=html_body,
                tenant_id=tenant_id,
            )
            logger.info(
                "Sent appointment confirmation email to %s for tenant %s",
                customer_email,
                tenant_id,
            )
        except Exception:
            logger.warning(
                "Failed to send appointment confirmation email to %s",
                customer_email,
                exc_info=True,
            )

    if customer_phone:
        try:
            sms_body = (
                f"Hi {customer_name}! Your appointment with {business_name} is confirmed for "
                f"{display_date} at {display_time}."
                f"{' Contact us to reschedule: ' + business_phone if business_phone else ''}"
            )
            await send_sms(to=customer_phone, body=sms_body)
            logger.info(
                "Sent appointment confirmation SMS to %s for tenant %s",
                customer_phone,
                tenant_id,
            )
        except Exception:
            logger.warning(
                "Failed to send appointment confirmation SMS to %s",
                customer_phone,
                exc_info=True,
            )
