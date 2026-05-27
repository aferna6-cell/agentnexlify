"""Agent OS agent-run inspection — P0.

A run is the async record of one worker-agent invocation. The UI polls
GET /agent-runs/{run_id} for live status + thought process while the stub
worker executes in a background task. report-bug flags a run for review.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


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


@router.get("/agent-runs/{run_id}")
async def get_agent_run(run_id: str, claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return _load_run(db, client_id, run_id)


@router.post("/agent-runs/{run_id}/report-bug")
async def report_bug(run_id: str, claims: dict = Depends(_get_current_tenant)):
    """Flag a run as buggy. Records the timestamp for later triage."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    _load_run(db, client_id, run_id)
    updated = (
        tenant_table(db, "os_agent_runs", client_id)
        .update({"bug_reported_at": _now(), "updated_at": _now()})
        .eq("id", run_id)
        .execute()
    )
    return updated.data[0]
