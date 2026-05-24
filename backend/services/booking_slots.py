"""Available-slot generation: business hours, exceptions, booking conflicts."""


import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


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
    from backend.services import booking as _b

    config = _b.get_business_hours(tenant_id)
    if not config:
        return []

    tz = ZoneInfo(config["timezone"])
    hours = config["hours"] or _b.DEFAULT_HOURS
    duration = config.get("slot_duration_minutes", 30)
    buffer = config.get("buffer_minutes", 0)
    step = duration + buffer

    # Check for exception date overrides (holidays, special hours)
    exception = _b._get_exception_for_date(hours, target_date)
    if exception:
        if exception.get("closed", False):
            logger.info(
                "slots: date %s is closed (exception override) for tenant %s",
                target_date,
                tenant_id,
            )
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
        day_name = _b.DAY_NAMES[target_date.weekday()]
        day_config = hours.get(day_name, {})

        if not day_config.get("enabled", False):
            return []

        start_parts = day_config["start"].split(":")
        end_parts = day_config["end"].split(":")
        day_start = time(int(start_parts[0]), int(start_parts[1]))
        day_end = time(int(end_parts[0]), int(end_parts[1]))

    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)

    slots = []
    current = datetime.combine(target_date, day_start, tzinfo=tz)
    end_boundary = datetime.combine(target_date, day_end, tzinfo=tz)

    while current + timedelta(minutes=duration) <= end_boundary:
        slot_end = current + timedelta(minutes=duration)

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

    day_start_utc = datetime.combine(target_date, day_start, tzinfo=tz).astimezone(timezone.utc)
    day_end_utc = datetime.combine(target_date, day_end, tzinfo=tz).astimezone(timezone.utc)

    db = _b.get_service_supabase()
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

    # Fetch Google Calendar busy times (best-effort)
    try:
        from backend.services.google_calendar import get_busy_times, get_integration

        if get_integration(tenant_id):
            gcal_busy = get_busy_times(tenant_id, day_start_utc, day_end_utc)
            booked_ranges.extend(gcal_busy)
    except Exception:
        logger.warning(
            "Failed to fetch Google Calendar busy times for tenant %s",
            tenant_id,
            exc_info=True,
        )

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
