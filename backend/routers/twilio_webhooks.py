"""Twilio webhook endpoints — missed call text-back and inbound SMS handling.

When a call goes unanswered, Twilio hits our missed-call webhook.
We auto-text the caller and track the SMS conversation.
"""

import hashlib
import hmac
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.services.activity import log_activity
from backend.services.twilio_service import format_textback_message, send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twilio", tags=["twilio-webhooks"])

# Default text-back message
DEFAULT_TEXTBACK = (
    "Hi! Sorry we missed your call at {business_name}. "
    "How can we help? Reply here and we'll get back to you right away."
)


def _verify_twilio_signature(request: Request, body: bytes) -> bool:
    """Verify Twilio webhook signature (X-Twilio-Signature header)."""
    if not settings.twilio_auth_token:
        return False
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False
    url = str(request.url)
    # Twilio computes HMAC-SHA1 over URL + sorted POST params
    try:
        params = dict(x.split("=", 1) for x in body.decode().split("&") if "=" in x)
        from urllib.parse import unquote_plus
        params = {k: unquote_plus(v) for k, v in params.items()}
    except Exception:
        params = {}
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    expected = hmac.new(
        settings.twilio_auth_token.encode(),
        data.encode(),
        hashlib.sha1,
    ).digest()
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(signature, expected_b64)


def _find_tenant_by_phone(phone: str) -> dict | None:
    """Look up tenant by their configured notification_phone or Twilio number."""
    db = get_supabase()
    result = (
        db.table("tenants")
        .select("id, business_name, notification_phone, sms_notifications_enabled, plan, textback_enabled, textback_message, textback_quiet_start, textback_quiet_end")
        .eq("sms_notifications_enabled", True)
        .limit(50)
        .execute()
    )
    for tenant in (result.data or []):
        if tenant.get("notification_phone"):
            # Normalize for comparison (strip spaces, dashes)
            norm_tenant = tenant["notification_phone"].replace(" ", "").replace("-", "")
            norm_phone = phone.replace(" ", "").replace("-", "")
            if norm_tenant.endswith(norm_phone[-10:]) or norm_phone.endswith(norm_tenant[-10:]):
                return tenant
    return None


@router.post("/missed-call")
@limiter.limit("30/minute")
async def handle_missed_call(request: Request):
    """Twilio voice webhook — triggered when a call goes unanswered.

    Sends an auto text-back to the caller with the business greeting.
    Creates a lead if the caller isn't already in the system.
    """
    body = await request.body()

    # Parse form data
    try:
        from urllib.parse import parse_qs
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    caller = params.get("From", "")
    called = params.get("To", "")
    call_status = params.get("CallStatus", "")

    if not caller:
        return PlainTextResponse("OK")

    # Only handle missed/no-answer calls
    if call_status not in ("no-answer", "busy", "failed", "canceled"):
        return PlainTextResponse("OK")

    logger.info("Missed call from %s to %s (status: %s)", caller, called, call_status)

    # Find the tenant this call was for
    tenant = _find_tenant_by_phone(called)
    if not tenant:
        logger.warning("Missed call to %s — no matching tenant found", called)
        return PlainTextResponse("OK")

    business_name = tenant.get("business_name", "us")
    tenant_id = tenant["id"]

    # Check if text-back is enabled for this tenant
    if not tenant.get("textback_enabled", False):
        logger.info("Text-back disabled for tenant %s, skipping", tenant_id)
        return PlainTextResponse("OK")

    # Check quiet hours
    quiet_start = tenant.get("textback_quiet_start")  # e.g. "22:00"
    quiet_end = tenant.get("textback_quiet_end")  # e.g. "07:00"
    if quiet_start and quiet_end:
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        hour_now = now_utc.hour * 100 + now_utc.minute
        try:
            qs = int(quiet_start.replace(":", ""))
            qe = int(quiet_end.replace(":", ""))
            if qs > qe:  # Overnight quiet hours (e.g., 22:00 - 07:00)
                if hour_now >= qs or hour_now < qe:
                    logger.info("Quiet hours active for tenant %s (%s-%s), skipping text-back", tenant_id, quiet_start, quiet_end)
                    return PlainTextResponse("OK")
            elif qs <= hour_now < qe:
                logger.info("Quiet hours active for tenant %s, skipping text-back", tenant_id)
                return PlainTextResponse("OK")
        except ValueError:
            pass  # Malformed quiet hours, proceed with text-back

    # Send text-back using custom message or default
    custom_msg = tenant.get("textback_message")
    template = custom_msg if custom_msg and custom_msg.strip() else DEFAULT_TEXTBACK
    message = format_textback_message(template, business_name)
    sent = await send_sms(to=caller, body=message)

    if sent:
        logger.info("Text-back sent to %s for tenant %s", caller, tenant_id)

        # Log the missed call + text-back
        log_activity(
            tenant_id=tenant_id,
            activity_type="missed_call_textback",
            description=f"Missed call from {caller} — auto text-back sent",
            metadata={"caller": caller, "called": called, "status": call_status},
        )

        # Create/update lead from caller phone
        db = get_supabase()
        existing = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("phone", caller)
            .limit(1)
            .execute()
        )
        if not existing.data:
            db.table("leads").insert({
                "client_id": tenant_id,
                "phone": caller,
                "status": "new",
                "areas_of_interest": "missed call — text-back sent",
            }).execute()
            logger.info("Created lead from missed call: %s for tenant %s", caller, tenant_id)

    return PlainTextResponse("OK")


