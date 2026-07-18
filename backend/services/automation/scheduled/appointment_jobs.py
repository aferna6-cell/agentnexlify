"""Appointment scheduled jobs — reminders, rebook suggestions, aftercare."""

import html
import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email
from backend.services.internal_tenants import is_internal_tenant
from backend.services.automation.rule_engine import check_appointment_triggers
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.automation.templates import _REMINDER_EXTRAS, _REBOOK_INTERVALS, _AFTERCARE_TEMPLATES
from backend.services.automation.trigger import BATCH_LIMIT

logger = logging.getLogger(__name__)

# Grace after end_time before auto-completing (GH #454): appointments that
# run long should not be marked done mid-visit, and a no-show the owner is
# about to cancel gets a window before the "how was your visit?" chain arms.
AUTO_COMPLETE_GRACE_HOURS = 1


def _get_reminder_extras(business_type: str, notes: str) -> list[str]:
    """Return business-type-aware items to bring/prepare for an appointment."""
    extras = _REMINDER_EXTRAS.get(business_type, [])
    notes_lower = notes.lower()
    if business_type == "dental":
        if any(kw in notes_lower for kw in ["root canal", "surgery", "extraction"]):
            extras = extras + ["Arrange a ride home (sedation may be used)"]
        if "cleaning" in notes_lower or "checkup" in notes_lower:
            extras = extras + ["Floss before your visit"]
    return extras


