"""Instant owner alerts when an appointment is booked via the public page.

Mirror of ``lead_alerts.py`` for the higher-value booking event. When a
customer books through ``/api/v1/book/{slug}``, the owner gets notified
immediately via both configured channels:

  - Email (Resend) when ``tenants.owner_email`` is set.
  - SMS (Twilio) when ``tenants.notification_phone`` is set AND
    ``tenants.sms_notifications_enabled`` is true.

Why this exists: ``booking_submit`` already emails the CUSTOMER a confirmation
and fires an ``appointment.booked`` webhook, but the business OWNER got nothing
unless they had a webhook wired — so a booking was *less* notified than a mere
lead capture (which does fire ``send_new_lead_alert``). A service business must
know an appointment landed so they can staff/prepare. Found 2026-07-15 while
verifying the booking path after the widget-booking-link fix.

Design contract (identical to lead_alerts): best-effort, non-blocking,
idempotent per (tenant, appointment), demo-safe (the send_sms/send_email
wrappers no-op for demo tenants), and this module's entry point NEVER raises.

Multi-tenant note: appointments use ``tenant_id``; the owner config we read
lives on ``tenants`` keyed by ``id``.

WARNING: imported by a FastAPI router — do NOT add
``from __future__ import annotations`` here.
"""

import html as html_mod
import logging

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Per-worker idempotency guard, keyed by (tenant_id, appointment_id).
_alerted: set = set()
_MAX_TRACKED = 10_000


def _already_alerted(tenant_id: str, appointment_id: str) -> bool:
    """Return True if this (tenant, appointment) was already alerted this process."""
    if not tenant_id or not appointment_id:
        return False
    key = (tenant_id, appointment_id)
    if key in _alerted:
        return True
    if len(_alerted) >= _MAX_TRACKED:
        _alerted.clear()
    _alerted.add(key)
    return False


def reset_idempotency_cache() -> None:
    """Test helper — drop all tracked (tenant, appointment) pairs."""
    _alerted.clear()


