"""Agent OS action handler: sms.send.

Fires after a lead-nurture or booking deliverable that should reach the
recipient by SMS is approved. Extracts a structured SMS payload (to, body)
from the approved deliverable via a cheap Haiku call, then sends through
the existing Twilio pipeline in ``backend.services.twilio_service``.

Required connectors: none — Twilio is platform-wide via
``TWILIO_ACCOUNT_SID`` / ``TWILIO_AUTH_TOKEN`` / ``TWILIO_PHONE_NUMBER``.
If credentials are missing, ``send_sms`` returns False and this handler
records a failed run with that detail.
"""

import json
import logging
import re

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You extract an SMS payload from an approved follow-up message.
Return STRICT JSON with these keys:
- to (string, recipient phone in E.164 format, e.g. "+15555550123")
- body (string, plain text, no HTML, max 1600 chars)

If recipient is missing or cannot be parsed to E.164, return
{"error": "missing recipient"}. Never invent a phone number.\
"""

# Loose E.164 check — leading +, 8-15 digits. Twilio enforces full validation.
_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


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


async def _extract_sms_payload(body: str, client_id: str) -> dict:
    response = await call_claude_messages(
        operation="os_action_sms_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
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
        payload = await _extract_sms_payload(body, ctx.client_id)
    except Exception as e:
        logger.warning(
            "os_action_sms: extraction failed client_id=%s deliverable_id=%s",
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
    sms_body = (payload.get("body") or "").strip()

    if not to or not _PHONE_RE.match(to):
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={
                "stage": "validate",
                "message": "missing or invalid recipient (E.164 required)",
            },
        )
    if not sms_body:
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "empty sms body"},
        )

    request_payload = {"to": to, "body": sms_body}

    try:
        sent = await send_sms(to=to, body=sms_body)
    except Exception as e:
        logger.exception("os_action_sms: send_sms raised client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "twilio", "message": str(e)[:300]},
        )

    if not sent:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "twilio",
                "message": "send_sms reported failure (credentials missing or Twilio error)",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"detail": "sent"},
    )


SPEC = ActionSpec(
    name="sms.send",
    worker="lead_nurture",
    run=_run,
    required_connectors=[],
    description="Send a follow-up SMS via Twilio from an approved deliverable.",
)
