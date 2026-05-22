"""Agent OS threads + the orchestration flow — P0.

A thread is one task conversation. Posting a user message runs the
orchestrator, which routes the message one of three ways:
  - answer:   an assistant reply is posted, no worker run
  - delegate: an os_agent_runs row is created and a worker run is
              scheduled as a FastAPI background task
  - backlog:  an os_backlog_requests row is created for an owner decision

client_id is always the JWT tenant_id — never trust a path/body value.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import orchestrator, os_workers, usage_meter
from backend.services.email_sender import send_email
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


class ThreadCreateRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=200)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/threads", status_code=201)
async def create_thread(
    req: ThreadCreateRequest, claims: dict = Depends(_get_current_tenant)
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    created = (
        tenant_table(db, "os_threads", client_id)
        .insert({"title": req.title.strip() or "New conversation"})
        .execute()
    )
    return created.data[0]


@router.get("/threads")
async def list_threads(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        tenant_table(db, "os_threads", client_id)
        .select("*")
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/threads/{thread_id}/messages")
async def list_messages(thread_id: str, claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    _load_thread(db, client_id, thread_id)
    messages = (
        tenant_table(db, "os_messages", client_id)
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    runs = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"messages": messages.data or [], "agent_runs": runs.data or []}


@router.post("/threads/{thread_id}/messages", status_code=201)
async def post_message(
    thread_id: str,
    req: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Post a user message and run the orchestrator on it."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    _load_thread(db, client_id, thread_id)

    if usage_meter.cap_reached(db, client_id):
        raise HTTPException(
            status_code=429,
            detail="Monthly agent-run cap reached for this billing cycle.",
        )

    user_content = req.content.strip()
    history = (
        tenant_table(db, "os_messages", client_id)
        .select("role, content")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    ).data or []

    messages_tbl = tenant_table(db, "os_messages", client_id)
    user_message = (
        messages_tbl.insert(
            {"thread_id": thread_id, "role": "user", "content": user_content}
        )
        .execute()
        .data[0]
    )
    usage_meter.record_message(db, client_id)

    decision = await orchestrator.orchestrate(
        db, client_id, user_content, history=history
    )
    if decision.memory_writes:
        await orchestrator.record_memory_writes(
            db, client_id, decision.memory_writes, source=f"thread:{thread_id}"
        )

    agent_runs: list[dict] = []
    if decision.action == "delegate":
        run = (
            tenant_table(db, "os_agent_runs", client_id)
            .insert(
                {
                    "thread_id": thread_id,
                    "agent_name": decision.agent_name,
                    "status": "queued",
                    "thought_process": decision.thought_process,
                }
            )
            .execute()
            .data[0]
        )
        agent_runs.append(run)
        assistant_message = (
            messages_tbl.insert(
                {
                    "thread_id": thread_id,
                    "role": "assistant",
                    "content": decision.reply,
                    "agent_run_id": run["id"],
                }
            )
            .execute()
            .data[0]
        )
        background_tasks.add_task(
            os_workers.run_worker,
            run["id"],
            client_id,
            thread_id,
            decision.agent_name,
            user_content,
            decision.deliverable_title or "Draft",
        )
    elif decision.action == "backlog":
        _create_backlog(db, client_id, thread_id, user_content, decision)
        assistant_message = (
            messages_tbl.insert(
                {"thread_id": thread_id, "role": "assistant", "content": decision.reply}
            )
            .execute()
            .data[0]
        )
        await _notify_owner_no_fit(db, client_id, user_content, decision)
    else:  # answer
        assistant_message = (
            messages_tbl.insert(
                {"thread_id": thread_id, "role": "assistant", "content": decision.reply}
            )
            .execute()
            .data[0]
        )

    tenant_table(db, "os_threads", client_id).update({"updated_at": _now()}).eq(
        "id", thread_id
    ).execute()

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "action": decision.action,
        "agent_runs": agent_runs,
    }


def _load_thread(db, client_id: str, thread_id: str) -> dict:
    result = (
        tenant_table(db, "os_threads", client_id)
        .select("*")
        .eq("id", thread_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Thread not found")
    return result.data[0]


def _create_backlog(
    db, client_id: str, thread_id: str, user_content: str, decision
) -> None:
    tenant_table(db, "os_backlog_requests", client_id).insert(
        {
            "thread_id": thread_id,
            "summary": (decision.deliverable_title or user_content)[:200],
            "detail": user_content,
            "reason": decision.reason or "No available worker agent fits.",
        }
    ).execute()


async def _notify_owner_no_fit(db, client_id: str, user_content: str, decision) -> None:
    """Best-effort owner email when a request lands in the no-fit backlog."""
    try:
        tenant = (
            db.table("tenants")
            .select("owner_email, business_name")
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        if not tenant.data or not tenant.data[0].get("owner_email"):
            return
        owner_email = tenant.data[0]["owner_email"]
        business = tenant.data[0].get("business_name") or "your business"
        await send_email(
            to=owner_email,
            subject="Agent OS: a request needs your decision",
            body_html=(
                f"<p>A request for {business} could not be handled by any "
                f"current worker agent and was parked in the backlog.</p>"
                f"<p><strong>Request:</strong> {user_content}</p>"
                f"<p><strong>Why no fit:</strong> "
                f"{decision.reason or 'No worker agent matches this task.'}</p>"
                "<p>Review it in the Agent OS backlog to build, defer, or drop it.</p>"
            ),
            tenant_id=client_id,
        )
    except Exception:
        logger.warning("no-fit owner notification failed", exc_info=True)