async def send_appointment_reminders() -> int:
    """Check for upcoming appointments and send email/SMS reminders.

    Sends reminders at two windows:
    - 24 hours before (23h-25h window)
    - 1 hour before (30m-90m window)

    Uses a simple approach: query appointments in each window that haven't
    had a reminder sent yet (tracked via notes field with reminder tags).
    Returns count of reminders sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    reminder_windows = [
        {"label": "24h", "min_hours": 23, "max_hours": 25},
        {"label": "1h", "min_hours": 0.5, "max_hours": 1.5},
    ]

    for window in reminder_windows:
        window_start = now + timedelta(hours=window["min_hours"])
        window_end = now + timedelta(hours=window["max_hours"])

        reminder_col = f"reminder_{window['label']}_sent_at"

        try:
            appointments = (
                db.table("appointments")
                .select(
                    "id, tenant_id, customer_name, customer_email, customer_phone, "
                    "start_time, end_time, notes, status, reminder_24h_sent_at, reminder_1h_sent_at"
                )
                .gte("start_time", window_start.isoformat())
                .lte("start_time", window_end.isoformat())
                # Every appointment-creation path sets status "confirmed"
                # (booking_page, appointments router, booking service; prod has
                # only confirmed/completed, never "booked"). Filtering on
                # "booked" meant reminders were sent to ZERO appointments, ever
                # — customers never got a 24h/1h reminder → no-shows. Accept the
                # real value plus "booked" for any legacy/custom row. (2026-07-15)
                .in_("status", ["confirmed", "booked"])
                .execute()
            )
        except Exception:
            logger.exception(
                "send_appointment_reminders: failed to query appointments for %s window",
                window["label"],
            )
            continue

        for appt in appointments.data or []:
            if appt.get(reminder_col):
                continue
            reminder_tag = f"reminder_{window['label']}_sent"
            notes = appt.get("notes") or ""
            if reminder_tag in notes:
                continue

            tenant_id = appt["tenant_id"]

            try:
                tenant = (
                    db.table("tenants")
                    .select(
                        "business_name, owner_email, plan, business_type, "
                        "appointment_reminders_enabled"
                    )
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                if not tenant.data:
                    continue
                tenant_data = tenant.data[0]
                # Per-tenant opt-out (migration 167). Column defaults true, so
                # this changes nothing until a tenant disables reminders.
                if tenant_data.get("appointment_reminders_enabled") is False:
                    continue
                business_name = html.escape(
                    tenant_data.get("business_name") or "Our Team"
                )
            except Exception:
                logger.exception(
                    "send_appointment_reminders: failed to load tenant %s", tenant_id
                )
                continue

            try:
                start_dt = datetime.fromisoformat(
                    appt["start_time"].replace("Z", "+00:00")
                )
                time_str = start_dt.strftime("%B %d at %I:%M %p")
            except Exception:
                time_str = appt["start_time"]

            customer_name = html.escape(appt.get("customer_name") or "there")
            customer_email = appt.get("customer_email")
            business_type = (tenant_data.get("business_type") or "").lower()

            bring_items = _get_reminder_extras(business_type, appt.get("notes") or "")

            if customer_email:
                subject_map = {
                    "24h": f"Reminder: Your appointment with {business_name} tomorrow",
                    "1h": f"Your appointment with {business_name} is in 1 hour",
                }
                bring_html = ""
                if bring_items and window["label"] == "24h":
                    bring_html = (
                        "<p><strong>Please remember to bring:</strong></p><ul>"
                        + "".join(f"<li>{item}</li>" for item in bring_items)
                        + "</ul>"
                    )

                body_map = {
                    "24h": (
                        f"<h2>Hi {customer_name},</h2>"
                        f"<p>This is a friendly reminder that you have an appointment "
                        f"with <strong>{business_name}</strong> scheduled for <strong>{time_str}</strong>.</p>"
                        f"{bring_html}"
                        f"<p>If you need to reschedule or cancel, please reply to this email "
                        f"or contact us directly.</p>"
                        f"<p>We look forward to seeing you!</p>"
                        f"<p>Best,<br>The {business_name} Team</p>"
                    ),
                    "1h": (
                        f"<h2>Hi {customer_name},</h2>"
                        f"<p>Just a quick reminder &mdash; your appointment with "
                        f"<strong>{business_name}</strong> is coming up in about 1 hour "
                        f"(<strong>{time_str}</strong>).</p>"
                        f"<p>See you soon!</p>"
                        f"<p>Best,<br>The {business_name} Team</p>"
                    ),
                }

                try:
                    await send_email(
                        to=customer_email,
                        subject=subject_map[window["label"]],
                        body_html=body_map[window["label"]],
                        tenant_id=tenant_id,
                    )
                    sent += 1
                    logger.info(
                        "Sent %s reminder for appointment %s to %s",
                        window["label"],
                        appt["id"],
                        customer_email,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send %s reminder for appointment %s",
                        window["label"],
                        appt["id"],
                    )

            customer_phone = appt.get("customer_phone")
            if customer_phone:
                bring_sms = ""
                if bring_items and window["label"] == "24h":
                    bring_sms = " Please bring: " + ", ".join(bring_items[:3]) + "."

                sms_map = {
                    "24h": (
                        f"Hi {customer_name}, reminder: you have an appointment "
                        f"with {business_name} tomorrow ({time_str}).{bring_sms} "
                        f"Reply to reschedule."
                    ),
                    "1h": (
                        f"Hi {customer_name}, your appointment with "
                        f"{business_name} is in 1 hour ({time_str}). See you soon!"
                    ),
                }
                try:
                    if check_sms_rate_limit(
                        tenant_id, tenant_data.get("plan") or "free"
                    ):
                        await send_sms(to=customer_phone, body=sms_map[window["label"]])
                        increment_sms_count(tenant_id)
                        sent += 1
                except Exception:
                    logger.exception(
                        "Failed to send SMS %s reminder for appointment %s",
                        window["label"],
                        appt["id"],
                    )

            update_payload = {
                reminder_col: datetime.now(timezone.utc).isoformat(),
            }
            try:
                db.table("appointments").update(update_payload).eq(
                    "id", appt["id"]
                ).execute()
            except Exception:
                updated_notes = (
                    f"{notes}\n{reminder_tag}".strip() if notes else reminder_tag
                )
                try:
                    db.table("appointments").update({"notes": updated_notes}).eq(
                        "id", appt["id"]
                    ).execute()
                except Exception:
                    logger.exception(
                        "Failed to mark reminder sent for appointment %s", appt["id"]
                    )

    return sent


async def send_rebook_suggestions() -> int:
    """After appointment completion, suggest rebooking for relevant business types.

    Checks completed appointments from 24-48 hours ago. Sends one rebook
    suggestion per appointment. Deduped via activity_log.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    window_start = now - timedelta(hours=48)
    window_end = now - timedelta(hours=24)

    try:
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, lead_id, updated_at"
            )
            .eq("status", "completed")
            .gte("updated_at", window_start.isoformat())
            .lte("updated_at", window_end.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception(
            "send_rebook_suggestions: failed to query completed appointments"
        )
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, business_type, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        btype = (tenant.get("business_type") or "").lower()
        if btype not in _REBOOK_INTERVALS:
            continue

        days, suggestion = _REBOOK_INTERVALS[btype]

        try:
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", appt.get("lead_id"))
                .eq("activity_type", "rebook_suggestion_sent")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in automation trigger", exc_info=True)

        business_name = html.escape(tenant.get("business_name") or "Us")
        customer_name = html.escape(appt.get("customer_name") or "there")
        customer_email = appt.get("customer_email")

        if customer_email:
            subject = f"Time to schedule your {suggestion} with {business_name}"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>We hope your recent visit to <strong>{business_name}</strong> went well!</p>"
                f"<p>We recommend scheduling your next <strong>{suggestion}</strong> in about "
                f"<strong>{days} days</strong> to stay on track.</p>"
                f"<p>Reply to this email or contact us to book your next appointment.</p>"
                f"<p>Best,<br>The {business_name} Team</p>"
            )
            try:
                result = await send_email(
                    to=customer_email,
                    subject=subject,
                    body_html=body,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    sent += 1
            except Exception:
                logger.exception(
                    "Failed to send rebook suggestion for appointment %s", appt["id"]
                )

        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "lead_id": appt.get("lead_id"),
                    "activity_type": "rebook_suggestion_sent",
                    "description": f"Rebook suggestion sent: {suggestion} in {days} days",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log rebook suggestion for appointment %s",
                appt["id"],
                exc_info=True,
            )

    return sent


