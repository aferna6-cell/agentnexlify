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
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import agent_os_bridge, usage_meter
from backend.services.demo_guard import is_demo_tenant
from backend.services.os_thread_runner import process_user_turn
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

# Live-demo sandbox: hard daily turn budget shared by all demo visitors.
# Self-resets at midnight UTC (like the nightly data reset) and is checked
# BEFORE the plan-tier monthly cap so the demo never shows an "upgrade"
# message. Bounds Claude token burn from the public demo.
_DEMO_DAILY_TURN_CAP = 250


def _demo_turns_exhausted(db, client_id: str) -> bool:
    """True when the demo tenant has used today's turn budget. Fails open."""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        result = (
            tenant_table(db, "os_messages", client_id)
            .select("id", count="exact")
            .eq("role", "user")
            .gte("created_at", f"{today}T00:00:00+00:00")
            .limit(1)
            .execute()
        )
        used = result.count or 0
        return used >= _DEMO_DAILY_TURN_CAP
    except Exception:
        logger.warning("demo turn-cap check failed for %s — allowing turn", client_id, exc_info=True)
        return False


def _require_agent_os_plan(db, client_id: str) -> None:
    """The AI Workforce (Agent OS) is the agent_os plan only.

    The chatbot plan's AI Front Desk runs through the widget chat endpoint,
    not orchestrate, so a chatbot/free tenant must not reach the multi-agent
    workforce here. Demo tenants always pass so the public sales demo works.
    Reads the live plan (never stale JWT claims) and fails closed.
    """
    if is_demo_tenant(client_id):
        return
    if usage_meter.tenant_plan(db, client_id) != "agent_os":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "plan_upgrade_required",
                "message": (
                    "The AI Workforce is included with the AI Workforce plan. "
                    "Upgrade to put your full AI staff to work."
                ),
                "upgrade_path": "/billing",
            },
        )


class OrchestrateRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=8000)
    force_agent_id: str | None = Field(default=None, max_length=64)


@router.get("/context")
async def get_context(claims: dict = Depends(_get_current_tenant)):
    """Debug/inspection: the SharedContext the engine would receive."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    _require_agent_os_plan(db, client_id)
    return agent_os_bridge.assemble_shared_context(db, client_id)


@router.post("/orchestrate")
async def orchestrate(
    req: OrchestrateRequest,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    # AI Workforce is agent_os-plan only (demo tenants exempt).
    _require_agent_os_plan(db, client_id)

    if is_demo_tenant(client_id) and _demo_turns_exhausted(db, client_id):
        raise HTTPException(
            status_code=429,
            detail=(
                "The live demo has reached today's activity limit — it resets "
                "overnight. Start your free account to keep going."
            ),
        )

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
