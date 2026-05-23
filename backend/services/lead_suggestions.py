"""Lead suggestion approve/dismiss helpers.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Suggestions are stored as `activity_log`
rows with `activity_type='lead_suggestion'`. Approving promotes the
suggested field deltas into the lead row; both approve and dismiss
delete the suggestion afterwards.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_delete, tenant_select, tenant_update

logger = logging.getLogger(__name__)

VALID_ACTIONS = ("approve", "dismiss")


def apply_or_dismiss_suggestion(
    db: Any,
    tenant_id: str,
    suggestion_id: str,
    action: str,
) -> dict:
    """Approve or dismiss a lead update suggestion.

    Returns ``{"success": True, "action": <action>}`` on success.

    Raises:
        ValueError: ``action`` is not "approve" or "dismiss".
        LookupError("not_found"): suggestion row does not exist for tenant.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"action must be one of {VALID_ACTIONS}")

    suggestion = (
        tenant_select(db, "activity_log", tenant_id, "id, lead_id, metadata")
        .eq("id", suggestion_id)
        .eq("activity_type", "lead_suggestion")
        .limit(1)
        .execute()
    )
    if not suggestion.data:
        raise LookupError("not_found")

    entry = suggestion.data[0]

    if action == "approve":
        suggestions = (entry.get("metadata") or {}).get("suggestions", {})
        lead_id = entry.get("lead_id")
        if suggestions and lead_id:
            updates = {field: s["new"] for field, s in suggestions.items()}
            tenant_update(db, "leads", tenant_id, updates).eq(
                "id", lead_id
            ).execute()
            logger.info(
                "Approved suggestion %s: updated lead %s with %s",
                suggestion_id,
                lead_id,
                list(updates.keys()),
            )

    tenant_delete(db, "activity_log", tenant_id).eq("id", suggestion_id).execute()

    return {"success": True, "action": action}
