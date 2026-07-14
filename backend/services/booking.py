"""Appointment booking service — slot generation, conflict detection, lead linkage."""


import asyncio
import hashlib
import hmac
import html as html_mod
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

_RESCHEDULE_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60

logger = logging.getLogger(__name__)

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DEFAULT_HOURS = {
    "monday":    {"enabled": True, "start": "09:00", "end": "17:00"},
    "tuesday":   {"enabled": True, "start": "09:00", "end": "17:00"},
    "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
    "thursday":  {"enabled": True, "start": "09:00", "end": "17:00"},
    "friday":    {"enabled": True, "start": "09:00", "end": "17:00"},
    "saturday":  {"enabled": False, "start": "09:00", "end": "17:00"},
    "sunday":    {"enabled": False, "start": "09:00", "end": "17:00"},
}


def coerce_hours(value) -> dict:
    """Normalise a business_hours ``hours`` value into a dict.

    The demo seeder double-encoded hours (json.dumps into a jsonb column), so
    prod rows can hold a JSON *string* instead of an object - that shape
    crashed widget chat with AttributeError (GH #422) and would break slot
    generation the same way. Accept dict as-is, parse a JSON string, and
    return {} for anything else so consumers degrade to "no hours" instead
    of 500ing.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            import json

            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
        logger.warning("business_hours: unparseable string hours value")
    return {}


def get_business_hours(tenant_id: str) -> dict | None:
    """Fetch business hours config for a tenant. Returns None if not configured.

    ``hours`` is normalised via ``coerce_hours`` so every consumer
    (slot generation, appointments availability API) sees a dict."""
    db = get_service_supabase()
    result = (
        tenant_table(db, "business_hours", tenant_id)
        .select("*")
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    config = result.data[0]
    config["hours"] = coerce_hours(config.get("hours"))
    return config


def upsert_business_hours(tenant_id: str, data: dict) -> dict:
    """Create or update business hours for a tenant."""
    db = get_service_supabase()
    existing = get_business_hours(tenant_id)

    payload = {
        "tenant_id": tenant_id,
        "timezone": data.get("timezone", "America/New_York"),
        "hours": data.get("hours", DEFAULT_HOURS),
        "slot_duration_minutes": data.get("slot_duration_minutes", 30),
        "buffer_minutes": data.get("buffer_minutes", 0),
        "max_advance_days": data.get("max_advance_days", 30),
    }

    if existing:
        result = (
            tenant_table(db, "business_hours", tenant_id)
            .update(payload)
            .execute()
        )
    else:
        result = tenant_table(db, "business_hours", tenant_id).insert(payload).execute()

    return result.data[0] if result.data else payload


def _get_exception_for_date(hours: dict, target_date: date) -> dict | None:
    """Check if a date has an exception override in the hours JSONB.

    The hours JSONB may contain an "exceptions" key with a list of:
      {"date": "2026-12-25", "closed": true}
      {"date": "2026-12-31", "open": "10:00", "close": "14:00"}

    Returns the matching exception dict, or None if no exception applies.
    """
    exceptions = hours.get("exceptions")
    if not exceptions or not isinstance(exceptions, list):
        return None
    date_str = target_date.isoformat()
    for exc in exceptions:
        if isinstance(exc, dict) and exc.get("date") == date_str:
            return exc
    return None


def generate_available_slots(
    tenant_id: str,
    target_date: date,
) -> list[dict]:
    """Generate available time slots for a given date.

    Returns list of {"start": "HH:MM", "end": "HH:MM", "start_utc": ISO, "end_utc": ISO}.
    Filters out already-booked slots and past times.

    Supports exception dates in the hours JSONB:
    - {"date": "YYYY-MM-DD", "closed": true} => no slots for that day
    - {"date": "YYYY-MM-DD", "open": "HH:MM", "close": "HH:MM"} => override hours
    """
    config = get_business_hours(tenant_id)
    if not config:
        return []

    tz = ZoneInfo(config["timezone"])
    hours = config["hours"] or DEFAULT_HOURS
    duration = config.get("slot_duration_minutes", 30)
    buffer = config.get("buffer_minutes", 0)
    step = duration + buffer

    # Check for exception date overrides (holidays, special hours)
    exception = _get_exception_for_date(hours, target_date)
    if exception:
        if exception.get("closed", False):
            logger.info("slots: date %s is closed (exception override) for tenant %s", target_date, tenant_id)
            return []
        # Use override hours for this date
        override_open = exception.get("open")
        override_close = exception.get("close")
        if override_open and override_close:
            open_parts = override_open.split(":")
            close_parts = override_close.split(":")
            day_start = time(int(open_parts[0]), int(open_parts[1]))
            day_end = time(int(close_parts[0]), int(close_parts[1]))
        else:
            # Exception exists but no open/close and not closed — fall through to normal hours
            exception = None

    if not exception:
        # Determine day of week
        day_name = DAY_NAMES[target_date.weekday()]
        day_config = hours.get(day_name, {})

        if not day_config.get("enabled", False):
            return []

        # Parse start/end times
        start_parts = day_config["start"].split(":")
        end_parts = day_config["end"].split(":")
        day_start = time(int(start_parts[0]), int(start_parts[1]))
        day_end = time(int(end_parts[0]), int(end_parts[1]))

    # Generate all possible slot start times
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)

    slots = []
    current = datetime.combine(target_date, day_start, tzinfo=tz)
    end_boundary = datetime.combine(target_date, day_end, tzinfo=tz)

    while current + timedelta(minutes=duration) <= end_boundary:
        slot_end = current + timedelta(minutes=duration)

        # Skip past slots
        if current > now_local:
            slots.append({
                "start": current.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M"),
                "start_utc": current.astimezone(timezone.utc).isoformat(),
                "end_utc": slot_end.astimezone(timezone.utc).isoformat(),
            })

        current += timedelta(minutes=step)

    if not slots:
        return []

    # Fetch existing confirmed appointments for this date range
    day_start_utc = datetime.combine(target_date, day_start, tzinfo=tz).astimezone(timezone.utc)
    day_end_utc = datetime.combine(target_date, day_end, tzinfo=tz).astimezone(timezone.utc)

    db = get_service_supabase()
    booked = (
        tenant_table(db, "appointments", tenant_id)
        .select("start_time, end_time")
        .eq("status", "confirmed")
        .gte("start_time", day_start_utc.isoformat())
        .lte("start_time", day_end_utc.isoformat())
        .execute()
    )

    booked_ranges = []
    for appt in booked.data or []:
        b_start = datetime.fromisoformat(appt["start_time"])
        b_end = datetime.fromisoformat(appt["end_time"])
        booked_ranges.append((b_start, b_end))

    # Fetch Google Calendar busy times. If the tenant has a Google integration
    # but we CANNOT verify it (API error / bad token — get_busy_times returns
    # None), fail closed: hide this day's slots rather than offer a time that may
    # already be booked in Google (external double-booking, audit C5). A brief
    # empty-availability window during a Google outage is recoverable; a
    # double-booked customer is not. To prefer availability over this safety
    # (still show slots + confirm manually), change the `return []` below.
    try:
        from backend.services.google_calendar import get_busy_times, get_integration

        if get_integration(tenant_id):
            gcal_busy = get_busy_times(tenant_id, day_start_utc, day_end_utc)
            if gcal_busy is None:
                logger.warning(
                    "generate_available_slots: Google Calendar busy times unverifiable "
                    "for tenant %s — hiding this day's slots to avoid double-booking",
                    tenant_id,
                )
                return []
            booked_ranges.extend(gcal_busy)
    except Exception:
        logger.warning("Failed to fetch Google Calendar busy times for tenant %s", tenant_id, exc_info=True)

    # Filter out slots that overlap with booked appointments
    available = []
    for slot in slots:
        s_start = datetime.fromisoformat(slot["start_utc"])
        s_end = datetime.fromisoformat(slot["end_utc"])
        conflict = any(
            s_start < b_end and s_end > b_start
            for b_start, b_end in booked_ranges
        )
        if not conflict:
            available.append(slot)

    return available


def create_appointment(
    tenant_id: str,
    customer_name: str,
    customer_email: str,
    start_time: str,
    end_time: str,
    customer_phone: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create a new appointment with double-booking protection.

    Uses a pre-insert overlap check plus DB EXCLUDE constraint as safety net.
    Raises ValueError on conflict so callers can return 409.
    """
    db = get_service_supabase()

    # Pre-insert overlap check — catch most races before hitting DB constraint
    existing = (
        tenant_table(db, "appointments", tenant_id)
        .select("id")
        .neq("status", "cancelled")
        .lt("start_time", end_time)
        .gt("end_time", start_time)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise ValueError("This time slot is already booked. Please choose a different time.")

    payload = {
        "tenant_id": tenant_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "start_time": start_time,
        "end_time": end_time,
        "status": "confirmed",
        "notes": notes,
    }

    try:
        result = tenant_table(db, "appointments", tenant_id).insert(payload).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "exclude" in error_msg or "overlap" in error_msg or "conflicting" in error_msg:
            raise ValueError("This time slot was just booked by someone else. Please choose a different time.") from e
        raise
    appointment = result.data[0]

    # Link to lead
    try:
        lead_id = link_appointment_to_lead(tenant_id, appointment)
        if lead_id:
            tenant_table(db, "appointments", tenant_id).update({"lead_id": lead_id}).eq("id", appointment["id"]).execute()
            appointment["lead_id"] = lead_id
    except Exception:
        logger.warning("Failed to link appointment %s to lead", appointment["id"], exc_info=True)

    # Sync to Google Calendar (best-effort)
    try:
        from backend.services.google_calendar import create_calendar_event, get_integration

        if get_integration(tenant_id):
            google_event_id = create_calendar_event(
                tenant_id=tenant_id,
                summary=f"Appointment with {customer_name}",
                start_utc=start_time,
                end_utc=end_time,
                attendee_email=customer_email,
                description=f"Customer: {customer_name}\nEmail: {customer_email}"
                + (f"\nPhone: {customer_phone}" if customer_phone else "")
                + (f"\nNotes: {notes}" if notes else ""),
            )
            if google_event_id:
                tenant_table(db, "appointments", tenant_id).update({"google_event_id": google_event_id}).eq("id", appointment["id"]).execute()
                appointment["google_event_id"] = google_event_id
    except Exception:
        logger.warning("Failed to sync appointment %s to Google Calendar", appointment["id"], exc_info=True)

    # Schedule 24h/2h SMS reminders (best-effort). See appointment_reminders.py.
    try:
        from backend.services.appointment_reminders import schedule_reminders_for_appointment

        schedule_reminders_for_appointment(appointment)
    except Exception:
        logger.warning("Failed to schedule reminders for appointment %s", appointment["id"], exc_info=True)

    # Send confirmation to customer (best-effort, background)
    try:
        confirmation = _send_appointment_confirmation(tenant_id, appointment)
        loop = asyncio.get_running_loop()
        loop.create_task(confirmation)
    except RuntimeError:
        if hasattr(confirmation, "close"):
            confirmation.close()
        logger.info("No running event loop; skipping async confirmation for %s", appointment["id"])
    except Exception:
        logger.warning("Failed to send appointment confirmation for %s", appointment["id"], exc_info=True)

    return appointment


def _reschedule_link_html(appointment: dict) -> str:
    """Generate a reschedule link for the confirmation email."""
    try:
        url = build_reschedule_url(appointment["id"])
        return f'<a href="{url}" style="color: #2563eb; text-decoration: underline;">click here to reschedule</a>'
    except Exception:
        return "please contact us"


async def _send_appointment_confirmation(tenant_id: str, appointment: dict) -> None:
    """Send booking confirmation via email and/or SMS to the customer."""
    from backend.services.email_sender import send_email
    from backend.services.twilio_service import send_sms

    db = get_service_supabase()
    tenant = tenant_table(db, "tenants", tenant_id).select("business_name, business_phone").limit(1).execute()
    business_name = tenant.data[0]["business_name"] if tenant.data else "Our business"
    business_phone = (tenant.data[0].get("business_phone") or "") if tenant.data else ""

    customer_name = appointment.get("customer_name", "Customer")
    customer_email = appointment.get("customer_email")
    customer_phone = appointment.get("customer_phone")
    start_time = appointment.get("start_time", "")

    # Parse the start time for display
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        display_date = dt.strftime("%A, %B %d, %Y")
        display_time = dt.strftime("%I:%M %p")
    except Exception:
        display_date = start_time
        display_time = ""

    # Send email confirmation
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
                <p>If you need to reschedule or cancel, {_reschedule_link_html(appointment)}{f" or contact us at {safe_phone}" if business_phone else " please use the link above or contact us"}.</p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">— {safe_biz}</p>
            </div>
            """
            await send_email(
                to=customer_email,
                subject=f"Appointment Confirmed - {business_name}",
                body_html=html_body,
                tenant_id=tenant_id,
            )
            logger.info("Sent appointment confirmation email to %s for tenant %s", customer_email, tenant_id)
        except Exception:
            logger.warning("Failed to send appointment confirmation email to %s", customer_email, exc_info=True)

    # Send SMS confirmation
    if customer_phone:
        try:
            sms_body = (
                f"Hi {customer_name}! Your appointment with {business_name} is confirmed for "
                f"{display_date} at {display_time}."
                f"{' Contact us to reschedule: ' + business_phone if business_phone else ''}"
            )
            await send_sms(to=customer_phone, body=sms_body)
            logger.info("Sent appointment confirmation SMS to %s for tenant %s", customer_phone, tenant_id)
        except Exception:
            logger.warning("Failed to send appointment confirmation SMS to %s", customer_phone, exc_info=True)


def link_appointment_to_lead(tenant_id: str, appointment: dict) -> str | None:
    """Find or create a lead by email and link to the appointment."""
    email = appointment.get("customer_email")
    if not email:
        return None

    db = get_service_supabase()

    # Check for existing lead with same email
    existing = (
        tenant_table(db, "leads", tenant_id)
        .select("id")
        .eq("email", email)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # Create new lead from appointment booking
    lead = tenant_table(db, "leads", tenant_id).insert({
        "client_id": tenant_id,
        "name": appointment.get("customer_name"),
        "email": email,
        "phone": appointment.get("customer_phone"),
        "status": "appointment_booked",
        "source": "booking",
        "conversation_summary": "Created from appointment booking",
    }).execute()

    return lead.data[0]["id"] if lead.data else None


def create_recurring_series(
    tenant_id: str,
    appointment_id: str,
    rule: str,
    end_date_str: str,
) -> list[dict]:
    """Generate recurring appointment instances from a parent appointment.

    Args:
        tenant_id: The tenant owning the appointment.
        appointment_id: The parent appointment to recur.
        rule: One of 'weekly', 'biweekly', 'monthly'.
        end_date_str: YYYY-MM-DD end date for the series.

    Returns:
        List of created appointment dicts (excluding parent).
    """
    db = get_service_supabase()

    # Fetch the parent appointment
    parent_result = (
        tenant_table(db, "appointments", tenant_id)
        .select("*")
        .eq("id", appointment_id)
        .limit(1)
        .execute()
    )
    if not parent_result.data:
        return []

    parent = parent_result.data[0]

    # Don't recurse from a child appointment
    if parent.get("recurrence_parent_id"):
        return []

    # Mark the parent with recurrence info
    tenant_table(db, "appointments", tenant_id).update({
        "recurrence_rule": rule,
        "recurrence_end_date": end_date_str,
    }).eq("id", appointment_id).execute()

    # Calculate interval
    parent_start = datetime.fromisoformat(parent["start_time"])
    parent_end = datetime.fromisoformat(parent["end_time"])
    duration = parent_end - parent_start
    end_date = date.fromisoformat(end_date_str)

    if rule == "weekly":
        delta = timedelta(weeks=1)
    elif rule == "biweekly":
        delta = timedelta(weeks=2)
    elif rule == "monthly":
        delta = timedelta(days=30)  # Approximate; good enough for scheduling
    else:
        return []

    # Generate future instances
    created = []
    current_start = parent_start + delta

    while current_start.date() <= end_date:
        current_end = current_start + duration
        payload = {
            "tenant_id": tenant_id,
            "lead_id": parent.get("lead_id"),
            "customer_name": parent["customer_name"],
            "customer_email": parent["customer_email"],
            "customer_phone": parent.get("customer_phone"),
            "start_time": current_start.isoformat(),
            "end_time": current_end.isoformat(),
            "status": "confirmed",
            "notes": parent.get("notes"),
            "recurrence_rule": rule,
            "recurrence_parent_id": appointment_id,
        }

        try:
            result = tenant_table(db, "appointments", tenant_id).insert(payload).execute()
            if result.data:
                created.append(result.data[0])
        except Exception:
            # Skip conflicting slots (double-booking constraint)
            logger.warning(
                "Skipped recurring instance at %s (conflict)",
                current_start.isoformat(),
            )

        current_start += delta

    logger.info(
        "Created %d recurring instances for appointment %s (%s until %s)",
        len(created), appointment_id, rule, end_date_str,
    )
    return created


def list_appointments(
    tenant_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List appointments with optional filters."""
    db = get_service_supabase()
    query = (
        tenant_table(db, "appointments", tenant_id)
        .select("*")
        .order("start_time", desc=False)
    )

    if start_date:
        query = query.gte("start_time", start_date)
    if end_date:
        query = query.lte("start_time", end_date)
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


def update_appointment(tenant_id: str, appointment_id: str, data: dict) -> dict:
    """Update appointment fields (status, notes, reschedule)."""
    db = get_service_supabase()
    result = (
        tenant_table(db, "appointments", tenant_id)
        .update(data)
        .eq("id", appointment_id)
        .execute()
    )
    if not result.data:
        return {}

    appointment = result.data[0]

    # Sync changes to Google Calendar (best-effort)
    google_event_id = appointment.get("google_event_id")
    if google_event_id:
        try:
            from backend.services.google_calendar import update_calendar_event

            gcal_updates = {}
            if "start_time" in data:
                gcal_updates["start_utc"] = data["start_time"]
            if "end_time" in data:
                gcal_updates["end_utc"] = data["end_time"]
            if gcal_updates:
                update_calendar_event(tenant_id, google_event_id, **gcal_updates)
        except Exception:
            logger.warning("Failed to sync appointment update %s to Google Calendar", appointment_id, exc_info=True)

    return appointment


def cancel_appointment(tenant_id: str, appointment_id: str) -> dict:
    """Soft-delete: set status to cancelled."""
    # Fetch appointment first to get google_event_id
    db = get_service_supabase()
    existing = (
        tenant_table(db, "appointments", tenant_id)
        .select("google_event_id")
        .eq("id", appointment_id)
        .limit(1)
        .execute()
    )

    result = update_appointment(tenant_id, appointment_id, {"status": "cancelled"})

    # Delete from Google Calendar (best-effort)
    if existing.data and existing.data[0].get("google_event_id"):
        try:
            from backend.services.google_calendar import delete_calendar_event

            delete_calendar_event(tenant_id, existing.data[0]["google_event_id"])
        except Exception:
            logger.warning("Failed to delete Google Calendar event for appointment %s", appointment_id, exc_info=True)

    return result


# ── Reschedule link helpers ──────────────────────────────────────────────────


def _generate_reschedule_token(appointment_id: str) -> str:
    """Generate an expiring HMAC token for appointment reschedule links."""
    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload = f"reschedule:{appointment_id}:{issued_at}"
    signature = hmac.new(
        settings.api_secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{issued_at}.{signature}"


def build_reschedule_url(appointment_id: str, business_slug: str = "") -> str:
    """Build a public reschedule URL with a signed HMAC token."""
    token = _generate_reschedule_token(appointment_id)
    base_url = settings.api_url
    return f"{base_url}/api/v1/book/reschedule/{appointment_id}?token={token}"
