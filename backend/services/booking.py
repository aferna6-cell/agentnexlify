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


def generate_available_slots(
    tenant_id: str,
    target_date: date,
) -> list[dict]:
    """Generate available time slots for a given date.

    Returns list of {"start": "HH:MM", "end": "HH:MM", "start_utc": ISO, "end_utc": ISO}.
    Filters out already-booked slots and past times.
    """
    config = get_business_hours(tenant_id)
    if not config:
        return []

    tz = ZoneInfo(config["timezone"])
    hours = config["hours"] or DEFAULT_HOURS
    duration = config.get("slot_duration_minutes", 30)
    buffer = config.get("buffer_minutes", 0)
    step = duration + buffer

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

    result = db.table("appointments").insert(payload).execute()
    appointment = result.data[0]

    # Link to lead
    try:
        lead_id = link_appointment_to_lead(tenant_id, appointment)
        if lead_id:
            db.table("appointments").update({"lead_id": lead_id}).eq("id", appointment["id"]).execute()
            appointment["lead_id"] = lead_id
    except Exception:
        logger.warning("Failed to link appointment %s to lead", appointment["id"], exc_info=True)

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
        .eq("tenant_id", tenant_id)
        .eq("email", email)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # Create new lead
    lead = db.table("leads").insert({
        "tenant_id": tenant_id,
        "name": appointment.get("customer_name"),
        "email": email,
        "phone": appointment.get("customer_phone"),
        "source": "booking",
        "lead_stage": "qualified",
        "notes": "Created from appointment booking",
    }).execute()

    return lead.data[0]["id"] if lead.data else None


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
    return result.data[0]


def cancel_appointment(tenant_id: str, appointment_id: str) -> dict:
    """Soft-delete: set status to cancelled."""
    return update_appointment(tenant_id, appointment_id, {"status": "cancelled"})
