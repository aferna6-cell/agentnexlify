"""Shared orchestration runner for Agent OS threads — engine-only (Phase 4).

The chat-shell router (``backend/routers/os_threads.py``), the orchestrate
endpoint, and the inbound-channel bridges
(``backend/services/os_inbound_bridge.py``) all drive one user-turn through
the same path: assemble the tenant's SharedContext, run the vendored Agent OS
engine in agent-service, persist the result into ``os_*``, mirror the reply
to the originating channel.

The legacy Python orchestrator + ``os_workers`` layer is retired (Phase 4 of
``plans/agent-os-demo-merge_plan.md``). When the engine is unconfigured or
unreachable the turn degrades honestly: the user message is already saved,
and the assistant replies that agents are temporarily offline — no silent
re-route through stale code, never a 503.

Contract: ``user_message_row`` is already inserted into ``os_messages``
before this runs. Caller owns insertion because inbound bridges need
``inbound_kind`` + ``source_ref`` set at insert time.
"""

import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from backend.services import agent_os_bridge, agent_sdk_client, os_graph_memory
from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.os_outbound_mirror import mirror_assistant_message
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

ENGINE_OFFLINE_REPLY = (
    "Your message is saved, but the agent engine is temporarily unavailable. "
    "We'll pick this up as soon as it's back — no need to resend."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_user_turn(
    db,
    client_id: str,
    thread_id: str,
    user_message_row: dict,
    background_tasks: BackgroundTasks | None,
    force_agent_id: str | None = None,
) -> dict:
    """Run one engine turn for a thread.

    Caller (router OR inbound bridge) must have already inserted the user
    message row. Returns the same shape the chat-shell router has always
    returned, so POST /threads/{id}/messages stays backwards-compatible.

    ``background_tasks=None`` is allowed for fully-background callers
    (e.g. inbound bridges already running inside a BackgroundTask) — in
    that case any auto-send action handler runs inline.
    """
    user_content = user_message_row["content"]

    out = None
    business_name = ""
    if agent_sdk_client.is_configured():
        context = agent_os_bridge.assemble_shared_context(db, client_id)
        business_name = (context.get("businessProfile") or {}).get("businessName") or ""
        # Long-term memory rides in as KbEntry rows — the engine's agents
        # already consume SharedContext.kb, so no engine change is needed.
        context["kb"] = await os_graph_memory.graph_kb_entries(
            db, client_id, user_content
        )
        out = await run_in_threadpool(
            agent_sdk_client.orchestrate_sync,
            client_id,
            user_content,
            context,
            force_agent_id=force_agent_id,
        )

    if out is None:
        return await _degrade_offline(db, client_id, thread_id, user_message_row)

    persisted = agent_os_bridge.persist_orchestration(db, client_id, thread_id, out)
    assistant_message = persisted.get("assistant_message")
    if assistant_message:
        await _mirror_to_channel(db, client_id, thread_id, assistant_message)

    agent_run = persisted.get("agent_run")
    await _dispatch_auto_send(db, client_id, agent_run, background_tasks)

    # Knowledge-graph accumulation AFTER the reply is persisted — memory
    # never adds latency to the conversation and never breaks a turn.
    assistant_text = (assistant_message or {}).get("content")
    if background_tasks is not None:
        background_tasks.add_task(
            os_graph_memory.accumulate_background,
            client_id,
            user_content,
            assistant_text,
            f"thread:{thread_id}",
            business_name,
        )
    else:
        await os_graph_memory.accumulate_background(
            client_id, user_content, assistant_text, f"thread:{thread_id}", business_name
        )

    return {
        "user_message": user_message_row,
        "assistant_message": assistant_message,
        "action": "delegate" if agent_run else "answer",
        "agent_runs": [agent_run] if agent_run else [],
    }


async def _degrade_offline(
    db, client_id: str, thread_id: str, user_message_row: dict
) -> dict:
    """Honest fallback when agent-service is unconfigured or unreachable.

    The user message is already persisted; reply that agents are offline,
    mirror that reply to the originating channel, bump the thread. The next
    turn retries the engine — nothing is lost, nothing silently re-routes.
    """
    logger.warning(
        "agent engine unavailable: client_id=%s thread=%s configured=%s",
        client_id,
        thread_id,
        agent_sdk_client.is_configured(),
    )
    assistant_message = (
        tenant_table(db, "os_messages", client_id)
        .insert(
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": ENGINE_OFFLINE_REPLY,
            }
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
        "action": "answer",
        "agent_runs": [],
    }


async def _dispatch_auto_send(
    db, client_id: str, agent_run: dict | None, background_tasks: BackgroundTasks | None
) -> None:
    """Fire the action handler for a tenant-opted auto-approved run.

    ``persist_orchestration`` only marks a run approved when the engine said
    no approval is needed AND the tenant opted in (``os_auto_send_enabled``)
    AND the agent is outside the never-auto-send set. Everything else stays
    pending and fires through the owner's Approve button instead.
    """
    if not agent_run:
        return
    if agent_run.get("deliverable_status") != "approved":
        return
    if not agent_run.get("action_type"):
        return
    try:
        await queue_action_for_run(db, client_id, agent_run, background_tasks)
    except Exception:
        logger.warning(
            "auto-send dispatch failed run_id=%s", agent_run.get("id"), exc_info=True
        )


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
