"""Agent OS orchestration — one engine path (Phase 4 cutover).

POST /api/v1/os/orchestrate runs one owner turn through the agent-service
engine via the shared turn-runner: insert the user message, assemble the
tenant's SharedContext from Supabase, call agent-service, persist the
returned run record, and fire tenant-opted auto-send actions. The widget
feeds this as a data source (chat_messages -> SharedContext.widgetHistory).

When agent-service is unavailable the runner degrades honestly (saved
message + "engine offline" reply) — never a 503, never the retired legacy
orchestrator.

client_id is always the JWT tenant_id — never a path/body value. Lives beside
os_threads under the same /api/v1/os prefix (distinct paths, no shadowing).
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import agent_os_bridge, usage_meter
from backend.services.os_thread_runner import process_user_turn
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


class OrchestrateRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=8000)
    force_agent_id: str | None = Field(default=None, max_length=64)


@router.get("/context")
async def get_context(claims: dict = Depends(_get_current_tenant)):
    """Debug/inspection: the SharedContext the engine would receive."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return agent_os_bridge.assemble_shared_context(db, client_id)


@router.post("/orchestrate")
async def orchestrate(
    req: OrchestrateRequest,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    # Plan-tier cap: same gate the chat-shell route applies before each turn.
    if usage_meter.cap_reached(db, client_id):
        raise HTTPException(
            status_code=429,
            detail="Monthly agent-run limit reached for your plan. Upgrade to continue.",
        )

    # Thread must belong to this tenant.
    thread = (
        tenant_table(db, "os_threads", client_id)
        .select("id")
        .eq("id", req.thread_id)
        .limit(1)
        .execute()
    ).data or []
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": req.thread_id, "role": "user", "content": req.content})
        .execute()
        .data[0]
    )
    usage_meter.record_message(db, client_id)

    return await process_user_turn(
        db,
        client_id,
        req.thread_id,
        user_message,
        background_tasks,
        force_agent_id=req.force_agent_id,
    )
