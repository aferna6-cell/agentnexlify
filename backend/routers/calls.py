"""AI Answering Service — voice call handling and call management endpoints.

Twilio voice webhooks for incoming calls (greeting + recording + AI conversation),
transcription pipeline, AI summary generation, and action item extraction,
plus dashboard endpoints for listing, viewing, and aggregating call data.
"""

import json
import logging
import re
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.automations import verify_twilio_request

logger = logging.getLogger(__name__)

# Max AI conversation rounds before ending the call
_MAX_VOICE_ROUNDS = 3

# Live AI answering is the Professional-tier feature ("AI answering service").
# Lower tiers get voicemail mode (recording -> transcription -> recovery draft).
_AI_VOICE_PLANS = {"professional", "enterprise"}


def _ai_voice_mode(tenant: dict) -> bool:
    """True when this tenant's calls get the live AI loop instead of voicemail."""
    return bool(tenant.get("voice_ai_enabled")) and (
        (tenant.get("plan") or "free") in _AI_VOICE_PLANS
    )


def _find_or_create_lead(db, tenant_id: str, caller: str, note: str) -> str | None:
    """Find lead by caller phone or create one. None on failure (never raises)."""
    try:
        existing = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("phone", caller)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]["id"]
        created = (
            db.table("leads")
            .insert(
                {
                    "client_id": tenant_id,
                    "phone": caller,
                    "status": "new",
                    "areas_of_interest": note,
                }
            )
            .execute()
        )
        return created.data[0]["id"] if created.data else None
    except Exception:
        logger.exception(
            "Failed to find/create lead for caller tenant=%s", tenant_id
        )
        return None

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])


# ---------------------------------------------------------------------------
# Pydantic models — field names match the `calls` table columns (migration 044)
# ---------------------------------------------------------------------------


class CallOut(BaseModel):
    id: str
    tenant_id: str
    lead_id: str | None = None
    caller_phone: str
    called_number: str | None = None
    direction: str = "inbound"
    duration_seconds: int = 0
    status: str = "completed"
    recording_url: str | None = None
    transcript: list[dict[str, Any]] | None = Field(default_factory=list)
    summary: str | None = None
    sentiment: str | None = None
    action_taken: str | None = None
    twilio_call_sid: str | None = None
    created_at: str | None = None


class CallListResponse(BaseModel):
    calls: list[CallOut]
    total: int
    page: int
    per_page: int


class CallStatsResponse(BaseModel):
    total_calls: int = 0
    missed_calls: int = 0
    avg_duration_seconds: float = 0.0
    calls_today: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_tenant_by_phone(phone: str) -> dict | None:
    """Look up tenant by their configured notification_phone or Twilio number.

    Same pattern as twilio_webhooks.py._find_tenant_by_phone.
    """
    db = get_service_supabase()
    try:
        result = (
            db.table("tenants")
            .select(
                "id, business_name, business_type, owner_email, notification_phone, "
                "sms_notifications_enabled, plan, voice_ai_enabled"
            )
            .limit(50)
            .execute()
        )
    except Exception:
        logger.exception("Failed to query tenants for phone lookup: %s", phone)
        return None

    for tenant in result.data or []:
        tenant_phone = tenant.get("notification_phone")
        if not tenant_phone:
            continue
        # Normalize for comparison (strip spaces, dashes)
        norm_tenant = tenant_phone.replace(" ", "").replace("-", "")
        norm_phone = phone.replace(" ", "").replace("-", "")
        if norm_tenant.endswith(norm_phone[-10:]) or norm_phone.endswith(norm_tenant[-10:]):
            return tenant
    return None


