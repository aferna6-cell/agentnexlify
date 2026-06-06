"""Agent OS orchestration via the vendored demo engine (Phase 1b).

POST /api/v1/os/orchestrate routes one owner turn through the agent-service
engine instead of the legacy Python orchestrator: insert the user message,
assemble the tenant's SharedContext from Supabase, call agent-service, and
persist the returned run record. The widget feeds this as a data source
(chat_messages -> SharedContext.widgetHistory).

client_id is always the JWT tenant_id — never a path/body value. Lives beside
os_threads under the same /api/v1/os prefix (distinct paths, no shadowing).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import agent_os_bridge, agent_sdk_client
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
    req: OrchestrateRequest, claims: dict = Depends(_get_current_tenant)
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

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

    context = agent_os_bridge.assemble_shared_context(db, client_id)

    out = await run_in_threadpool(
        agent_sdk_client.orchestrate_sync,
        client_id,
        req.content,
        context,
        force_agent_id=req.force_agent_id,
    )
    if out is None:
        # agent-service unconfigured or errored — the user message is already
        # saved; surface a clear unavailable state rather than a silent failure.
        raise HTTPException(
            status_code=503,
            detail="Agent OS engine unavailable (AGENT_SERVICE_URL not set or request failed)",
        )

    persisted = agent_os_bridge.persist_orchestration(db, client_id, req.thread_id, out)
    return {"user_message": user_message, **persisted}
