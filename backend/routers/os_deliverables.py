"""Agent OS deliverables — P0.

A deliverable is the approval-gated draft a worker run produces. It lives
on os_agent_runs.deliverable (JSONB) — no separate table in P0, addressed
by run_id. The owner edits it while pending, then approves or rejects.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


class DeliverableEditRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=50000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_run(db, client_id: str, run_id: str) -> dict:
    result = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return result.data[0]


def _require_pending(run: dict) -> dict:
    deliverable = run.get("deliverable")
    if not deliverable:
        raise HTTPException(status_code=404, detail="No deliverable on this run")
    if run.get("deliverable_status") != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Deliverable already {run.get('deliverable_status')}",
        )
    return deliverable


@router.patch("/deliverables/{run_id}")
async def edit_deliverable(
    run_id: str,
    req: DeliverableEditRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Edit a draft while it is still pending approval."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    run = _load_run(db, client_id, run_id)
    deliverable = dict(_require_pending(run))

    if req.title is not None:
        deliverable["title"] = req.title.strip()
    if req.body is not None:
        deliverable["body"] = req.body

    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update({"deliverable": deliverable, "updated_at": _now()})
        .eq("id", run_id)
        .execute()
    )
    return updated.data[0]


@router.post("/deliverables/{run_id}/approve")
async def approve_deliverable(run_id: str, claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    run = _load_run(db, client_id, run_id)
    _require_pending(run)
    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update({"deliverable_status": "approved", "updated_at": _now()})
        .eq("id", run_id)
        .execute()
    )
    return updated.data[0]


@router.post("/deliverables/{run_id}/reject")
async def reject_deliverable(run_id: str, claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    run = _load_run(db, client_id, run_id)
    _require_pending(run)
    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update({"deliverable_status": "rejected", "updated_at": _now()})
        .eq("id", run_id)
        .execute()
    )
    return updated.data[0]
