"""Agent OS action handler: email.send.

Fires after a lead-nurture or follow-up deliverable is approved. Extracts a
structured email payload (to, subject, body_html) from the approved
deliverable via a cheap Haiku call, then sends through the right provider
for this tenant:

* M365 connected -> ``m365_mail.send_email_via_graph`` (Mail.Send scope from
  the same OAuth consent that ships calendar event creation). Outbound mail
  flows from the tenant's own Outlook mailbox.
* Otherwise -> the existing Resend pipeline in
  ``backend.services.email_sender`` (platform-wide ``RESEND_API_KEY``).

Provider selection mirrors the calendar action's "runtime dispatch inside
one action" decision: single ``email.send`` action_type, branch chosen at
run time based on which integration row exists for the tenant.
"""

import json
import logging
import re

from backend.services.email_sender import send_email
from backend.services.llm_runtime import call_claude_messages
from backend.services.m365_mail import is_connected as m365_is_connected
from backend.services.m365_mail import send_email_via_graph as m365_send_email_via_graph
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You extract an email payload from an approved follow-up message.
Return STRICT JSON with these keys:
- to (string, recipient email)
- subject (string, short, no markdown)
- body_html (string, valid HTML — wrap plain text in <p> tags)

If recipient is missing, return {"error": "missing recipient"}. If the body
is only plain text, wrap each paragraph in <p>...</p>. Do not invent a
recipient address.\
"""

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _parse_json_block(text: str) -> dict | None:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.+?)```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def _extract_email_payload(body: str, client_id: str) -> dict:
    response = await call_claude_messages(
        operation="os_action_email_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Approved follow-up message:\n\n{body}",
            }
        ],
        metadata={"client_id": client_id},
    )
    return _parse_json_block(response.text) or {}


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    if not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

    try:
        payload = await _extract_email_payload(body, ctx.client_id)
    except Exception as e:
        logger.warning(
            "os_action_email: extraction failed client_id=%s deliverable_id=%s",
            ctx.client_id,
            ctx.deliverable_id,
            exc_info=True,
        )
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": str(e)[:300]},
        )

    if "error" in payload:
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": payload["error"]},
        )

    to = (payload.get("to") or "").strip()
    subject = (payload.get("subject") or "").strip() or "Following up"
    body_html = payload.get("body_html") or ""

    if not to or not _EMAIL_RE.match(to):
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={
                "stage": "validate",
                "message": "missing or invalid recipient",
            },
        )
    if not body_html.strip():
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "empty body_html"},
        )

    request_payload = {"to": to, "subject": subject, "body_html": body_html}

    provider = _pick_provider(ctx.client_id)
    request_payload["provider"] = provider

    if provider == "m365":
        return await _send_via_m365(
            ctx.client_id, to, subject, body_html, request_payload
        )
    return await _send_via_resend(
        ctx.client_id, to, subject, body_html, request_payload
    )


def _pick_provider(client_id: str) -> str:
    """Return the email provider to dispatch on for this tenant.

    Preference order: ``m365`` -> ``resend``. M365 is per-tenant and uses the
    tenant's own Outlook mailbox; Resend is the platform-wide fallback. Stable
    order keeps existing Resend-only tenants behaving exactly as before.
    """
    try:
        if m365_is_connected(client_id):
            return "m365"
    except Exception:
        logger.warning(
            "os_action_email: m365 connectivity lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
    return "resend"


async def _send_via_m365(
    client_id: str,
    to: str,
    subject: str,
    body_html: str,
    request_payload: dict,
) -> ActionResult:
    try:
        result = await m365_send_email_via_graph(
            tenant_id=client_id,
            to=to,
            subject=subject,
            body_html=body_html,
        )
    except Exception as e:
        logger.exception("os_action_email: m365 send raised client_id=%s", client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "m365", "message": str(e)[:300]},
        )

    if not result.get("success"):
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "m365",
                "message": result.get("detail") or "m365 send reported failure",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={
            "provider": "m365",
            "message_id": result.get("message_id", ""),
            "detail": result.get("detail", "sent"),
        },
    )


async def _send_via_resend(
    client_id: str,
    to: str,
    subject: str,
    body_html: str,
    request_payload: dict,
) -> ActionResult:
    try:
        result = await send_email(
            to=to,
            subject=subject,
            body_html=body_html,
            tenant_id=client_id,
        )
    except Exception as e:
        logger.exception("os_action_email: send_email raised client_id=%s", client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "resend", "message": str(e)[:300]},
        )

    if not result.get("success"):
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "resend",
                "message": result.get("detail") or "send_email reported failure",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={
            "provider": "resend",
            "resend_id": result.get("resend_id", ""),
            "detail": result.get("detail", "sent"),
        },
    )


SPEC = ActionSpec(
    name="email.send",
    worker="lead_nurture",
    run=_run,
    required_connectors=[],
    description=(
        "Send a follow-up email from an approved deliverable. Dispatches to "
        "M365 Graph when the tenant has an M365 integration; otherwise Resend."
    ),
)
