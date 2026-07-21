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

from backend.services import (
    agent_os_bridge,
    agent_sdk_client,
    connector_awareness,
    os_approval_notify,
    os_custom_instructions,
    os_failure_notify,
    os_mcp_context,
    os_graph_memory,
    os_kb_feed,
    os_routing_memory,
)
from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.os_outbound_mirror import mirror_assistant_message
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Threads originating from these channels are customer-facing - the person
# typing cannot connect the owner's integrations (os_inbound_bridge sources).
_INBOUND_THREAD_SOURCES = {"widget", "email", "sms", "facebook", "instagram"}

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

    # Connector-need inference (deterministic regex + status lookups on hit
    # only). When the ask needs an unconnected integration, the engine gets
    # told so its reply is grounded, and a follow-up connect prompt is posted
    # after the turn. Best-effort: never blocks or breaks the turn.
    missing_connectors: list[dict] = []
    try:
        # Threadpool: on an inference hit this runs up to 4 sequential
        # Supabase queries — off the event loop (audit 2026-07-14 M1).
        missing_connectors = await run_in_threadpool(
            connector_awareness.missing_for_message, db, client_id, user_content
        )
    except Exception:
        logger.warning(
            "connector_awareness failed client_id=%s", client_id, exc_info=True
        )

    out = None
    business_name = ""
    if agent_sdk_client.is_configured():
        context = agent_os_bridge.assemble_shared_context(db, client_id)
        profile = context.get("businessProfile") or {}
        business_name = profile.get("businessName") or ""
        # Knowledge rides in as KbEntry rows — the engine's agents already
        # consume SharedContext.kb, so no engine change is needed. Owner's
        # per-department instructions lead the feed (topics-lite), then static
        # business truth (vertical guidance + FAQs + website), then learned
        # memory (knowledge graph + semantic hits for this ask).
        context["kb"] = (
            os_custom_instructions.kb_entries(db, client_id)
            + os_mcp_context.kb_entries(db, client_id)
            + os_kb_feed.tenant_kb_entries(db, client_id, profile.get("businessType"))
            + await os_graph_memory.graph_kb_entries(db, client_id, user_content)
        )
        if missing_connectors:
            context["integrations"] = {
                "missing_for_this_request": [m["key"] for m in missing_connectors],
                "note": (
                    "These integrations are NOT connected yet, so do not claim "
                    "to have done anything through them. A connect prompt with "
                    "the setup link is shown to the owner after your reply."
                ),
            }
        # Routing memory v1: replay a standing owner correction for a
        # near-identical ask (strict similarity gate; explicit force wins).
        # Threadpool: one Supabase query on the no-force path.
        effective_force = await run_in_threadpool(
            os_routing_memory.resolve_force_agent,
            db,
            client_id,
            user_content,
            force_agent_id,
        )
        out = await run_in_threadpool(
            agent_sdk_client.orchestrate_sync,
            client_id,
            user_content,
            context,
            force_agent_id=effective_force,
        )

    if out is None:
        return await _degrade_offline(db, client_id, thread_id, user_message_row)

    persisted = agent_os_bridge.persist_orchestration(db, client_id, thread_id, out)
    assistant_message = persisted.get("assistant_message")
    if assistant_message:
        await _mirror_to_channel(db, client_id, thread_id, assistant_message)

    connect_message = await _post_connect_prompt(
        db, client_id, thread_id, missing_connectors
    )

    agent_run = persisted.get("agent_run")
    await _dispatch_auto_send(db, client_id, agent_run, background_tasks)

    # Owner notification when a draft is parked for approval — without it,
    # approvals rot until the owner happens to open the dashboard. Background
    # + best-effort: never adds latency to or breaks the turn.
    if agent_run and agent_run.get("deliverable_status") == "pending_approval":
        deliverable = agent_run.get("deliverable") or {}
        if background_tasks is not None:
            background_tasks.add_task(
                os_approval_notify.notify_pending_approval,
                db,
                client_id,
                agent_name=agent_run.get("agent_name") or "assistant",
                channel=deliverable.get("channel"),
                title=deliverable.get("title"),
            )
        else:
            await os_approval_notify.notify_pending_approval(
                db,
                client_id,
                agent_name=agent_run.get("agent_name") or "assistant",
                channel=deliverable.get("channel"),
                title=deliverable.get("title"),
            )

    # Platform-owner alert when the turn failed or abstained on a low-confidence
    # match. Background + best-effort, full transcript attached. Routine
    # clarification/declined-personal outcomes are intentionally not alerted.
    decision_status = persisted.get("status")
    run_status = (agent_run or {}).get("status")
    alert_reason = None
    if run_status == "failed":
        alert_reason = "failed"
    elif decision_status == "wishlist_fallback":
        alert_reason = "wishlist_fallback"
    if alert_reason:
        if background_tasks is not None:
            background_tasks.add_task(
                os_failure_notify.notify_agent_failure,
                db,
                client_id,
                thread_id,
                alert_reason,
                business_name,
            )
        else:
            await os_failure_notify.notify_agent_failure(
                db, client_id, thread_id, alert_reason, business_name
            )

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
        "followup_messages": [connect_message] if connect_message else [],
        # Routing outcome for the UI: when status is "needs_clarification" the
        # picker offers clarify_between as one-click re-route buttons.
        "status": decision_status,
        "clarify_between": persisted.get("clarify_between") or [],
        "decision_id": persisted.get("decision_id"),
    }


async def _post_connect_prompt(
    db, client_id: str, thread_id: str, missing_connectors: list[dict]
) -> dict | None:
    """Post the "connect X to do this for real" follow-up message.

    Only for owner-facing threads: inbound-channel threads (widget / email /
    SMS / Facebook) belong to the END CUSTOMER, who cannot connect the
    owner's integrations. Dashboard threads carry the DEFAULT source 'chat'
    (os_threads.source is NOT NULL DEFAULT 'chat', migration 124) - so the
    check is an inbound denylist, not "any source set". One nudge per
    connector per thread (dedup on the connect path in prior assistant
    messages). Best-effort - never raises into the turn.
    """
    if not missing_connectors:
        return None
    try:
        thread_rows = (
            tenant_table(db, "os_threads", client_id)
            .select("id, source")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        ).data or []
        if not thread_rows:
            return None
        source = thread_rows[0].get("source") or "chat"
        if source in _INBOUND_THREAD_SOURCES:
            return None

        prior = (
            tenant_table(db, "os_messages", client_id)
            .select("role, content")
            .eq("thread_id", thread_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        ).data or []
        fresh = connector_awareness.already_prompted(prior, missing_connectors)
        if not fresh:
            return None

        return (
            tenant_table(db, "os_messages", client_id)
            .insert(
                {
                    "thread_id": thread_id,
                    "role": "assistant",
                    "content": connector_awareness.connect_prompt(fresh),
                }
            )
            .execute()
            .data[0]
        )
    except Exception:
        logger.warning(
            "connect prompt failed client_id=%s thread=%s",
            client_id,
            thread_id,
            exc_info=True,
        )
        return None


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
    # Engine-offline is a hard failure to answer — alert the platform owner.
    await os_failure_notify.notify_agent_failure(db, client_id, thread_id, "offline")
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
