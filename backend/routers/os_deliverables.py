"""Agent OS deliverables — P0 + Group B action wiring.

A deliverable is the approval-gated draft a worker run produces. It lives
on os_agent_runs.deliverable (JSONB) — no separate table in P0, addressed
by run_id. The owner edits it while pending, then approves or rejects.

On approve, if the deliverable's parent ``os_agent_runs.action_type`` is
set and matches a registered handler in ``backend/services/os_actions/``,
the handler is scheduled via FastAPI BackgroundTasks. The run row is
written to ``os_action_runs`` and linked back via ``action_run_id``.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.os_actions import all_actions, get_action, run_action
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


def _is_owner(claims: dict) -> bool:
    role = claims.get("role") or ""
    return role.lower() == "owner"


@router.get("/deliverables/pending")
async def list_pending_deliverables(claims: dict = Depends(_get_current_tenant)):
    """Return all runs with deliverable_status='pending_approval' for this tenant.

    Powers the sidebar approval badge — operators see pending drafts from any
    page. Returns count + lightweight summary items (no full deliverable body)
    so the badge poll stays cheap.
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("*")
        .eq("deliverable_status", "pending_approval")
        .order("updated_at", desc=True)
        .execute()
    )
    items = []
    for row in result.data or []:
        deliverable = row.get("deliverable") or {}
        # Skip legacy v1-shape drafts (have 'format', lack 'channel'). Migration
        # 132 rejects the historical backlog; this keeps the queue v2-only if the
        # engine ever falls back to a legacy worker.
        if deliverable.get("format") and not deliverable.get("channel"):
            continue
        items.append(
            {
                "run_id": row.get("id"),
                "title": deliverable.get("title", ""),
                "thread_id": row.get("thread_id"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )
    return {"count": len(items), "items": items}


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
async def approve_deliverable(
    run_id: str,
    background: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Approve a deliverable and schedule its action handler (if any).

    If the parent agent_run has an ``action_type`` matching a registered
    handler, an ``os_action_runs`` row is created with ``status='queued'``
    and the handler is scheduled via BackgroundTasks. If no action_type is
    set, the deliverable is approved with no side effect (display-only).

    Owner-only: approval can fire a real-world send (SMS/email/widget), the
    same bar ``retry_action_run`` already enforces.
    """
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")

    client_id = claims["tenant_id"]
    db = get_service_supabase()
    run = _load_run(db, client_id, run_id)
    _require_pending(run)

    action_run_id = await queue_action_for_run(db, client_id, run, background)

    update_fields = {"deliverable_status": "approved", "updated_at": _now()}
    if action_run_id:
        update_fields["action_run_id"] = action_run_id

    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update(update_fields)
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


@router.get("/action-runs/{action_run_id}")
async def get_action_run(
    action_run_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Return one action run for status polling in the UI."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        tenant_table(db, "os_action_runs", client_id)
        .select("*")
        .eq("id", action_run_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Action run not found")
    return result.data[0]


@router.post("/action-runs/{action_run_id}/retry")
async def retry_action_run(
    action_run_id: str,
    background: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Owner-only: retry a failed action run.

    Reuses the deliverable + action_type but creates a NEW os_action_runs row
    so the prior attempt's history is preserved.
    """
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")

    client_id = claims["tenant_id"]
    db = get_service_supabase()
    existing = (
        tenant_table(db, "os_action_runs", client_id)
        .select("*")
        .eq("id", action_run_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Action run not found")
    row = existing.data[0]
    if row.get("status") != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry action in status={row.get('status')}",
        )

    action_type = row["action_type"]
    deliverable_id = row["deliverable_id"]
    if get_action(action_type) is None:
        raise HTTPException(
            status_code=400, detail=f"Unknown action_type {action_type}"
        )

    created = (
        tenant_table(db, "os_action_runs", client_id)
        .insert(
            {
                "client_id": client_id,
                "deliverable_id": deliverable_id,
                "action_type": action_type,
                "status": "queued",
                "request_payload": {},
            }
        )
        .execute()
    )
    new_action_run_id = created.data[0]["id"]
    background.add_task(
        run_action, new_action_run_id, client_id, deliverable_id, action_type
    )

    tenant_table(db, "os_agent_runs", client_id).update(
        {"action_run_id": new_action_run_id, "updated_at": _now()}
    ).eq("id", deliverable_id).execute()

    return created.data[0]


@router.get("/actions/registered")
async def list_registered_actions(
    _claims: dict = Depends(_get_current_tenant),
):
    """Debug/UI helper — list registered action handlers."""
    return {
        "actions": [
            {
                "name": spec.name,
                "worker": spec.worker,
                "description": spec.description,
                "required_connectors": spec.required_connectors,
            }
            for spec in all_actions().values()
        ]
    }
