"""Activity timeline helpers for the leads router.

Pulled out of `get_lead_activity` so the router stays focused on auth +
404 mapping. Functions here own the cross-table fetch + merge into a
single chronological timeline.

DB helpers accept `db: Any` so the router's
`get_service_supabase()` patch (used by tests) still applies.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)


def lead_exists(db: Any, tenant_id: str, lead_id: str) -> bool:
    """Cheap existence check used to map missing leads to HTTP 404."""
    result = (
        tenant_select(db, "leads", tenant_id, "id")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def fetch_lead_timeline(
    db: Any, tenant_id: str, lead_id: str, *, limit: int = 100
) -> list[dict[str, Any]]:
    """Return up to `limit` timeline entries for a lead, sorted desc.

    Merges activity_log (50), appointments (20), and email_events (20)
    into a single shape with `type/description/metadata/created_at`.
    """
    activity = (
        tenant_select(
            db, "activity_log", tenant_id,
            "id, activity_type, description, metadata, created_at",
        )
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    appointments = (
        tenant_select(
            db, "appointments", tenant_id,
            "id, customer_name, start_time, status, created_at",
        )
        .eq("lead_id", lead_id)
        .order("start_time", desc=True)
        .limit(20)
        .execute()
    )

    email_events = (
        tenant_select(
            db, "email_events", tenant_id,
            "id, event_type, details, created_at",
        )
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )

    timeline: list[dict[str, Any]] = []

    for a in (activity.data or []):
        timeline.append({
            "type": a.get("activity_type") or "activity",
            "description": a.get("description") or "",
            "metadata": a.get("metadata"),
            "created_at": a["created_at"],
        })

    for appt in (appointments.data or []):
        status = appt.get("status") or "scheduled"
        timeline.append({
            "type": f"appointment_{status}",
            "description": (
                f"Appointment ({status}): "
                f"{appt.get('customer_name') or 'Customer'} at "
                f"{appt.get('start_time', '')}"
            ),
            "metadata": {"appointment_id": appt["id"]},
            "created_at": appt["created_at"],
        })

    for ev in (email_events.data or []):
        timeline.append({
            "type": f"email_{ev.get('event_type', 'event')}",
            "description": f"Email {ev.get('event_type', 'event')}",
            "metadata": ev.get("details"),
            "created_at": ev["created_at"],
        })

    timeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return timeline[:limit]
