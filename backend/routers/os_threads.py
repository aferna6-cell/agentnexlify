"""Agent OS threads + the orchestration flow — P0.

A thread is one task conversation. Posting a user message runs the
orchestrator, which routes the message one of three ways:
  - answer:   an assistant reply is posted, no worker run
  - delegate: an os_agent_runs row is created and a worker run is
              scheduled as a FastAPI background task
  - backlog:  an os_backlog_requests row is created for an owner decision

client_id is always the JWT tenant_id — never trust a path/body value.

Per-turn orchestration (history fetch + orchestrate + persist) lives in
``backend.services.os_thread_runner`` so inbound bridges (widget, email,
SMS, Facebook) share the same pipeline. This router owns thread/message
CRUD and the rate-limit gate; the runner owns the orchestrator turn.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import usage_meter
from backend.services.os_thread_runner import process_user_turn
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


class ThreadCreateRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=200)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


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
    agent_runs = _attach_routing(db, client_id, runs.data or [])
    return {"messages": messages.data or [], "agent_runs": agent_runs}


def _attach_routing(db, client_id: str, runs: list[dict]) -> list[dict]:
    """Attach a compact ``routing`` object to each run for the dashboard.

    Surfaces the orchestrator's decision (classifier, chosen agent, confidence,
    alternates) from os_routing_decision plus the routing model from
    os_model_call_log so the trace can show "Routed to X · 92% · haiku". Best
    effort: any failure leaves runs untouched rather than breaking the thread.
    """
    run_ids = [r["id"] for r in runs if r.get("id")]
    if not run_ids:
        return runs
    try:
        decisions = (
            tenant_table(db, "os_routing_decision", client_id)
            .select("run_id, classifier, chosen_agent, confidence, decision, alternates")
            .in_("run_id", run_ids)
            .execute()
        )
        calls = (
            tenant_table(db, "os_model_call_log", client_id)
            .select("run_id, model")
            .eq("purpose", "routing")
            .in_("run_id", run_ids)
            .execute()
        )
    except Exception:
        logger.warning("os_threads: routing attach failed", exc_info=True)
        return runs

    decision_by_run: dict = {}
    for d in decisions.data or []:
        decision_by_run.setdefault(d.get("run_id"), d)
    model_by_run: dict = {}
    for c in calls.data or []:
        model_by_run.setdefault(c.get("run_id"), c.get("model"))

    out = []
    for r in runs:
        dec = decision_by_run.get(r.get("id"))
        if dec:
            r = {
                **r,
                "routing": {
                    "classifier": dec.get("classifier"),
                    "chosen_agent": dec.get("chosen_agent"),
                    "confidence": dec.get("confidence"),
                    "decision": dec.get("decision"),
                    "alternates": dec.get("alternates"),
                    "model": model_by_run.get(r.get("id")),
                },
            }
        out.append(r)
    return out


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
    user_message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": thread_id, "role": "user", "content": user_content})
        .execute()
        .data[0]
    )
    usage_meter.record_message(db, client_id)

    return await process_user_turn(
        db, client_id, thread_id, user_message, background_tasks
    )


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