async def send_aftercare_instructions() -> int:
    """Send aftercare instructions 2-4 hours after appointment completion.

    Deduped via activity_log (aftercare_sent per appointment).
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    window_start = now - timedelta(hours=4)
    window_end = now - timedelta(hours=2)

    try:
        appts = (
            db.table("appointments")
            .select("id, tenant_id, customer_name, customer_email, notes, updated_at")
            .eq("status", "completed")
            .gte("updated_at", window_start.isoformat())
            .lte("updated_at", window_end.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_aftercare_instructions: failed to query")
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]
        appt_id = appt["id"]

        try:
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", f"aftercare_sent_{appt_id}")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in automation trigger", exc_info=True)

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, business_type, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant or (tenant.get("plan") or "free") == "free":
            continue

        btype = (tenant.get("business_type") or "").lower()
        templates = _AFTERCARE_TEMPLATES.get(btype)
        if not templates:
            continue

        if not appt.get("customer_email"):
            continue

        notes_lower = (appt.get("notes") or "").lower()
        message = templates.get("default", "")
        for keyword, template in templates.items():
            if keyword != "default" and keyword in notes_lower:
                message = template
                break

        if not message:
            continue

        business_name = html.escape(tenant.get("business_name") or "Us")
        customer_name = html.escape(appt.get("customer_name") or "there")

        subject = f"Post-visit care instructions from {business_name}"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>{html.escape(message)}</p>"
            f"<p>If you have any questions or concerns, don't hesitate to reach out.</p>"
            f"<p>Best,<br>The {business_name} Team</p>"
        )

        try:
            result = await send_email(
                to=appt["customer_email"],
                subject=subject,
                body_html=body,
                tenant_id=tenant_id,
            )
            if result.get("success"):
                sent += 1
        except Exception:
            logger.exception("Failed to send aftercare for appointment %s", appt_id)

        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "activity_type": f"aftercare_sent_{appt_id}",
                    "description": f"Aftercare instructions sent to {customer_name}",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log aftercare for appointment %s", appt_id, exc_info=True
            )

    return sent


async def auto_complete_past_appointments() -> int:
    """Flip confirmed appointments past end_time (+grace) to completed.

    GH #454: review requests, rebook prompts, and aftercare automations all
    gate on status == "completed", but the only path there was a manual
    dashboard action - so they never fired for public bookings. This job
    closes that loop on schedule. Idempotent by construction: the select
    filter only matches confirmed/booked rows, so completed rows can never
    be re-processed. Internal/demo tenants are skipped with the same
    denylist the digest metrics use.
    """
    db = get_service_supabase()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=AUTO_COMPLETE_GRACE_HOURS)

    try:
        result = (
            db.table("appointments")
            .select("id, tenant_id, end_time, status")
            .in_("status", ["confirmed", "booked"])
            .lt("end_time", cutoff.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("auto_complete_past_appointments: appointment query failed")
        return 0

    appts = result.data or []
    if not appts:
        return 0

    tenant_ids = sorted({a.get("tenant_id") for a in appts if a.get("tenant_id")})
    internal_ids: set[str] = set()
    try:
        tenants_result = (
            db.table("tenants")
            .select("id, business_name, is_demo")
            .in_("id", tenant_ids)
            .execute()
        )
        for tenant in tenants_result.data or []:
            if is_internal_tenant(tenant):
                internal_ids.add(tenant.get("id"))
    except Exception:
        # Fail closed on the guard: if we cannot tell who is internal,
        # complete nothing rather than arm demo-tenant automations.
        logger.exception("auto_complete_past_appointments: tenant lookup failed")
        return 0

    completed = 0
    for appt in appts:
        appt_id = appt.get("id")
        if appt.get("tenant_id") in internal_ids:
            continue
        try:
            (
                db.table("appointments")
                .update({"status": "completed"})
                .eq("id", appt_id)
                .in_("status", ["confirmed", "booked"])
                .execute()
            )
            completed += 1
        except Exception:
            logger.exception(
                "auto_complete_past_appointments: update failed for %s", appt_id
            )
            continue
        try:
            await check_appointment_triggers(appt_id, completed=True)
        except Exception:
            logger.warning(
                "auto_complete_past_appointments: trigger dispatch failed for %s",
                appt_id,
                exc_info=True,
            )

    if completed:
        logger.info("auto_complete_past_appointments: completed %d appointment(s)", completed)
    return completed
