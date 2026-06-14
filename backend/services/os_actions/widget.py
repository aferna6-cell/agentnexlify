"""Agent OS action handler: widget.message.

Posts an assistant message back into a widget chat session after the owner
approves a customer-question deliverable. The session_id is read from the
agent_run row (orchestrator persists it on the os_thread when a widget
session triggered the run).

Required connectors: none — writes directly to ``chat_messages``.
"""

import logging

from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec
from backend.services.tenant_scope import tenant_insert

logger = logging.getLogger(__name__)

_MAX_CONTENT_LEN = 4000


def _resolve_session_id(ctx: ActionContext) -> str | None:
    """Find the widget session_id this action targets.

    Looks in (priority): deliverable.session_id, deliverable.metadata.session_id,
    agent_run.thread_metadata.session_id, agent_run.context.session_id.
    """
    deliv = ctx.deliverable or {}
    sid = deliv.get("session_id")
    if sid:
        return str(sid)
    meta = deliv.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("session_id"):
        return str(meta["session_id"])
    run = ctx.agent_run or {}
    for key in ("thread_metadata", "context", "input_context"):
        blob = run.get(key)
        if isinstance(blob, dict) and blob.get("session_id"):
            return str(blob["session_id"])
    return None


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    if not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

    session_id = _resolve_session_id(ctx)
    if not session_id:
        return ActionResult(
            status="failed",
            error_detail={
                "stage": "validate",
                "message": "no session_id on deliverable or agent_run — cannot route reply",
            },
        )

    content = body[:_MAX_CONTENT_LEN]
    request_payload = {"session_id": session_id, "content": content}

    try:
        result = tenant_insert(
            ctx.db,
            "chat_messages",
            ctx.client_id,
            {
                "tenant_id": ctx.client_id,
                "session_id": session_id,
                "role": "assistant",
                "content": content,
            },
        ).execute()
    except Exception as e:
        logger.exception(
            "os_action_widget: insert failed client_id=%s session_id=%s",
            ctx.client_id,
            session_id,
        )
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "insert", "message": str(e)[:300]},
        )

    rows = result.data or []
    message_id = rows[0].get("id") if rows else None
    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"message_id": message_id},
    )


SPEC = ActionSpec(
    name="widget.message",
    worker="customer_question",
    run=_run,
    required_connectors=[],
    description="Post an assistant reply into a widget chat session.",
)
