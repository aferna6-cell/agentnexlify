"""Business hours configuration — fetch, upsert, exception lookups."""


import logging
from datetime import date

from backend.services.tenant_scope import tenant_table

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
    from backend.services import booking as _b
    db = _b.get_service_supabase()
    result = (
        tenant_table(db, "business_hours", tenant_id)
        .select("*")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_business_hours(tenant_id: str, data: dict) -> dict:
    """Create or update business hours for a tenant."""
    from backend.services import booking as _b
    db = _b.get_service_supabase()
    existing = _b.get_business_hours(tenant_id)

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
