"""Shared orchestration runner for Agent OS threads.

Extracted from ``backend/routers/os_threads.py::post_message`` so the
chat-shell router AND the inbound-channel bridges
(``backend/services/os_inbound_bridge.py``) drive the same orchestrator +
worker pipeline. The bridge fan-in is the reason this exists: when a
widget/email/SMS/Facebook message lands in an ``os_thread``, the same
orchestrate -> answer/delegate/backlog routing has to fire as if the
owner typed it in the chat shell.

Single source of truth for one user-turn:
1. Pull thread history.
2. Run the orchestrator.
3. Record any orchestrator-detected memory writes.
4. Persist the resulting assistant turn (delegate -> create agent_run row,
   answer -> assistant message, backlog -> backlog row + notify).
5. Bump thread updated_at.

Contract: ``user_message_row`` is already inserted into ``os_messages``
before this runs. Caller owns insertion because inbound bridges need
``inbound_kind`` + ``source_ref`` set at insert time.
"""

import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks

from backend.services import orchestrator, os_workers
from backend.services.email_sender import send_email
from backend.services.os_outbound_mirror import mirror_assistant_message
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_user_turn(
    db,
    client_id: str,
    thread_id: str,
    user_message_row: dict,
    background_tasks: BackgroundTasks | None,
) -> dict:
    """Run one orchestrator turn for a thread.

    Caller (router OR inbound bridge) must have already inserted the user
    message row. Returns the same shape that the chat-shell router returns
    today so the public POST /threads/{id}/messages response stays
    backwards-compatible.

    ``background_tasks=None`` is allowed for fully-background callers
    (e.g. inbound bridges already running inside a BackgroundTask) — in
    that case worker runs execute inline. The router passes the live
    BackgroundTasks instance.
    """
    user_content = user_message_row["content"]

    history_rows = (
        tenant_table(db, "os_messages", client_id)
        .select("role, content")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    ).data or []
    # The just-inserted user message is in history; orchestrator expects
    # prior turns only.
    history = [
        row
        for row in history_rows
        if row.get("content") != user_content or row.get("role") != "user"
    ]

    decision = await orchestrator.orchestrate(
        db, client_id, user_content, history=history
    )
    if decision.memory_writes:
        await orchestrator.record_memory_writes(
            db, client_id, decision.memory_writes, source=f"thread:{thread_id}"
        )

    messages_tbl = tenant_table(db, "os_messages", client_id)
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
        if background_tasks is not None:
            background_tasks.add_task(
                os_workers.run_worker,
                run["id"],
                client_id,
                thread_id,
                decision.agent_name,
                user_content,
                decision.deliverable_title or "Draft",
            )
        else:
            # Bridge path: already inside a background task. Run inline so
            # the worker completes before this function returns.
            await os_workers.run_worker(
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

    await _mirror_to_channel(db, client_id, thread_id, assistant_message)

    tenant_table(db, "os_threads", client_id).update({"updated_at": _now()}).eq(
        "id", thread_id
    ).execute()

    return {
        "user_message": user_message_row,
        "assistant_message": assistant_message,
        "action": decision.action,
        "agent_runs": agent_runs,
    }


async def _mirror_to_channel(
    db, client_id: str, thread_id: str, assistant_message: dict
) -> None:
    """Best-effort Group C bi-directional sync.

    Reads the thread's inbound source (widget/email/sms/facebook) and mirrors
    the assistant reply back into the originating channel store so the
    customer actually sees it. Never raises — OS reply is already persisted
    in os_messages regardless of mirror outcome.
    """
    try:
        thread_resp = (
            tenant_table(db, "os_threads", client_id)
            .select("id, source, source_metadata, source_thread_id")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        thread_rows = getattr(thread_resp, "data", None) or []
        if not thread_rows:
            return
        result = await mirror_assistant_message(
            db, client_id, thread_rows[0], assistant_message
        )
        status = result.get("status", "")
        if status.startswith("error:"):
            logger.warning(
                "os_outbound_mirror: client_id=%s thread=%s status=%s",
                client_id,
                thread_id,
                status,
            )
    except Exception:
        logger.warning(
            "os_outbound_mirror: unexpected failure client_id=%s thread=%s",
            client_id,
            thread_id,
            exc_info=True,
        )


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
