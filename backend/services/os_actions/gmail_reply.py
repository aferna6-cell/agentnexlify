"""Agent OS action handler: gmail.reply.

Fires when an inbox-triage draft reply is approved from the dashboard
(``POST /api/v1/os/deliverables/{run_id}/approve``). The draft was written
by ``backend.services.inbox_triage`` with a fully structured payload in the
deliverable metadata (gmail_thread_id, to, subject, in_reply_to,
references) — no LLM extraction pass is needed here, unlike email.send.
Sends through the tenant's own Gmail via ``gmail_connector.send_reply`` so
the reply lands in the original thread.
"""

import logging

from backend.services import gmail_connector
from backend.services.inbox_triage import _body_to_html
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec

logger = logging.getLogger(__name__)


async def _run(ctx: ActionContext) -> ActionResult:
    deliverable = ctx.deliverable or {}
    metadata = deliverable.get("metadata") or {}
    to = (metadata.get("to") or "").strip()
    thread_id = metadata.get("gmail_thread_id") or ""
    subject = metadata.get("subject") or ""
    body = deliverable.get("body") or ""

    request_payload = {
        "to": to,
        "gmail_thread_id": thread_id,
        "subject": subject,
    }

    if not to or not thread_id or not body:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "validate",
                "message": "draft is missing to/gmail_thread_id/body",
            },
        )

    if not gmail_connector.is_connected(ctx.client_id):
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "gmail",
                "message": "Gmail is not connected for this tenant",
            },
        )

    try:
        result = gmail_connector.send_reply(
            ctx.db,
            ctx.client_id,
            thread_id=thread_id,
            to=to,
            subject=subject,
            body_html=_body_to_html(body),
            in_reply_to=metadata.get("in_reply_to"),
            references=metadata.get("references"),
        )
    except Exception as e:
        logger.exception(
            "os_action_gmail_reply: send_reply raised client_id=%s", ctx.client_id
        )
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "gmail", "message": str(e)[:300]},
        )

    if not result.get("success"):
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "gmail",
                "message": result.get("detail") or "send_reply reported failure",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={
            "provider": "gmail",
            "message_id": result.get("message_id", ""),
            "detail": result.get("detail", "sent"),
        },
    )


SPEC = ActionSpec(
    name="gmail.reply",
    worker="inbox_triage",
    run=_run,
    required_connectors=["gmail"],
    description=(
        "Send an approved inbox-triage draft reply through the tenant's "
        "connected Gmail, threading into the original conversation."
    ),
)