@router.post("/sms-reply")
@limiter.limit("60/minute")
async def handle_inbound_sms(request: Request):
    """Twilio messaging webhook — handles inbound SMS replies.

    When a caller replies to a text-back, route the message to the
    AI chat engine and send the AI's response back via SMS.
    """
    body = await request.body()

    try:
        from urllib.parse import parse_qs
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    from_number = params.get("From", "")
    to_number = params.get("To", "")
    message_body = params.get("Body", "").strip()

    if not from_number or not message_body:
        return PlainTextResponse("OK")

    logger.info("Inbound SMS from %s: %s", from_number, message_body[:100])

    # Find tenant
    tenant = _find_tenant_by_phone(to_number)
    if not tenant:
        logger.warning("Inbound SMS to %s — no matching tenant", to_number)
        return PlainTextResponse("OK")

    tenant_id = tenant["id"]
    db = get_supabase()

    # Use phone number as session ID for SMS conversations
    session_id = f"sms_{from_number.replace('+', '').replace(' ', '')}"

    # Save inbound message
    db.table("chat_messages").insert({
        "tenant_id": tenant_id,
        "session_id": session_id,
        "role": "user",
        "content": message_body,
    }).execute()

    # Generate AI response using the same chat engine
    try:
        import anthropic
        from backend.routers.widget_helpers import _build_system_prompt, _load_chat_history

        # Load context
        history = _load_chat_history(tenant_id, session_id, limit=10)
        faq_data = []
        try:
            faq_result = db.table("faq_entries").select("question, answer").eq("tenant_id", tenant_id).eq("is_active", True).execute()
            faq_data = faq_result.data or []
        except Exception:
            logger.warning("FAQ load failed for SMS reply, tenant %s", tenant_id, exc_info=True)

        system_prompt = _build_system_prompt(tenant, faq_data)

        # Build messages for Claude
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": message_body})

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,  # Shorter for SMS
            system=system_prompt + "\n\nIMPORTANT: This conversation is via SMS. Keep responses SHORT (under 160 characters if possible). Be concise.",
            messages=messages,
        )
        ai_response = resp.content[0].text.strip()

        # Truncate for SMS
        if len(ai_response) > 1500:
            ai_response = ai_response[:1497] + "..."

    except Exception:
        logger.exception("AI response generation failed for SMS from %s", from_number)
        ai_response = f"Thanks for your message! Someone from {tenant.get('business_name', 'our team')} will get back to you shortly."

    # Save AI response
    db.table("chat_messages").insert({
        "tenant_id": tenant_id,
        "session_id": session_id,
        "role": "assistant",
        "content": ai_response,
    }).execute()

    # Send AI response via SMS
    await send_sms(to=from_number, body=ai_response)

    # Log activity
    log_activity(
        tenant_id=tenant_id,
        activity_type="sms_conversation",
        description=f"SMS from {from_number}: {message_body[:50]}",
        metadata={"phone": from_number, "session_id": session_id},
    )

    return PlainTextResponse("OK")
