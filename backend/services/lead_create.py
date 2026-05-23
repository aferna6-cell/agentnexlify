"""Manual lead-creation helper.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Owns payload assembly + insert + activity
log + outbound event firing. Router still owns the auth check and
HTTP-shape concerns.
"""

import logging
from collections.abc import Callable
from typing import Any

from backend.services.activity import log_activity
from backend.services.tenant_scope import tenant_insert

logger = logging.getLogger(__name__)


def build_manual_lead_payload(
    tenant_id: str,
    *,
    name: str | None,
    email: str | None,
    phone: str | None,
    status: str | None,
    lead_temperature: str | None,
    areas_of_interest: str | None,
    deal_value: float | None,
    expected_close_date: str | None,
) -> dict:
    """Assemble the insert payload for a manually-created lead.

    Drops keys with ``None`` values so the DB defaults apply.
    """
    payload: dict[str, Any] = {
        "client_id": tenant_id,
        "name": name,
        "email": email,
        "phone": phone,
        "status": status or "new",
        "lead_temperature": lead_temperature,
        "areas_of_interest": areas_of_interest,
        "source": "manual",
    }
    if deal_value is not None:
        payload["deal_value"] = deal_value
    if expected_close_date:
        payload["expected_close_date"] = expected_close_date
    return {k: v for k, v in payload.items() if v is not None}


def insert_manual_lead(
    db: Any,
    tenant_id: str,
    payload: dict,
    *,
    performer_id: str | None,
    performer_name: str | None,
    fire_event: Callable[[str, str, dict], Any] | None = None,
) -> dict:
    """Insert the lead, log the activity, fire the webhook event.

    Returns the inserted lead row.

    Raises:
        RuntimeError: insert returned no row (treated as 500 router-side).
    """
    result = tenant_insert(db, "leads", tenant_id, payload).execute()
    if not result.data:
        raise RuntimeError("insert_failed")

    lead = result.data[0]
    descriptor = payload.get("name") or payload.get("email") or payload.get("phone")
    log_activity(
        tenant_id=tenant_id,
        lead_id=lead["id"],
        activity_type="lead_created",
        description=f"Lead created manually: {descriptor}",
        metadata={
            "performed_by": performer_id,
            "performed_by_name": performer_name,
        },
    )
    if fire_event is not None:
        fire_event(
            tenant_id,
            "lead.created",
            {
                "lead_id": lead["id"],
                "name": payload.get("name"),
                "source": "manual",
            },
        )
    return lead