def _build_twiml_greeting(
    business_name: str,
    recording_callback_url: str,
    transcription_callback_url: str | None = None,
) -> str:
    """Build a TwiML response that greets the caller and records their message.

    If transcription_callback_url is provided, the <Record> verb will include
    transcribe="true" and transcriptionUrl so Twilio sends the transcribed text
    back to our transcription-complete endpoint automatically.
    """
    # XML-escape the business name to prevent injection
    safe_name = (
        business_name
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    transcription_attrs = ""
    if transcription_callback_url:
        transcription_attrs = (
            ' transcribe="true"'
            f' transcriptionUrl="{transcription_callback_url}"'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Say voice=\"alice\">"
        f"Thanks for calling {safe_name}! "
        "We're not available right now, but your call is important to us. "
        "Please leave a message after the beep and we'll get back to you as soon as possible."
        "</Say>"
        "<Record"
        ' maxLength="120"'
        ' playBeep="true"'
        f' recordingStatusCallback="{recording_callback_url}"'
        ' recordingStatusCallbackMethod="POST"'
        f"{transcription_attrs}"
        " />"
        "<Say voice=\"alice\">We didn't receive a recording. Goodbye!</Say>"
        "</Response>"
    )


def _build_twiml_error() -> str:
    """Build a TwiML response for when we can't identify the tenant."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Say voice="alice">'
        "We're sorry, we're unable to take your call right now. Please try again later."
        "</Say>"
        "</Response>"
    )


def _build_twiml_gather(say_text: str, respond_url: str, round_num: int) -> str:
    """Build TwiML that speaks text and then gathers speech input.

    Uses <Gather> with speech input and a configurable action URL.
    After the gather timeout, falls back to a goodbye message.
    """
    safe_text = (
        say_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" timeout="5" speechTimeout="auto"'
        f' action="{respond_url}?round={round_num}" method="POST">'
        f'<Say voice="alice">{safe_text}</Say>'
        "</Gather>"
        '<Say voice="alice">'
        "I didn't hear anything. Thank you for calling! Goodbye."
        "</Say>"
        "</Response>"
    )


def _build_twiml_goodbye(say_text: str) -> str:
    """Build TwiML that speaks a goodbye message and hangs up."""
    safe_text = (
        say_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="alice">{safe_text}</Say>'
        "</Response>"
    )


def _xml_escape(text: str) -> str:
    """Escape text for safe inclusion in XML."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ---------------------------------------------------------------------------
# AI call summary & action item extraction (Features 2 & 3)
# ---------------------------------------------------------------------------


async def _generate_call_summary(call_id: str, tenant_id: str, lead_id: str | None, transcript_text: str) -> None:
    """Generate an AI summary of a call transcript and store it.

    Calls Claude to produce:
    - A one-paragraph summary
    - Action items (list)
    - Caller sentiment (positive/neutral/negative)
    - Suggested follow-up

    Then updates the call record and inserts action items into action_items table.
    This runs as a background task so it does not block the webhook response.
    """
    if not transcript_text or not transcript_text.strip():
        logger.warning("Skipping summary generation for call %s: empty transcript", call_id)
        return

    prompt = (
        "Analyze this phone call transcript and provide:\n"
        "1. A one-paragraph summary\n"
        "2. Action items (list)\n"
        "3. Caller sentiment (positive/neutral/negative)\n"
        "4. Suggested follow-up\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "action_items": ["item 1", "item 2"],\n'
        '  "sentiment": "positive|neutral|negative",\n'
        '  "follow_up": "..."\n'
        "}\n\n"
        f"Transcript:\n{transcript_text}"
    )

    try:
        llm_result = await call_claude_messages(
            operation="calls.generate_summary",
            model=resolve_string_setting("voice_chat_model", "claude-sonnet-4-6"),
            max_tokens=max(600, resolve_int_setting("voice_chat_max_tokens", 160) * 3),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            timeout=30.0,
            metadata={
                "tenant_id": tenant_id,
                "call_id": call_id,
                "transcript_chars": len(transcript_text),
            },
        )
        raw_text = llm_result.text.strip()
    except Exception:
        logger.exception("Claude API call failed for call summary, call %s", call_id)
        return

    # Parse the JSON response from Claude
    summary = ""
    action_items: list[str] = []
    sentiment = "neutral"
    follow_up = ""

    try:
        # Extract JSON from the response (Claude may wrap it in markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            parsed = json.loads(json_match.group())
            summary = parsed.get("summary", "")
            action_items = parsed.get("action_items", [])
            raw_sentiment = parsed.get("sentiment", "neutral").lower().strip()
            if raw_sentiment in ("positive", "neutral", "negative"):
                sentiment = raw_sentiment
            else:
                sentiment = "neutral"
            follow_up = parsed.get("follow_up", "")
        else:
            logger.warning("No JSON found in Claude response for call %s, using raw text", call_id)
            summary = raw_text[:500]
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Failed to parse Claude summary JSON for call %s: %s", call_id, exc)
        summary = raw_text[:500]

    # Build action_taken from follow-up and action items
    action_taken_parts: list[str] = []
    if follow_up:
        action_taken_parts.append(f"Follow-up: {follow_up}")
    if action_items:
        action_taken_parts.append("Action items: " + "; ".join(action_items))
    action_taken = " | ".join(action_taken_parts) if action_taken_parts else None

    # Update the call record with summary, sentiment, and action_taken
    db = get_service_supabase()
    try:
        update_data: dict[str, Any] = {
            "summary": summary,
            "sentiment": sentiment,
        }
        if action_taken:
            update_data["action_taken"] = action_taken

        db.table("calls").update(update_data).eq("id", call_id).eq("tenant_id", tenant_id).execute()
        logger.info(
            "Updated call %s with AI summary (sentiment=%s, %d action items)",
            call_id, sentiment, len(action_items),
        )
    except Exception:
        logger.exception("Failed to update call %s with AI summary", call_id)

    # Feature 3: Insert action items into action_items table
    if action_items:
        await _insert_call_action_items(
            tenant_id=tenant_id,
            lead_id=lead_id,
            call_id=call_id,
            items=action_items,
        )

    # G3 Phase 1: file a callback-text draft into the Agent OS approval flow.
    # The owner sees "Missed call from X" with the summary and a one-tap
    # text-back; per-agent auto-send rules (G6) can send it automatically.
    try:
        caller_phone = ""
        business_name = ""
        call_row = (
            db.table("calls")
            .select("caller_phone")
            .eq("id", call_id)
            .limit(1)
            .execute()
        )
        if call_row.data:
            caller_phone = call_row.data[0].get("caller_phone") or ""
        tenant_row = (
            db.table("tenants")
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_row.data:
            business_name = tenant_row.data[0].get("business_name") or "us"

        if caller_phone:
            from backend.services.voice_recovery import create_missed_call_followup

            await create_missed_call_followup(
                db,
                tenant_id=tenant_id,
                business_name=business_name,
                caller=caller_phone,
                call_id=call_id,
                lead_id=lead_id,
                summary=summary,
                follow_up=follow_up,
                transcript_excerpt=transcript_text,
            )
    except Exception:
        logger.exception(
            "Missed-call recovery draft failed for call %s (summary still saved)",
            call_id,
        )


async def _insert_call_action_items(
    tenant_id: str,
    lead_id: str | None,
    call_id: str,
    items: list[str],
) -> None:
    """Insert action items extracted from a call into the action_items table.

    Phone call action items are always high priority since they represent
    direct customer communication.
    """
    if not items:
        return

    db = get_service_supabase()
    inserted = 0
    for item_text in items:
        if not item_text or not item_text.strip():
            continue
        row: dict[str, Any] = {
            "tenant_id": tenant_id,
            "description": item_text.strip()[:500],
            "priority": "high",
            "status": "pending",
        }
        if lead_id:
            row["lead_id"] = lead_id
        try:
            db.table("action_items").insert(row).execute()
            inserted += 1
        except Exception:
            logger.exception(
                "Failed to insert action item for call %s: %s",
                call_id, item_text[:80],
            )
    if inserted:
        logger.info("Inserted %d action items from call %s for tenant %s", inserted, call_id, tenant_id)

    # Log activity for the action items creation
    log_activity(
        tenant_id=tenant_id,
        activity_type="call_action_items",
        description=f"AI extracted {inserted} action item(s) from phone call",
        lead_id=lead_id,
        metadata={"call_id": call_id, "action_item_count": inserted},
    )


async def _finalize_ai_call(
    db, tenant_id: str, call_sid: str, duration_seconds: int
) -> None:
    """Close out a live-AI call: persist the transcript from chat_messages,
    mark the call completed, and kick off summary + recovery draft.

    Idempotent — a call already marked completed is skipped, so the inline
    max-rounds finalize and the Twilio status callback can both fire.
    """
    if not call_sid:
        return
    result = (
        db.table("calls")
        .select("id, tenant_id, lead_id, status")
        .eq("twilio_call_sid", call_sid)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return
    call = result.data[0]
    if call.get("status") == "completed":
        return

    session_id = f"call_{call_sid}"
    transcript: list[dict[str, Any]] = []
    transcript_text = ""
    try:
        history = (
            db.table("chat_messages")
            .select("role, content")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(40)
            .execute()
        )
        for i, msg in enumerate(history.data or []):
            speaker = "assistant" if msg.get("role") == "assistant" else "caller"
            transcript.append(
                {"timestamp": i, "speaker": speaker, "text": msg.get("content") or ""}
            )
        transcript_text = "\n".join(
            f"[{t['speaker']}]: {t['text']}" for t in transcript if t["text"]
        )
    except Exception:
        logger.exception("Failed to build transcript for call %s", call_sid)

    update: dict[str, Any] = {"status": "completed"}
    if duration_seconds:
        update["duration_seconds"] = duration_seconds
    if transcript:
        update["transcript"] = transcript
        update["summary"] = "AI conversation completed. Summary generating..."
    db.table("calls").update(update).eq("id", call["id"]).eq(
        "tenant_id", tenant_id
    ).execute()

    if transcript_text:
        await _generate_call_summary(
            call_id=call["id"],
            tenant_id=tenant_id,
            lead_id=call.get("lead_id"),
            transcript_text=transcript_text,
        )


# ---------------------------------------------------------------------------
# Twilio voice webhooks
# ---------------------------------------------------------------------------


@router.post("/voice/call-status")
@limiter.limit("60/minute")
async def handle_call_status(
    request: Request,
    background_tasks: BackgroundTasks,
    _sig: None = Depends(verify_twilio_request),
):
    """Twilio call status callback — the reliable end-of-call hook.

    Configure the Twilio number's statusCallback to this URL. When a live-AI
    call ends (including mid-conversation hangups, which never reach the
    max-rounds goodbye), this finalizes the call record and triggers the
    summary + missed-call recovery draft.
    """
    body = await request.body()
    try:
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        return Response(content="OK", media_type="text/plain")

    call_status = params.get("CallStatus", "")
    call_sid = params.get("CallSid", "")
    called = params.get("To", "")
    try:
        duration = int(params.get("CallDuration", "0"))
    except (ValueError, TypeError):
        duration = 0

    if call_status != "completed" or not call_sid:
        return Response(content="OK", media_type="text/plain")

    tenant = _find_tenant_by_phone(called)
    if not tenant:
        return Response(content="OK", media_type="text/plain")

    try:
        db = get_service_supabase()
    except Exception:
        logger.exception("call-status: supabase unavailable for %s", call_sid)
        return Response(content="OK", media_type="text/plain")
    background_tasks.add_task(
        _finalize_ai_call, db, tenant["id"], call_sid, duration
    )
    return Response(content="OK", media_type="text/plain")


@router.post("/voice/incoming")
@limiter.limit("30/minute")
async def handle_incoming_call(request: Request, _sig: None = Depends(verify_twilio_request)):
    """Twilio voice webhook -- greets the caller and starts AI conversation.

    Twilio POSTs form-encoded data with caller info. We respond with TwiML
    that plays a greeting using the business name and then uses <Gather> to
    collect the caller's speech for an AI-powered conversation loop.

    Falls back to voicemail recording if the AI conversation path fails.
    """
    body = await request.body()

    try:
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        logger.error("Failed to parse incoming call body")
        return Response(content=_build_twiml_error(), media_type="application/xml")

    caller = params.get("From", "")
    called = params.get("To", "")
    call_sid = params.get("CallSid", "")

    logger.info("Incoming call from %s to %s (SID: %s)", caller, called, call_sid)

    # Find the tenant this call was for
    tenant = _find_tenant_by_phone(called)
    if not tenant:
        logger.warning("Incoming call to %s -- no matching tenant found", called)
        return Response(content=_build_twiml_error(), media_type="application/xml")

    business_name = tenant.get("business_name") or "our business"
    base_url = str(request.base_url).rstrip("/")

    # Voice mode switch (G3): live AI answering is opt-in AND plan-gated;
    # everyone else gets voicemail mode, which feeds the missed-call
    # recovery pipeline (record -> transcribe -> summarize -> OS draft).
    if not _ai_voice_mode(tenant):
        recording_callback_url = f"{base_url}/api/v1/calls/voice/recording-complete"
        return Response(
            content=_build_twiml_greeting(business_name, recording_callback_url),
            media_type="application/xml",
        )

    # AI mode: open the call record + lead up front so a mid-call hangup
    # still leaves a trail (finalized by /voice/call-status). A DB outage
    # must never block answering the phone — degrade to no trail.
    db = None
    try:
        db = get_service_supabase()
        lead_id = _find_or_create_lead(
            db, tenant["id"], caller, "Inbound phone call (AI answered)"
        )
        db.table("calls").insert(
            {
                "tenant_id": tenant["id"],
                "caller_phone": caller,
                "called_number": called,
                "direction": "inbound",
                "status": "in-progress",
                "twilio_call_sid": call_sid,
                "summary": "AI conversation in progress.",
                **({"lead_id": lead_id} if lead_id else {}),
            }
        ).execute()
    except Exception:
        logger.exception("Failed to open call record for %s", call_sid)

    respond_url = f"{base_url}/api/v1/calls/voice/respond"

    greeting = (
        f"Thanks for calling {_xml_escape(business_name)}! "
        "How can I help you today?"
    )
    # Use raw XML since greeting is already escaped where needed
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" timeout="5" speechTimeout="auto"'
        f' action="{respond_url}?round=1" method="POST">'
        f'<Say voice="alice">{greeting}</Say>'
        "</Gather>"
        '<Say voice="alice">'
        "I didn't hear anything. Thank you for calling! Goodbye."
        "</Say>"
        "</Response>"
    )

    # Save the greeting as the first assistant message
    try:
        session_id = f"call_{call_sid}"
        db.table("chat_messages").insert({
            "tenant_id": tenant["id"],
            "session_id": session_id,
            "role": "assistant",
            "content": f"Thanks for calling {business_name}! How can I help you today?",
        }).execute()
    except Exception:
        logger.exception("Failed to save greeting message for call %s", call_sid)

    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/respond")
@limiter.limit("30/minute")
async def handle_voice_respond(request: Request, _sig: None = Depends(verify_twilio_request)):
    """AI voice conversation handler -- processes speech input and responds.

    Twilio POSTs form-encoded data with the caller's SpeechResult from <Gather>.
    We:
    1. Extract the caller's speech text
    2. Look up the tenant
    3. Load conversation history from chat_messages
    4. Call Claude with business context
    5. Return TwiML with <Say> + another <Gather> for continued conversation
    6. Save both messages to chat_messages

    After _MAX_VOICE_ROUNDS rounds or if no speech is detected, end with goodbye.
    """
    request_started = perf_counter()
    body = await request.body()

    try:
        raw_params = parse_qs(body.decode())
        params = {k: v[0] for k, v in raw_params.items()}
    except Exception:
        logger.error("Failed to parse voice respond body")
        return Response(
            content=_build_twiml_goodbye("Sorry, I had trouble understanding. Goodbye!"),
            media_type="application/xml",
        )

    speech_result = params.get("SpeechResult", "")
    call_sid = params.get("CallSid", "")
    caller = params.get("From", "")
    called = params.get("To", "")

    # Parse round number from query string
    query_string = str(request.url.query) if request.url.query else ""
    round_num = 1
    try:
        qs_params = parse_qs(query_string)
        round_num = int(qs_params.get("round", ["1"])[0])
    except (ValueError, TypeError):
        round_num = 1

    logger.info(
        "Voice respond: SID=%s, round=%d, speech='%s'",
        call_sid, round_num, speech_result[:100],
    )

    if not speech_result:
        return Response(
            content=_build_twiml_goodbye(
                "I didn't catch that. Thank you for calling! Goodbye."
            ),
            media_type="application/xml",
        )

    # Find the tenant
    tenant = _find_tenant_by_phone(called)
    if not tenant:
        logger.warning("Voice respond: no tenant found for %s", called)
        return Response(
            content=_build_twiml_goodbye(
                "Sorry, I'm unable to assist right now. Goodbye!"
            ),
            media_type="application/xml",
        )

    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "our business"
    session_id = f"call_{call_sid}"
    db = get_service_supabase()

    # Save the caller's message
    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": "user",
            "content": speech_result,
        }).execute()
    except Exception:
        logger.exception("Failed to save user voice message for call %s", call_sid)

    # Load conversation history for context
    conversation_messages: list[dict[str, str]] = []
    try:
        history = (
            db.table("chat_messages")
            .select("role, content")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )
        for msg in history.data or []:
            conversation_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
    except Exception:
        logger.exception("Failed to load conversation history for call %s", call_sid)
        # Fall back to just this message
        conversation_messages = [{"role": "user", "content": speech_result}]

    voice_history_limit = resolve_int_setting("widget_prompt_history_messages", 8)
    voice_message_chars = min(resolve_int_setting("widget_prompt_message_chars", 420), 320)
    compact_voice_history = []
    for msg in conversation_messages[-voice_history_limit:]:
        content = (msg.get("content") or "").strip()
        if len(content) > voice_message_chars:
            content = content[: voice_message_chars - 3].rstrip() + "..."
        compact_voice_history.append({
            "role": msg.get("role") or "user",
            "content": content,
        })
    conversation_messages = compact_voice_history

    # Load business info for system prompt context
    business_info = ""
    try:
        tenant_detail = (
            db.table("tenants")
            .select("business_name, business_type, owner_email")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_detail.data:
            td = tenant_detail.data[0]
            business_info = f"Business: {td.get('business_name', '')}. "
            if td.get("business_type"):
                business_info += f"Type: {td['business_type']}. "
    except Exception:
        logger.warning("Failed to load tenant details for voice AI, tenant %s", tenant_id)

    # Load FAQ for additional context
    faq_text = ""
    try:
        faq_result = (
            db.table("faq_entries")
            .select("question, answer")
            .eq("tenant_id", tenant_id)
            .limit(resolve_int_setting("widget_prompt_faq_limit", 6))
            .execute()
        )
        if faq_result.data:
            faq_text = "Frequently Asked Questions:\n" + "\n".join(
                f"Q: {(f.get('question') or '')[:160]}\nA: {(f.get('answer') or '')[:280]}"
                for f in faq_result.data
            )
    except Exception:
        logger.warning("Failed to load FAQ for voice AI, tenant %s", tenant_id)

    # Vertical operating guidance (same pack the Agent OS staff uses — e.g.
    # financial_services carries the no-personalized-advice compliance entry)
    guidance_text = ""
    try:
        from backend.services.os_kb_feed import vertical_guidance

        entries = vertical_guidance(tenant.get("business_type"))[:3]
        if entries:
            guidance_text = "Operating guidance:\n" + "\n".join(
                f"- {e['answer'][:300]}" for e in entries
            )
    except Exception:
        logger.warning("Failed to load vertical guidance for voice AI", exc_info=True)

    system_prompt = (
        f"You are a helpful phone assistant for {business_name}. {business_info}"
        "You are speaking with a caller on the phone. Keep your responses concise "
        "and conversational -- ideally 1-3 sentences since this will be spoken aloud. "
        "Be warm and helpful. If you don't know the answer, offer to have someone "
        "call them back. Never say you are an AI unless directly asked. "
        "If the caller wants an appointment or a quote, collect their name and "
        "the best time to reach them, and say someone will confirm shortly."
    )
    if guidance_text:
        system_prompt += f"\n\n{guidance_text}"
    if faq_text:
        system_prompt += f"\n\n{faq_text}"

    # Call Claude for AI response
    ai_response = ""
    try:
        llm_result = await call_claude_messages(
            operation="calls.voice_respond",
            model=resolve_string_setting("voice_chat_model", "claude-sonnet-4-6"),
            max_tokens=resolve_int_setting("voice_chat_max_tokens", 160),
            system=system_prompt,
            messages=conversation_messages,
            temperature=0.0,
            timeout=30.0,
            metadata={
                "tenant_id": tenant_id,
                "call_sid": call_sid,
                "round": round_num,
                "history_count": len(conversation_messages),
                "faq_chars": len(faq_text),
            },
        )
        ai_response = llm_result.text.strip()
        logger.info(
            "voice_respond: llm_result call_sid=%s round=%d llm_ms=%d response_chars=%d",
            call_sid,
            round_num,
            llm_result.duration_ms,
            len(ai_response),
        )
    except Exception:
        logger.exception("Claude API call failed for voice respond, call %s", call_sid)
        ai_response = (
            "I'm sorry, I'm having a little trouble right now. "
            "Let me have someone call you back as soon as possible."
        )

    # Save the AI response
    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": "assistant",
            "content": ai_response,
        }).execute()
    except Exception:
        logger.exception("Failed to save AI voice response for call %s", call_sid)

    # Check if we should continue or end the conversation
    if round_num >= _MAX_VOICE_ROUNDS:
        goodbye_text = (
            f"{ai_response} "
            f"Thank you for calling {_xml_escape(business_name)}! "
            "Have a great day. Goodbye!"
        )
        # Belt-and-braces finalize; /voice/call-status covers hangups too.
        try:
            await _finalize_ai_call(db, tenant_id, call_sid, duration_seconds=0)
        except Exception:
            logger.exception("Inline finalize failed for call %s", call_sid)
        return Response(
            content=_build_twiml_goodbye(goodbye_text),
            media_type="application/xml",
        )

    # Continue conversation with another Gather
    base_url = str(request.base_url).rstrip("/")
    respond_url = f"{base_url}/api/v1/calls/voice/respond"
    next_round = round_num + 1

    twiml = _build_twiml_gather(ai_response, respond_url, next_round)
    logger.info(
        "voice_respond: timing_summary call_sid=%s total_ms=%d history_count=%d",
        call_sid,
        int((perf_counter() - request_started) * 1000),
        len(conversation_messages),
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/recording-complete")
@limiter.limit("30/minute")
async def handle_recording_complete(request: Request, _sig: None = Depends(verify_twilio_request)):
    """Twilio recording status callback -- fires when a recording is ready.

    Stores the call record, creates/updates a lead, sends an SMS notification
    to the business owner, and fires the call.completed webhook event.
    """
    body = await request.body()

    try:
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        logger.error("Failed to parse recording callback body")
        raise HTTPException(status_code=400, detail="Invalid request body")

    call_sid = params.get("CallSid", "")
    recording_url = params.get("RecordingUrl", "")
    recording_duration = params.get("RecordingDuration", "0")
    caller = params.get("From", "")
    called = params.get("To", "")
    recording_status = params.get("RecordingStatus", "")

    logger.info(
        "Recording complete: SID=%s, status=%s, duration=%ss, caller=%s",
        call_sid, recording_status, recording_duration, caller,
    )

    # Only process completed recordings
    if recording_status != "completed":
        logger.info("Skipping recording with status: %s", recording_status)
        return Response(content="OK", media_type="text/plain")

    # Find the tenant
    tenant = _find_tenant_by_phone(called)
    if not tenant:
        logger.warning("Recording callback for %s -- no matching tenant", called)
        return Response(content="OK", media_type="text/plain")

    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "us"
    db = get_service_supabase()

    # Parse duration
    try:
        duration = int(recording_duration)
    except (ValueError, TypeError):
        duration = 0

    # Create/find lead from caller phone
    lead_id = None
    try:
        existing_lead = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("phone", caller)
            .limit(1)
            .execute()
        )
        if existing_lead.data:
            lead_id = existing_lead.data[0]["id"]
        else:
            # Create new lead
            new_lead = (
                db.table("leads")
                .insert({
                    "client_id": tenant_id,
                    "phone": caller,
                    "status": "new",
                    "areas_of_interest": "Inbound phone call",
                })
                .execute()
            )
            if new_lead.data:
                lead_id = new_lead.data[0]["id"]
                logger.info("Created lead %s from caller %s for tenant %s", lead_id, caller, tenant_id)
    except Exception:
        logger.exception("Failed to create/find lead for caller %s, tenant %s", caller, tenant_id)

    # Store call record
    # NOTE: For v1, summary is a placeholder. Future enhancement: use a speech-to-text
    # service (e.g., Twilio intelligence, Deepgram, or Whisper) to transcribe the
    # recording, then pass the transcript to Claude for summarization.
    call_data: dict[str, Any] = {
        "tenant_id": tenant_id,
        "caller_phone": caller,
        "called_number": called,
        "direction": "inbound",
        "duration_seconds": duration,
        "status": "completed",
        "recording_url": recording_url,
        "twilio_call_sid": call_sid,
        "summary": "Voicemail recorded. Transcription pending.",
    }
    if lead_id:
        call_data["lead_id"] = lead_id

    call_id = None
    try:
        result = db.table("calls").insert(call_data).execute()
        if result.data:
            call_id = result.data[0]["id"]
        logger.info("Stored call record %s for tenant %s", call_id, tenant_id)
    except Exception:
        logger.exception("Failed to store call record for SID %s", call_sid)

    # Log activity
    log_activity(
        tenant_id=tenant_id,
        activity_type="inbound_call",
        description=f"Inbound call from {caller} ({duration}s recording)",
        lead_id=lead_id,
        metadata={
            "caller": caller,
            "called": called,
            "call_sid": call_sid,
            "duration_seconds": duration,
            "recording_url": recording_url,
        },
    )

    # Send SMS notification to business owner
    owner_phone = tenant.get("notification_phone")
    if owner_phone:
        notification_msg = (
            f"You missed a call from {caller}. "
            f"Recording available in your dashboard."
        )
        try:
            await send_sms(to=owner_phone, body=notification_msg)
            logger.info("Sent call notification SMS to %s for tenant %s", owner_phone, tenant_id)
        except Exception:
            logger.exception("Failed to send call notification SMS to %s", owner_phone)

    # Fire webhook event
    fire_event_background(
        tenant_id=tenant_id,
        event="call.completed",
        data={
            "call_id": call_id,
            "caller_phone": caller,
            "duration_seconds": duration,
            "recording_url": recording_url,
            "lead_id": lead_id,
        },
    )

    # Request transcription of the recording via Twilio API.
    # Twilio will POST the transcription to our transcription-complete endpoint.
    recording_sid = params.get("RecordingSid", "")
    if recording_sid and settings.twilio_account_sid and settings.twilio_auth_token:
        base_url = str(request.base_url).rstrip("/")
        transcription_url = f"{base_url}/api/v1/calls/voice/transcription-complete"
        try:
            import httpx
            twilio_api_url = (
                f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{settings.twilio_account_sid}/Recordings/"
                f"{recording_sid}/Transcriptions.json"
            )
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                resp = await http_client.post(
                    twilio_api_url,
                    data={"TranscriptionUrl": transcription_url},
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                )
                if resp.status_code in (200, 201):
                    logger.info(
                        "Requested Twilio transcription for recording %s (call %s)",
                        recording_sid, call_sid,
                    )
                else:
                    logger.warning(
                        "Twilio transcription request failed: status=%d body=%s",
                        resp.status_code, resp.text[:200],
                    )
        except Exception:
            logger.exception(
                "Failed to request Twilio transcription for recording %s", recording_sid
            )

    return Response(content="OK", media_type="text/plain")