def _fetch_tenant_alert_config(tenant_id: str) -> dict:
    """Read owner notification config off the tenants table.

    Returns {} on any failure so callers degrade to "no channels" not a raise.
    """
    try:
        result = (
            get_service_supabase()
            .table("tenants")
            .select(
                "business_name, owner_email, notification_phone, "
                "sms_notifications_enabled"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "booking_alert: tenant config lookup failed for %s", tenant_id, exc_info=True
        )
        return {}
    rows = result.data or []
    return rows[0] if rows else {}


def _when(booking_info: dict) -> str:
    """Human-readable slot string from date + start/end time."""
    date = booking_info.get("date") or "?"
    start = booking_info.get("start_time") or "?"
    end = booking_info.get("end_time")
    return f"{date} {start}–{end}" if end else f"{date} {start}"


def _build_email_html(business_name: str, customer_name: str, booking_info: dict) -> str:
    """Owner-alert email body. All interpolated values escaped."""
    safe_business = html_mod.escape(business_name)
    safe_name = html_mod.escape(customer_name)
    safe_email = html_mod.escape(booking_info.get("email") or "not provided")
    safe_phone = html_mod.escape(booking_info.get("phone") or "not provided")
    safe_when = html_mod.escape(_when(booking_info))
    return (
        f"<h2>New appointment for {safe_business}</h2>"
        f"<p>A customer just booked an appointment through your booking page:</p>"
        f"<table style='border-collapse:collapse;margin:16px 0;'>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>When</td>"
        f"<td style='padding:4px 0;'>{safe_when}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Customer</td>"
        f"<td style='padding:4px 0;'>{safe_name}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Email</td>"
        f"<td style='padding:4px 0;'>{safe_email}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Phone</td>"
        f"<td style='padding:4px 0;'>{safe_phone}</td></tr>"
        f"</table>"
        f"<p>Log in to your dashboard to view the appointment.</p>"
        f"<p>The AgentNexLiFy Team</p>"
    )


def _build_sms_body(business_name: str, customer_name: str, booking_info: dict) -> str:
    """Owner-alert SMS body (plain text)."""
    return f"New appointment for {business_name}: {customer_name} on {_when(booking_info)}"


async def _send_email_alert(
    tenant_id: str, business_name: str, owner_email: str, customer_name: str, booking_info: dict
) -> None:
    from backend.services.email_sender import send_email

    try:
        await send_email(
            to=owner_email,
            subject=f"New appointment for {business_name}: {customer_name}",
            body_html=_build_email_html(business_name, customer_name, booking_info),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "booking_alert: email send FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )


async def _send_sms_alert(
    tenant_id: str, business_name: str, phone: str, customer_name: str, booking_info: dict
) -> None:
    from backend.services.twilio_service import send_sms

    try:
        await send_sms(
            to=phone,
            body=_build_sms_body(business_name, customer_name, booking_info),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "booking_alert: SMS send FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )


async def send_new_booking_alert(
    tenant_id: str,
    customer_name: str,
    booking_info: dict,
    appointment_id: str = "",
) -> None:
    """Fire instant owner alerts (email + SMS) for a newly booked appointment.

    Best-effort, non-blocking, idempotent, demo-safe. NEVER raises — callers
    await this inside the booking-submit response cycle.

    Args:
        tenant_id: tenant the appointment belongs to (tenants.id).
        customer_name: booking customer's display name.
        booking_info: dict with optional email/phone + date/start_time/end_time.
        appointment_id: the appointment id, used for idempotency. Empty → the
            alert still fires but is not deduped.
    """
    try:
        # Namespaced key so a booking alert and a later cancellation alert for
        # the SAME appointment don't dedup each other out.
        if _already_alerted(tenant_id, f"{appointment_id}:booked"):
            logger.info(
                "booking_alert: already alerted tenant=%s appt=%s, skipping",
                tenant_id, appointment_id,
            )
            return

        config = _fetch_tenant_alert_config(tenant_id)
        if not config:
            logger.warning("booking_alert: no tenant config for %s, skipping", tenant_id)
            return

        business_name = config.get("business_name") or "your business"
        owner_email = config.get("owner_email")
        phone = config.get("notification_phone")
        sms_enabled = config.get("sms_notifications_enabled")

        if owner_email:
            await _send_email_alert(
                tenant_id, business_name, owner_email, customer_name, booking_info
            )
        else:
            logger.info("booking_alert: no owner_email for tenant=%s, email skipped", tenant_id)

        if sms_enabled and phone:
            await _send_sms_alert(
                tenant_id, business_name, phone, customer_name, booking_info
            )
        else:
            logger.info(
                "booking_alert: SMS skipped tenant=%s (sms_enabled=%s phone_set=%s)",
                tenant_id, bool(sms_enabled), bool(phone),
            )
    except Exception:
        logger.error(
            "booking_alert: send_new_booking_alert FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )


# ---------------------------------------------------------------------------
# Cancellation alerts — a cancelled appointment reopens a slot the owner should
# know about. reschedule_cancel previously only fired a webhook + logged, so
# the owner learned nothing unless they'd wired a webhook (parallel gap to the
# original booking-alert gap). (2026-07-15)
# ---------------------------------------------------------------------------


def _build_cancel_email_html(business_name: str, customer_name: str, booking_info: dict) -> str:
    safe_business = html_mod.escape(business_name)
    safe_name = html_mod.escape(customer_name)
    safe_when = html_mod.escape(_when(booking_info))
    return (
        f"<h2>Appointment cancelled — {safe_business}</h2>"
        f"<p><strong>{safe_name}</strong> cancelled their appointment"
        f"{f' ({safe_when})' if booking_info.get('date') else ''}.</p>"
        f"<p>That time slot is open again — you may want to follow up or offer it to someone else.</p>"
        f"<p>The AgentNexLiFy Team</p>"
    )


def _build_cancel_sms_body(business_name: str, customer_name: str, booking_info: dict) -> str:
    when = _when(booking_info)
    tail = f" ({when})" if booking_info.get("date") else ""
    return f"Cancelled — {business_name}: {customer_name} cancelled their appointment{tail}. The slot is open again."


async def _send_cancel_email_alert(
    tenant_id: str, business_name: str, owner_email: str, customer_name: str, booking_info: dict
) -> None:
    from backend.services.email_sender import send_email

    try:
        await send_email(
            to=owner_email,
            subject=f"Appointment cancelled — {business_name}: {customer_name}",
            body_html=_build_cancel_email_html(business_name, customer_name, booking_info),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "booking_alert: cancel email send FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )


async def _send_cancel_sms_alert(
    tenant_id: str, business_name: str, phone: str, customer_name: str, booking_info: dict
) -> None:
    from backend.services.twilio_service import send_sms

    try:
        await send_sms(
            to=phone,
            body=_build_cancel_sms_body(business_name, customer_name, booking_info),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "booking_alert: cancel SMS send FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )


async def send_cancellation_alert(
    tenant_id: str,
    customer_name: str,
    booking_info: dict,
    appointment_id: str = "",
) -> None:
    """Fire owner alerts (email + SMS) when an appointment is cancelled.

    Same contract as send_new_booking_alert: best-effort, demo-safe, idempotent
    per (tenant, appointment) with a cancellation-specific dedup namespace, and
    NEVER raises. ``booking_info`` may be sparse (id/name only) — the slot
    fields are optional.
    """
    try:
        if _already_alerted(tenant_id, f"{appointment_id}:cancelled"):
            logger.info(
                "booking_alert: cancel already alerted tenant=%s appt=%s, skipping",
                tenant_id, appointment_id,
            )
            return

        config = _fetch_tenant_alert_config(tenant_id)
        if not config:
            logger.warning("booking_alert: no tenant config for %s, skipping cancel", tenant_id)
            return

        business_name = config.get("business_name") or "your business"
        owner_email = config.get("owner_email")
        phone = config.get("notification_phone")
        sms_enabled = config.get("sms_notifications_enabled")

        if owner_email:
            await _send_cancel_email_alert(
                tenant_id, business_name, owner_email, customer_name, booking_info
            )
        if sms_enabled and phone:
            await _send_cancel_sms_alert(
                tenant_id, business_name, phone, customer_name, booking_info
            )
    except Exception:
        logger.error(
            "booking_alert: send_cancellation_alert FAILED tenant=%s customer=%s",
            tenant_id, customer_name, exc_info=True,
        )
