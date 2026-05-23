"""Lead field-update mutation helper.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Owns the update + dual event-fire pattern
(lead.updated always, lead.status_changed when status field is in the
patch). Router still owns auth + HTTP-shape concerns.
"""

import logging
from collections.abc import Callable
from typing import Any

from backend.services.tenant_scope import tenant_update

logger = logging.getLogger(__name__)


def apply_lead_update(
    db: Any,
    tenant_id: str,
    lead_id: str,
    updates: dict,
    *,
    fire_event: Callable[[str, str, dict], Any] | None = None,
) -> dict:
    """Patch a lead, fire lead.updated, conditionally fire lead.status_changed.

    Returns the updated lead row.

    Raises:
        ValueError: ``updates`` is empty. Router maps to HTTP 400.
        LookupError("not_found"): update affected no rows. Router maps to 404.
    """
    if not updates:
        raise ValueError("no_updates")

    result = tenant_update(db, "leads", tenant_id, updates).eq("id", lead_id).execute()
    if not result.data:
        raise LookupError("not_found")

    if fire_event is not None:
        fire_event(
            tenant_id,
            "lead.updated",
            {
                "lead_id": lead_id,
                "updated_fields": list(updates.keys()),
                **updates,
            },
        )
        if "status" in updates:
            fire_event(
                tenant_id,
                "lead.status_changed",
                {
                    "lead_id": lead_id,
                    "new_status": updates["status"],
                    "source": "leads_update",
                },
            )

    return result.data[0]
