"""Agent OS no-fit backlog — P0.

When the orchestrator finds no worker agent can serve a request, it parks
the request here. The owner reviews each one and decides: accept (build a
worker for it), decline (drop it), or defer.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services.os_opportunity_fulfill import fulfill_accepted_suggestion
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

_DECISIONS = {"accepted", "declined", "deferred"}


class BacklogDecisionRequest(BaseModel):
    decision: str = Field(description="accepted | declined | deferred")
    note: str = Field(default="", max_length=2000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/backlog")
async def list_backlog(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        tenant_table(db, "os_backlog_requests", client_id)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.post("/backlog/{request_id}/decision")
async def decide_backlog(
    request_id: str,
    req: BacklogDecisionRequest,
    background: BackgroundTasks,
    claims: dict = Depends(require_role("owner")),
):
    client_id = claims["tenant_id"]
    if req.decision not in _DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=f"decision must be one of {sorted(_DECISIONS)}",
        )
    db = get_service_supabase()
    existing = (
        tenant_table(db, "os_backlog_requests", client_id)
        .select("*")
        .eq("id", request_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Backlog request not found")
    row = existing.data[0]
    updated = (
        tenant_table(db, "os_backlog_requests", client_id)
        .update(
            {
                "status": req.decision,
                "decided_by": "owner",
                "decision_note": req.note.strip(),
                "decided_at": _now(),
            }
        )
        .eq("id", request_id)
        .execute()
    )

    # Keep the suggestion card's promise: accepting an opportunity ("Accept
    # and I'll draft a check-in for each") actually drafts the follow-ups.
    # Background + fault-tolerant - the accept response never waits on it.
    if req.decision == "accepted" and (row.get("reason") or "") == "opportunity":
        background.add_task(fulfill_accepted_suggestion, db, client_id, row)

    return updated.data[0]
