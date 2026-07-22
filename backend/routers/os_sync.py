"""Agent OS sync — owner-facing management routes.

The scheduled tick (in ``main.py``) drives normal sync. These routes let the
owner inspect status, enable/disable a source, force a run-now, or purge
sync state.

Routes:
- ``GET    /api/v1/os/sync/status``                  — list os_sync_state rows
- ``POST   /api/v1/os/sync/{source}/toggle``         — owner-only enable/disable
- ``POST   /api/v1/os/sync/{source}/run-now``        — owner-only manual run
- ``DELETE /api/v1/os/sync/{source}``                — owner-only purge state row
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services.os_sync import all_syncs, get_sync, run_sync
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Stage-3 plan gate (2026-07-22, audit H1): suite surface - agent_os
# plan (+ legacy) only; 402 upsell otherwise.
router = APIRouter(
    prefix="/api/v1/os/sync",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_owner(claims: dict) -> bool:
    role = claims.get("role") or ""
    return role.lower() == "owner"


class SyncToggleRequest(BaseModel):
    enabled: bool


class SyncRunNowRequest(BaseModel):
    backfill: bool = False


@router.get("/status")
async def list_sync_status(claims: dict = Depends(_get_current_tenant)):
    """Return current os_sync_state rows for the tenant + registry catalogue."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    state_rows = (
        tenant_table(db, "os_sync_state", client_id)
        .select("*")
        .order("source")
        .execute()
    ).data or []
    return {
        "registered": [
            {
                "name": spec.name,
                "description": spec.description,
                "required_connectors": spec.required_connectors,
            }
            for spec in all_syncs().values()
        ],
        "state": state_rows,
    }


@router.post("/{source}/toggle")
async def toggle_sync(
    source: str,
    req: SyncToggleRequest,
    claims: dict = Depends(_get_current_tenant),
):
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")
    if get_sync(source) is None:
        raise HTTPException(status_code=404, detail=f"Unknown sync source {source}")
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    existing = (
        tenant_table(db, "os_sync_state", client_id)
        .select("id")
        .eq("source", source)
        .limit(1)
        .execute()
    )
    if existing.data:
        updated = (
            tenant_table(db, "os_sync_state", client_id)
            .update({"enabled": req.enabled, "updated_at": _now()})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        return updated.data[0]

    created = (
        tenant_table(db, "os_sync_state", client_id)
        .insert(
            {
                "client_id": client_id,
                "source": source,
                "enabled": req.enabled,
                "status": "idle",
            }
        )
        .execute()
    )
    return created.data[0]


@router.post("/{source}/run-now")
async def run_sync_now(
    source: str,
    req: SyncRunNowRequest,
    background: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Owner-only: schedule a manual sync. Returns immediately; state polled via /status."""
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")
    if get_sync(source) is None:
        raise HTTPException(status_code=404, detail=f"Unknown sync source {source}")
    client_id = claims["tenant_id"]
    background.add_task(run_sync, client_id, source, req.backfill)
    return {"scheduled": True, "source": source, "backfill": req.backfill}


@router.delete("/{source}")
async def purge_sync_state(source: str, claims: dict = Depends(_get_current_tenant)):
    """Owner-only: drop the os_sync_state row for one source. Memory entries remain."""
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    deleted = (
        tenant_table(db, "os_sync_state", client_id)
        .delete()
        .eq("source", source)
        .execute()
    )
    return {"deleted": bool(deleted.data)}
