"""Lead-to-team-member assignment helpers.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Performer context (the user issuing the
assignment) is passed in by the router so this module stays free of HTTP
concerns.
"""

import logging
from typing import Any

from backend.services.activity import log_activity
from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)


def assign_lead_to_member(
    db: Any,
    tenant_id: str,
    lead_id: str,
    *,
    assigned_to: str | None,
    performer_id: str | None,
    performer_name: str | None,
) -> dict:
    """Assign (or, when ``assigned_to`` is None, unassign) a lead.

    Returns the updated lead row.

    Raises:
        LookupError("member"): ``assigned_to`` is set but no team member with
            that id exists for the tenant.
        LookupError("lead"): the lead row does not exist.
    """
    member_name = "nobody"
    if assigned_to:
        member_resp = (
            tenant_select(
                db, "team_members", tenant_id, "id, name, email"
            )
            .eq("id", assigned_to)
            .limit(1)
            .execute()
        )
        if not member_resp.data:
            raise LookupError("member")
        member_name = member_resp.data[0]["name"]

    update_resp = (
        tenant_update(
            db, "leads", tenant_id, {"assigned_to": assigned_to}
        )
        .eq("id", lead_id)
        .execute()
    )
    if not update_resp.data:
        raise LookupError("lead")

    try:
        log_activity(
            tenant_id=tenant_id,
            activity_type="assignment",
            description=f"Lead assigned to {member_name}",
            lead_id=lead_id,
            metadata={
                "assigned_to": assigned_to,
                "assigned_to_name": member_name,
                "performed_by": performer_id,
                "performed_by_name": performer_name,
            },
        )
    except Exception:
        logger.warning("Failed to log assignment activity", exc_info=True)

    return update_resp.data[0]
