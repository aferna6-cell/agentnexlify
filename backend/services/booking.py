"""Appointment booking service — slot generation, conflict detection, lead linkage."""


import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.models.database import get_supabase

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


def get_business_hours(tenant_id: str) -> dict | None:
    """Fetch business hours config for a tenant. Returns None if not configured."""
    db = get_supabase()
    result = (
        db.table("business_hours")
        .select("*")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_business_hours(tenant_id: str, data: dict) -> dict:
    """Create or update business hours for a tenant."""
    db = get_supabase()
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
            db.table("business_hours")
            .update(payload)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    else:
        result = db.table("business_hours").insert(payload).execute()

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

    db = get_supabase()
    booked = (
        db.table("appointments")
        .select("start_time, end_time")
        .eq("tenant_id", tenant_id)
        .in_("status", ["confirmed", "checked_in", "pending"])
        .gte("start_time", day_start_utc.isoformat())
        .lte("start_time", day_end_utc.isoformat())
        .execute()
    )

    booked_ranges = []
    buffer_td = timedelta(minutes=buffer)
    for appt in booked.data or []:
        b_start = datetime.fromisoformat(appt["start_time"])
        b_end = datetime.fromisoformat(appt["end_time"])
        # Extend booked range by buffer_minutes after end to prevent
        # scheduling too close together (travel time, cleanup, etc.)
        booked_ranges.append((b_start, b_end + buffer_td))

    # Fetch Google Calendar busy times (best-effort)
    try:
        from backend.services.google_calendar import get_busy_times, get_integration

        if get_integration(tenant_id):
            gcal_busy = get_busy_times(tenant_id, day_start_utc, day_end_utc)
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
    lead_id: str | None = None,
) -> dict:
    """Create a new appointment. Raises on double-booking (DB constraint)."""
    db = get_supabase()

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
    if lead_id:
        payload["lead_id"] = lead_id

    result = db.table("appointments").insert(payload).execute()
    appointment = result.data[0]

    # Link to lead (if not already linked)
    if not lead_id:
        try:
            lead_id = link_appointment_to_lead(tenant_id, appointment)
            if lead_id:
                db.table("appointments").update({"lead_id": lead_id}).eq("id", appointment["id"]).execute()
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
                db.table("appointments").update({"google_event_id": google_event_id}).eq("id", appointment["id"]).execute()
                appointment["google_event_id"] = google_event_id
    except Exception:
        logger.warning("Failed to sync appointment %s to Google Calendar", appointment["id"], exc_info=True)

    # Fetch tenant data once for confirmations (SMS + email)
    _confirm_tenant = {}
    if customer_phone or customer_email:
        try:
            _tr = db.table("tenants").select("business_name, plan, sms_notifications_enabled").eq("id", tenant_id).limit(1).execute()
            _confirm_tenant = _tr.data[0] if _tr.data else {}
        except Exception:
            logger.warning("Failed to fetch tenant data for appointment confirmations", exc_info=True)

    _confirm_biz = _confirm_tenant.get("business_name") or "our office"
    _confirm_plan = _confirm_tenant.get("plan") or "free"

    # Format the time for display
    try:
        from datetime import datetime as _dt
        _confirm_dt = _dt.fromisoformat(start_time.replace("Z", "+00:00"))
        _confirm_formatted = _confirm_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        _confirm_formatted_short = _confirm_dt.strftime("%A, %B %d at %I:%M %p")
    except (ValueError, AttributeError):
        _confirm_formatted = start_time
        _confirm_formatted_short = start_time

    # Send appointment confirmation SMS to customer
    if customer_phone and _confirm_plan != "free":
        try:
            from backend.services.sms_rate_limiter import check_sms_rate_limit
            if check_sms_rate_limit(tenant_id, _confirm_plan):
                from backend.services.twilio_service import send_sms as _send_confirm_sms
                _send_confirm_sms(
                    to=customer_phone,
                    body=f"Your appointment with {_confirm_biz} is confirmed for {_confirm_formatted_short}. Reply STOP to opt out.",
                    from_number=None,
                )
                logger.info("Sent confirmation SMS to %s for appointment %s", customer_phone, appointment["id"])
        except Exception:
            logger.warning("Failed to send confirmation SMS for appointment %s", appointment["id"], exc_info=True)

    # Send appointment confirmation email to customer
    if customer_email:
        try:
            from backend.services.email_sender import send_email as _send_confirm_email
            _send_confirm_email(
                to=customer_email,
                subject=f"Appointment Confirmed — {_confirm_biz}",
                html=f"""
                <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;">
                    <h2 style="color:#10b981;">Appointment Confirmed</h2>
                    <p>Hi {customer_name},</p>
                    <p>Your appointment with <strong>{_confirm_biz}</strong> has been confirmed:</p>
                    <div style="background:#f9fafb;border-radius:8px;padding:16px;margin:16px 0;">
                        <p style="margin:4px 0;"><strong>Date & Time:</strong> {_confirm_formatted}</p>
                        {f'<p style="margin:4px 0;"><strong>Notes:</strong> {notes}</p>' if notes else ''}
                    </div>
                    <p style="color:#666;font-size:13px;">We look forward to seeing you!</p>
                    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
                    <p style="color:#999;font-size:12px;">{_confirm_biz} — Powered by AgentNexLiFy</p>
                </div>
                """,
            )
            logger.info("Sent confirmation email to %s for appointment %s", customer_email, appointment["id"])
        except Exception:
            logger.warning("Failed to send confirmation email for appointment %s", appointment["id"], exc_info=True)

    return appointment


def link_appointment_to_lead(tenant_id: str, appointment: dict) -> str | None:
    """Find or create a lead by email and link to the appointment."""
    email = appointment.get("customer_email")
    if not email:
        return None

    db = get_supabase()

    # Check for existing lead with same email
    existing = (
        db.table("leads")
        .select("id")
        .eq("client_id", tenant_id)
        .eq("email", email)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # Create new lead from appointment booking
    lead = db.table("leads").insert({
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
    db = get_supabase()

    # Fetch the parent appointment
    parent_result = (
        db.table("appointments")
        .select("*")
        .eq("id", appointment_id)
        .eq("tenant_id", tenant_id)
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
    db.table("appointments").update({
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
            result = db.table("appointments").insert(payload).execute()
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
    db = get_supabase()
    query = (
        db.table("appointments")
        .select("*")
        .eq("tenant_id", tenant_id)
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
    db = get_supabase()
    result = (
        db.table("appointments")
        .update(data)
        .eq("id", appointment_id)
        .eq("tenant_id", tenant_id)
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
    db = get_supabase()
    existing = (
        db.table("appointments")
        .select("google_event_id")
        .eq("id", appointment_id)
        .eq("tenant_id", tenant_id)
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
