"""iCal feed builder for appointments.

Pulled out of `ical_feed` in the appointments router so the handler stays
focused on auth + HTTP. Owns date-range fetch, line-by-line iCal
serialization, and timestamp formatting.

DB helper accepts `db: Any` so test patches at
`backend.routers.appointments.get_service_supabase` still apply.
"""

from datetime import datetime, timedelta, timezone
from typing import Any


def format_ical_dt(dt_str: str) -> str:
    """Convert an ISO timestamp string to iCal `YYYYMMDDTHHMMSSZ`."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return dt_str.replace("-", "").replace(":", "").replace(" ", "T")[:15] + "Z"


def fetch_ical_appointments(db: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Fetch non-cancelled appointments in the iCal feed window.

    Window: 30 days back, 90 days forward, ordered by start_time, max 500.
    """
    cutoff_past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    cutoff_future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()

    result = (
        db.table("appointments")
        .select(
            "id, customer_name, customer_email, customer_phone, "
            "start_time, end_time, status, notes"
        )
        .eq("tenant_id", tenant_id)
        .neq("status", "cancelled")
        .gte("start_time", cutoff_past)
        .lte("start_time", cutoff_future)
        .order("start_time")
        .limit(500)
        .execute()
    )
    return result.data or []


def build_appointments_ical(
    appointments: list[dict[str, Any]], business_name: str
) -> str:
    """Render appointment dicts as RFC 5545 iCal text.

    Maps `no_show` status to iCal `CANCELLED`. All other non-cancelled
    statuses render as `CONFIRMED`.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//AgentNexLiFy//{business_name}//EN",
        f"X-WR-CALNAME:{business_name} Appointments",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for appt in appointments:
        uid = appt["id"]
        summary = f"Appointment: {appt.get('customer_name', 'Customer')}"
        description_parts = []
        if appt.get("customer_email"):
            description_parts.append(f"Email: {appt['customer_email']}")
        if appt.get("customer_phone"):
            description_parts.append(f"Phone: {appt['customer_phone']}")
        if appt.get("notes"):
            description_parts.append(f"Notes: {appt['notes']}")
        if appt.get("status"):
            description_parts.append(f"Status: {appt['status']}")
        description = "\\n".join(description_parts)

        dtstart = format_ical_dt(appt["start_time"])
        dtend = format_ical_dt(appt["end_time"])

        status = "CANCELLED" if appt.get("status") == "no_show" else "CONFIRMED"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}@agentnexlify.com",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"STATUS:{status}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
