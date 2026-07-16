"""Customer-facing notices when staff change an appointment from the dashboard.

When a business owner reschedules or cancels an appointment through the
dashboard calendar (``PATCH``/``DELETE /api/v1/appointments/...`` →
``booking.update_appointment`` / ``booking.cancel_appointment``), the CUSTOMER
previously got nothing — they received a confirmation when they booked, then
heard silence when staff moved or cancelled the slot. Result: the customer
shows up at the old time, or to a cancelled appointment.

This is the higher-traffic mirror of ``booking_alerts.send_cancellation_alert``
(which notifies the OWNER when a customer self-cancels via the public link).
That one faces owner-ward; these face customer-ward.

Design contract (shared plumbing in ``notify_common``): non-blocking,
demo-safe (``send_sms``/``send_email`` no-op for demo tenants), gated on the
customer having an email/phone, and every entry point NEVER raises — callers
schedule these as background tasks inside the update response cycle.

Appointments use ``tenant_id`` (NOT ``client_id``). See schema-discipline.md.

WARNING: imported lazily by a service used from FastAPI routers — do NOT add
``from __future__ import annotations`` here.
"""

import html as html_mod
import logging

from backend.models.database import get_service_supabase
from backend.services.notify_common import safe_send_email, safe_send_sms
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_LOG = "appointment_customer_notify"


def _business_identity(tenant_id: str) -> tuple:
    """(business_name, business_phone) off the tenants row. Safe defaults on failure."""
    try:
        result = (
            tenant_table(get_service_supabase(), "tenants", tenant_id)
            .select("business_name, business_phone")
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "appointment_customer_notify: tenant lookup failed for %s",
            tenant_id,
            exc_info=True,
        )
        return "Our business", ""
    row = result.data[0] if result.data else {}
    return (row.get("business_name") or "Our business"), (row.get("business_phone") or "")


def _display_when(start_time: str) -> tuple:
    """(date_str, time_str) for a Supabase ISO start_time. Degrades gracefully."""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat((start_time or "").replace("Z", "+00:00"))
        return dt.strftime("%A, %B %d, %Y"), dt.strftime("%I:%M %p")
    except Exception:
        return (start_time or ""), ""


async def send_reschedule_notice(tenant_id: str, appointment: dict) -> None:
    """Tell the customer their appointment moved to a new time.

    Best-effort, demo-safe, NEVER raises. ``appointment`` is the UPDATED row
    (new start_time already applied).
    """
    try:
        customer_name = appointment.get("customer_name") or "there"
        customer_email = appointment.get("customer_email")
        customer_phone = appointment.get("customer_phone")
        if not customer_email and not customer_phone:
            return

        business_name, business_phone = _business_identity(tenant_id)
        display_date, display_time = _display_when(appointment.get("start_time") or "")

        if customer_email:
            safe_name = html_mod.escape(customer_name)
            safe_biz = html_mod.escape(business_name)
            safe_phone = html_mod.escape(business_phone)
            html_body = (
                f'<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">'
                f'<h2 style="color: #2563eb;">Your appointment has been rescheduled</h2>'
                f"<p>Hi {safe_name},</p>"
                f"<p>Your appointment with <strong>{safe_biz}</strong> has been moved "
                f"to a new time:</p>"
                f'<div style="background: #f3f4f6; border-radius: 8px; padding: 16px; margin: 16px 0;">'
                f'<p style="margin: 4px 0;"><strong>New date:</strong> {html_mod.escape(display_date)}</p>'
                f'<p style="margin: 4px 0;"><strong>New time:</strong> {html_mod.escape(display_time)}</p>'
                f"</div>"
                f"<p>If this new time doesn't work"
                f"{f', please contact us at {safe_phone}' if business_phone else ' please reach out to us'}.</p>"
                f'<p style="color: #6b7280; font-size: 12px; margin-top: 24px;">— {safe_biz}</p>'
                f"</div>"
            )
            await safe_send_email(
                tenant_id=tenant_id,
                to=customer_email,
                subject=f"Your appointment has been rescheduled - {business_name}",
                body_html=html_body,
                log_prefix=_LOG,
            )

        if customer_phone:
            sms_body = (
                f"Hi {customer_name}, your appointment with {business_name} has been "
                f"rescheduled to {display_date} at {display_time}."
                f"{f' Questions? Call {business_phone}.' if business_phone else ''}"
            )
            await safe_send_sms(
                tenant_id=tenant_id, to=customer_phone, body=sms_body, log_prefix=_LOG
            )
    except Exception:
        logger.warning(
            "appointment_customer_notify: send_reschedule_notice FAILED tenant=%s appt=%s",
            tenant_id,
            appointment.get("id"),
            exc_info=True,
        )


async def send_cancellation_notice(tenant_id: str, appointment: dict) -> None:
    """Tell the customer their appointment was cancelled.

    Best-effort, demo-safe, NEVER raises.
    """
    try:
        customer_name = appointment.get("customer_name") or "there"
        customer_email = appointment.get("customer_email")
        customer_phone = appointment.get("customer_phone")
        if not customer_email and not customer_phone:
            return

        business_name, business_phone = _business_identity(tenant_id)
        display_date, display_time = _display_when(appointment.get("start_time") or "")
        when = f" ({display_date} at {display_time})" if display_time else ""

        if customer_email:
            safe_name = html_mod.escape(customer_name)
            safe_biz = html_mod.escape(business_name)
            safe_phone = html_mod.escape(business_phone)
            safe_when = html_mod.escape(when)
            html_body = (
                f'<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">'
                f'<h2 style="color: #dc2626;">Your appointment has been cancelled</h2>'
                f"<p>Hi {safe_name},</p>"
                f"<p>Your appointment with <strong>{safe_biz}</strong>{safe_when} "
                f"has been cancelled.</p>"
                f"<p>To book a new time"
                f"{f', please contact us at {safe_phone}' if business_phone else ' please reach out to us'}.</p>"
                f'<p style="color: #6b7280; font-size: 12px; margin-top: 24px;">— {safe_biz}</p>'
                f"</div>"
            )
            await safe_send_email(
                tenant_id=tenant_id,
                to=customer_email,
                subject=f"Your appointment has been cancelled - {business_name}",
                body_html=html_body,
                log_prefix=_LOG,
            )

        if customer_phone:
            sms_body = (
                f"Hi {customer_name}, your appointment with {business_name}{when} "
                f"has been cancelled."
                f"{f' To rebook, call {business_phone}.' if business_phone else ''}"
            )
            await safe_send_sms(
                tenant_id=tenant_id, to=customer_phone, body=sms_body, log_prefix=_LOG
            )
    except Exception:
        logger.warning(
            "appointment_customer_notify: send_cancellation_notice FAILED tenant=%s appt=%s",
            tenant_id,
            appointment.get("id"),
            exc_info=True,
        )
