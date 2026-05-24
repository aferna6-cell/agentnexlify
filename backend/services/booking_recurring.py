"""Recurring appointment series — generate weekly/biweekly/monthly instances."""


import logging
from datetime import date, datetime, timedelta

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


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
    from backend.services import booking as _b

    db = _b.get_service_supabase()

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

    if parent.get("recurrence_parent_id"):
        return []

    tenant_table(db, "appointments", tenant_id).update({
        "recurrence_rule": rule,
        "recurrence_end_date": end_date_str,
    }).eq("id", appointment_id).execute()

    parent_start = datetime.fromisoformat(parent["start_time"])
    parent_end = datetime.fromisoformat(parent["end_time"])
    duration = parent_end - parent_start
    end_date = date.fromisoformat(end_date_str)

    if rule == "weekly":
        delta = timedelta(weeks=1)
    elif rule == "biweekly":
        delta = timedelta(weeks=2)
    elif rule == "monthly":
        delta = timedelta(days=30)
    else:
        return []

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
            logger.warning(
                "Skipped recurring instance at %s (conflict)",
                current_start.isoformat(),
            )

        current_start += delta

    logger.info(
        "Created %d recurring instances for appointment %s (%s until %s)",
        len(created),
        appointment_id,
        rule,
        end_date_str,
    )
    return created
