"""No-show statistics for appointments.

Pulled out of `get_no_show_stats` in the appointments router so the
handler stays focused on auth + HTTP. Owns the aggregation and
repeat-offender ranking.

DB helper accepts `db: Any` so test patches at
`backend.routers.appointments.get_service_supabase` still apply.
"""

from typing import Any


def fetch_no_show_appointments(db: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Fetch every completed-or-no-show appointment for rate calculation."""
    result = (
        db.table("appointments")
        .select("id, status, customer_email, customer_name, lead_id")
        .eq("tenant_id", tenant_id)
        .in_("status", ["completed", "no_show"])
        .execute()
    )
    return result.data or []


def compute_no_show_stats(appointments: list[dict[str, Any]]) -> dict[str, Any]:
    """Return total, no_show_count, rate, and top-10 repeat offenders.

    Repeat offender = email/name with 2+ no-shows. Ranked by count desc,
    truncated to 10.
    """
    total = len(appointments)
    no_shows = [a for a in appointments if a["status"] == "no_show"]
    no_show_count = len(no_shows)
    no_show_rate = round((no_show_count / total * 100) if total > 0 else 0, 1)

    email_counts: dict[str, int] = {}
    for appt in no_shows:
        key = appt.get("customer_email") or appt.get("customer_name") or "unknown"
        email_counts[key] = email_counts.get(key, 0) + 1

    repeat_offenders = [
        {"customer": key, "no_show_count": count}
        for key, count in sorted(email_counts.items(), key=lambda x: -x[1])
        if count >= 2
    ][:10]

    return {
        "total_appointments": total,
        "no_show_count": no_show_count,
        "no_show_rate": no_show_rate,
        "repeat_offenders": repeat_offenders,
    }
