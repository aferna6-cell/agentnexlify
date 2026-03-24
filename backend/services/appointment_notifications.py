"""Appointment confirmation and reminder notifications.

Sends email + SMS confirmations when appointments are booked.
Called as a background task from the booking endpoint.
"""

import html as html_mod
import logging
from datetime import datetime, timezone

from backend.models.database import get_supabase
from backend.services.email_sender import send_email
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


def _format_appointment_time(start_time_str: str, tz_name: str = "America/New_York") -> str:
    """Format ISO timestamp into human-readable date/time string."""
    try:
        # Parse ISO format
        dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        # Try to convert to business timezone
        try:
            from zoneinfo import ZoneInfo
            dt_local = dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            dt_local = dt
        return dt_local.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        return start_time_str


async def send_appointment_confirmation(
    tenant_id: str,
    appointment: dict,
) -> None:
    """Send confirmation email and SMS after an appointment is booked.

    This runs as a background task (asyncio.create_task) so it does not
    block the booking response. All errors are caught and logged.
    """
    db = get_supabase()

    # Fetch tenant info for business name and contact details
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, owner_email, business_phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            logger.warning("appt_confirm: tenant %s not found", tenant_id)
            return
        tenant = tenant_result.data[0]
    except Exception:
        logger.exception("appt_confirm: failed to fetch tenant %s", tenant_id)
        return

    business_name = tenant.get("business_name") or "Our Business"
    business_phone = tenant.get("business_phone") or ""
    customer_name = appointment.get("customer_name") or "Customer"
    customer_email = appointment.get("customer_email") or ""
    customer_phone = appointment.get("customer_phone") or ""
    start_time = appointment.get("start_time", "")
    end_time = appointment.get("end_time", "")

    # Get business timezone from business_hours config
    tz_name = "America/New_York"
    try:
        bh_result = (
            db.table("business_hours")
            .select("timezone")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if bh_result.data:
            tz_name = bh_result.data[0].get("timezone") or tz_name
    except Exception:
        pass

    formatted_time = _format_appointment_time(start_time, tz_name)

    # --- Send confirmation email ---
    if customer_email:
        safe_biz = html_mod.escape(business_name)
        safe_name = html_mod.escape(customer_name)
        safe_time = html_mod.escape(formatted_time)

        body_html = (
            f"<h2>Appointment Confirmed</h2>"
            f"<p>Hi {safe_name},</p>"
            f"<p>Your appointment with <strong>{safe_biz}</strong> has been confirmed:</p>"
            f"<div style='background:#f8f9fa;padding:16px;border-radius:8px;margin:16px 0;'>"
            f"<p style='margin:0 0 8px;font-size:16px;'><strong>{safe_time}</strong></p>"
        )
        if business_phone:
            safe_phone = html_mod.escape(business_phone)
            body_html += f"<p style='margin:0;color:#666;'>Contact: {safe_phone}</p>"
        body_html += (
            f"</div>"
            f"<p>If you need to reschedule or cancel, please contact us as soon as possible.</p>"
            f"<p style='margin-top:16px;color:#666;font-size:0.9em;'>"
            f"&mdash; {safe_biz}</p>"
        )

        try:
            result = await send_email(
                to=customer_email,
                subject=f"Appointment Confirmed - {business_name}",
                body_html=body_html,
                tenant_id=tenant_id,
            )
            if result.get("success"):
                logger.info(
                    "appt_confirm: email sent to %s for tenant %s",
                    customer_email, tenant_id,
                )
            else:
                logger.warning(
                    "appt_confirm: email failed for %s: %s",
                    customer_email, result.get("detail"),
                )
        except Exception:
            logger.exception(
                "appt_confirm: email exception for %s tenant %s",
                customer_email, tenant_id,
            )

    # --- Send confirmation SMS ---
    if customer_phone:
        sms_body = (
            f"Your appointment with {business_name} is confirmed!\n"
            f"When: {formatted_time}\n"
        )
        if business_phone:
            sms_body += f"Questions? Call {business_phone}"

        try:
            success = await send_sms(to=customer_phone, body=sms_body)
            if success:
                logger.info(
                    "appt_confirm: SMS sent to %s for tenant %s",
                    customer_phone, tenant_id,
                )
            else:
                logger.warning(
                    "appt_confirm: SMS failed for %s tenant %s",
                    customer_phone, tenant_id,
                )
        except Exception:
            logger.exception(
                "appt_confirm: SMS exception for %s tenant %s",
                customer_phone, tenant_id,
            )

    # --- Notify business owner via email ---
    owner_email = tenant.get("owner_email")
    if owner_email:
        safe_biz = html_mod.escape(business_name)
        safe_name = html_mod.escape(customer_name)
        safe_time = html_mod.escape(formatted_time)
        safe_cust_email = html_mod.escape(customer_email) if customer_email else "Not provided"
        safe_cust_phone = html_mod.escape(customer_phone) if customer_phone else "Not provided"

        owner_body = (
            f"<h2>New Appointment Booked</h2>"
            f"<p>A new appointment has been booked for {safe_biz}:</p>"
            f"<div style='background:#f8f9fa;padding:16px;border-radius:8px;margin:16px 0;'>"
            f"<p style='margin:0 0 8px;'><strong>Customer:</strong> {safe_name}</p>"
            f"<p style='margin:0 0 8px;'><strong>When:</strong> {safe_time}</p>"
            f"<p style='margin:0 0 8px;'><strong>Email:</strong> {safe_cust_email}</p>"
            f"<p style='margin:0;'><strong>Phone:</strong> {safe_cust_phone}</p>"
            f"</div>"
            f"<p>Log in to your dashboard to manage this appointment.</p>"
        )

        try:
            await send_email(
                to=owner_email,
                subject=f"New Appointment: {customer_name} - {formatted_time}",
                body_html=owner_body,
                tenant_id=tenant_id,
            )
            logger.info(
                "appt_confirm: owner notification sent for tenant %s",
                tenant_id,
            )
        except Exception:
            logger.exception(
                "appt_confirm: owner email failed for tenant %s", tenant_id,
            )