@router.post("/voice/transcription-complete")
@limiter.limit("30/minute")
async def handle_transcription_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    _sig: None = Depends(verify_twilio_request),
):
    """Twilio transcription callback -- fires when a recording transcription is ready.

    Twilio POSTs form-encoded data with:
    - TranscriptionText: the transcribed text
    - TranscriptionSid: unique transcription identifier
    - RecordingSid: the recording that was transcribed
    - CallSid: the original call SID

    We:
    1. Parse the transcription text
    2. Find the call record by twilio_call_sid
    3. Store the transcript as a JSONB array
    4. Trigger AI summary generation as a background task
    """
    body = await request.body()

    try:
        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        logger.error("Failed to parse transcription callback body")
        raise HTTPException(status_code=400, detail="Invalid request body")

    transcription_text = params.get("TranscriptionText", "")
    transcription_sid = params.get("TranscriptionSid", "")
    recording_sid = params.get("RecordingSid", "")
    call_sid = params.get("CallSid", "")
    transcription_status = params.get("TranscriptionStatus", "")

    logger.info(
        "Transcription complete: CallSid=%s, TranscriptionSid=%s, RecordingSid=%s, status=%s, text_len=%d",
        call_sid, transcription_sid, recording_sid, transcription_status, len(transcription_text),
    )

    # Only process completed transcriptions
    if transcription_status and transcription_status != "completed":
        logger.info("Skipping transcription with status: %s", transcription_status)
        return Response(content="OK", media_type="text/plain")

    if not transcription_text.strip():
        logger.warning("Empty transcription text for call %s", call_sid)
        return Response(content="OK", media_type="text/plain")

    if not call_sid:
        logger.warning("Transcription callback missing CallSid")
        return Response(content="OK", media_type="text/plain")

    db = get_service_supabase()

    # Find the call record by twilio_call_sid
    call_record = None
    try:
        result = (
            db.table("calls")
            .select("id, tenant_id, lead_id, transcript")
            .eq("twilio_call_sid", call_sid)
            .limit(1)
            .execute()
        )
        if result.data:
            call_record = result.data[0]
    except Exception:
        logger.exception("Failed to find call record for SID %s", call_sid)

    if not call_record:
        logger.warning(
            "Transcription received for unknown call SID %s (transcription_sid=%s)",
            call_sid, transcription_sid,
        )
        return Response(content="OK", media_type="text/plain")

    call_id = call_record["id"]
    tenant_id = call_record["tenant_id"]
    lead_id = call_record.get("lead_id")

    # Build the transcript as a JSONB array.
    # Twilio provides the full transcription as one block of text.
    # We store it as a structured array for consistency with the schema.
    transcript_entry: list[dict[str, Any]] = [
        {
            "timestamp": 0,
            "speaker": "caller",
            "text": transcription_text.strip(),
        }
    ]

    # If there is an existing transcript (e.g., from the AI conversation path),
    # merge it rather than overwriting.
    existing_transcript = call_record.get("transcript") or []
    if existing_transcript and isinstance(existing_transcript, list):
        # Append the new transcription entry
        transcript_entry = existing_transcript + transcript_entry

    # Update the call record with the transcript
    try:
        db.table("calls").update({
            "transcript": transcript_entry,
            "summary": "Transcription received. AI summary generating...",
        }).eq("id", call_id).eq("tenant_id", tenant_id).execute()
        logger.info("Stored transcript for call %s (tenant %s)", call_id, tenant_id)
    except Exception:
        logger.exception("Failed to update call %s with transcript", call_id)

    # Trigger AI summary generation as a background task (Feature 2)
    # Build the full transcript text for the AI
    full_transcript_text = transcription_text.strip()
    if existing_transcript and isinstance(existing_transcript, list):
        # Include existing transcript entries in the text sent to Claude
        prior_parts = [
            f"[{entry.get('speaker', 'unknown')}]: {entry.get('text', '')}"
            for entry in existing_transcript
            if entry.get("text")
        ]
        if prior_parts:
            full_transcript_text = "\n".join(prior_parts) + "\n[caller]: " + transcription_text.strip()

    background_tasks.add_task(
        _generate_call_summary,
        call_id=call_id,
        tenant_id=tenant_id,
        lead_id=lead_id,
        transcript_text=full_transcript_text,
    )

    return Response(content="OK", media_type="text/plain")


