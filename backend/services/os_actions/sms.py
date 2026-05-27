"""Agent OS action handler: sms.send.

Fires after a lead-nurture or booking deliverable that should reach the
recipient by SMS is approved. Extracts a structured SMS payload (to, body)
from the approved deliverable via a cheap Haiku call, then dispatches to
the right Twilio account for this tenant:

* Tenant has a ``twilio_byo`` integration row -> ``twilio_tenant
  .send_sms_via_tenant`` (per-tenant Twilio subaccount + phone, 10DLC /
  branded-sender setup).
* Otherwise -> the platform-wide pool via ``twilio_service.send_sms``
  (shared ``TWILIO_ACCOUNT_SID`` / ``TWILIO_AUTH_TOKEN`` /
  ``TWILIO_PHONE_NUMBER`` env vars).

Mirrors the runtime-dispatch shape of ``email.send`` (M365 vs Resend) and
``calendar.event.create`` (M365 vs Google): single ``sms.send`` action
type, provider chosen per-run based on the tenant's integration row.
"""

import json
import logging
import re

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec
from backend.services.twilio_service import send_sms
from backend.services.twilio_tenant import is_connected as twilio_is_connected
from backend.services.twilio_tenant import send_sms_via_tenant

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


def _pick_provider(client_id: str) -> str:
    """Return the Twilio provider to dispatch on for this tenant.

    Preference order: ``twilio_byo`` -> ``twilio_platform``. BYO is per-tenant
    (own subaccount, branded sender, 10DLC compliance); platform is the shared
    pool. Stable order keeps existing platform-only tenants behaving exactly
    as before.
    """
    try:
        if twilio_is_connected(client_id):
            return "twilio_byo"
    except Exception:
        logger.warning(
            "os_action_sms: twilio_byo connectivity lookup failed client_id=%s",
            client_id,
            exc_info=True,
        )
    return "twilio_platform"


async def _send_via_twilio_byo(
    client_id: str,
    to: str,
    sms_body: str,
    request_payload: dict,
) -> ActionResult:
    try:
        result = await send_sms_via_tenant(
            tenant_id=client_id,
            to=to,
            body=sms_body,
        )
    except Exception as e:
        logger.exception(
            "os_action_sms: twilio_byo send raised client_id=%s", client_id
        )
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "twilio_byo", "message": str(e)[:300]},
        )

    if not result.get("success"):
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "twilio_byo",
                "message": result.get("detail") or "twilio_byo send reported failure",
            },
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={
            "provider": "twilio_byo",
            "message_sid": result.get("message_sid", ""),
            "detail": result.get("detail", "sent"),
        },
    )


async def _send_via_twilio_platform(
    client_id: str,
    to: str,
    sms_body: str,
    request_payload: dict,
) -> ActionResult:
    try:
        sent = await send_sms(to=to, body=sms_body)
    except Exception as e:
        logger.exception("os_action_sms: send_sms raised client_id=%s", client_id)
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
        response_payload={"provider": "twilio_platform", "detail": "sent"},
    )


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

    provider = _pick_provider(ctx.client_id)
    request_payload = {"to": to, "body": sms_body, "provider": provider}

    if provider == "twilio_byo":
        return await _send_via_twilio_byo(ctx.client_id, to, sms_body, request_payload)
    return await _send_via_twilio_platform(ctx.client_id, to, sms_body, request_payload)


SPEC = ActionSpec(
    name="sms.send",
    worker="lead_nurture",
    run=_run,
    required_connectors=[],
    description=(
        "Send a follow-up SMS from an approved deliverable. Dispatches to the "
        "tenant's own Twilio subaccount when twilio_byo integration exists; "
        "otherwise falls back to the platform Twilio pool."
    ),
)