# ---------------------------------------------------------------------------
# Dashboard endpoints (authenticated)
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}", response_model=CallListResponse)
async def list_calls(
    tenant_id: str,
    status: str | None = Query(None, description="Filter by call status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    claims: dict = Depends(_get_current_tenant),
):
    """List calls for a tenant with pagination and optional status filter."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        query = (
            db.table("calls")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
        )

        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True)

        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)

        result = query.execute()
        total = result.count if result.count is not None else len(result.data or [])

        return CallListResponse(
            calls=result.data or [],
            total=total,
            page=page,
            per_page=per_page,
        )
    except Exception:
        logger.exception("Failed to list calls for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve calls")


@router.get("/{tenant_id}/stats", response_model=CallStatsResponse)
async def get_call_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get call statistics for a tenant: total, missed, avg duration, calls today."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    stats = CallStatsResponse()

    # Total calls
    try:
        total_result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        stats.total_calls = total_result.count if total_result.count is not None else 0
    except Exception:
        logger.warning("Failed to count total calls for tenant %s", tenant_id, exc_info=True)

    # Missed calls (no-answer, busy, failed)
    try:
        for missed_status in ("no-answer", "busy", "failed"):
            missed_result = (
                db.table("calls")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("status", missed_status)
                .execute()
            )
            count = missed_result.count if missed_result.count is not None else 0
            stats.missed_calls += count
    except Exception:
        logger.warning("Failed to count missed calls for tenant %s", tenant_id, exc_info=True)

    # Average duration (from completed calls with duration > 0)
    try:
        duration_result = (
            db.table("calls")
            .select("duration_seconds")
            .eq("tenant_id", tenant_id)
            .eq("status", "completed")
            .execute()
        )
        durations = [
            r["duration_seconds"]
            for r in (duration_result.data or [])
            if r.get("duration_seconds") and r["duration_seconds"] > 0
        ]
        if durations:
            stats.avg_duration_seconds = round(sum(durations) / len(durations), 1)
    except Exception:
        logger.warning("Failed to compute avg duration for tenant %s", tenant_id, exc_info=True)

    # Calls today
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        today_result = (
            db.table("calls")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", today_start)
            .execute()
        )
        stats.calls_today = today_result.count if today_result.count is not None else 0
    except Exception:
        logger.warning("Failed to count today's calls for tenant %s", tenant_id, exc_info=True)

    return stats


@router.get("/{tenant_id}/{call_id}", response_model=CallOut)
async def get_call(
    tenant_id: str,
    call_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single call with full details."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        result = (
            db.table("calls")
            .select("*")
            .eq("id", call_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Call not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get call %s for tenant %s", call_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve call")
