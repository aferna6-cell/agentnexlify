"""Twilio voice webhooks - the AI answering service's inbound surface.

Extracted from backend/routers/calls.py (god-file split, audit 2026-07-22
H2). Handles the full call lifecycle: incoming call (greeting + recording
or live AI gather loop), per-round AI conversation, call-status updates,
recording completion, and the transcription -> summary -> action pipeline.
Dashboard read endpoints stay in calls.py, which mounts this router under
its /api/v1/calls prefix.
"""

import logging
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.automations import verify_twilio_request
from backend.services.voice_twiml import (
    _build_twiml_error,
    _build_twiml_gather,
    _build_twiml_goodbye,
    _build_twiml_greeting,
    _xml_escape,
)
from backend.services.voice_call_summary import (
    _finalize_ai_call,
    _generate_call_summary,
    should_skip_summary_generation,
    should_write_generating_placeholder,
)
from backend.services.voice_phone_routing import (
    _ai_voice_mode,
    _find_or_create_lead,
    _find_tenant_by_phone,
)

logger = logging.getLogger(__name__)

# Max AI conversation rounds before ending the call
_MAX_VOICE_ROUNDS = 3

# Spoken when Claude itself fails. Keep this exact string — callers and tests
# treat it as the live-AI recovery line.
_VOICE_CLAUDE_FALLBACK = (
    "I'm sorry, I'm having a little trouble right now. "
    "Let me have someone call you back as soon as possible."
)
# Spoken when the monthly token hard cap blocks the provider. Twilio still
# gets HTTP 200 TwiML; more Gather rounds cannot unblock a monthly cap.
_VOICE_USAGE_PAUSED = (
    "Thanks for calling. This assistant is temporarily paused "
    "because monthly usage is unusually high. Someone from the team "
    "will follow up with you shortly."
)


class VoiceBudgetExceeded(Exception):
    """Monthly AI hard cap blocked the live-AI Claude call."""


class VoiceBudgetGuardUnavailable(Exception):
    """Tenant/policy could not be loaded — fail closed before the provider."""


def _load_voice_budget_tenant(db: Any, tenant_id: str) -> dict[str, Any] | None:
    """Load the tenant row needed for a pack-aware reservation.

    Returns None when the row is missing or the lookup throws. Callers must
    fail closed before the provider — do not invent a free-plan cap (that
    would falsely block a paying tenant or ignore purchased packs) and do
    not call Claude unmetered.
    """
    try:
        rows = (
            db.table("tenants")
            .select(
                "id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        # Do not attach the lookup exception: it may contain connection or
        # customer context. Tenant id is enough to find the row.
        logger.warning(
            "voice respond tenant load failed tenant=%s",
            tenant_id,
        )
        return None
    if not rows:
        logger.warning(
            "voice respond tenant missing tenant=%s — failing closed before provider",
            tenant_id,
        )
        return None
    return {**rows[0], "id": tenant_id}


async def _call_voice_claude_with_budget(
    *,
    db: Any,
    tenant_id: str,
    call_sid: str,
    system: str,
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    round_num: int,
    faq_chars: int,
):
    """Reserve → Claude → record, or release on provider/error.

    llm_runtime only times/logs the provider call. Reservation + recording
    live here so live-AI voice spend uses the same contract as widget chat.

    Tenant/policy load failure fails closed here (no provider call). A
    later reserve RPC outage is different: reserve_ai_tokens returns
    allowed=True / reason=guard_unavailable and the shared helper may
    still call the provider without persisting usage.
    """
    tenant = _load_voice_budget_tenant(db, tenant_id)
    if tenant is None:
        logger.warning(
            "voice respond budget tenant unavailable tenant=%s — "
            "failing closed before provider",
            tenant_id,
        )
        raise VoiceBudgetGuardUnavailable(
            "AI usage guard unavailable — tenant policy could not be loaded"
        )
    reservation = reserve_ai_tokens(
        tenant=tenant,
        estimated_tokens=estimate_widget_chat_tokens(
            system_prompt=system,
            messages=messages,
            max_tokens=max_tokens,
        ),
        operation="calls.voice_respond",
        session_id=call_sid,
    )
    if not reservation.allowed:
        raise VoiceBudgetExceeded(
            "Monthly AI usage limit reached — add a usage pack or wait for the next cycle"
        )

    try:
        resp = await call_claude_messages(
            operation="calls.voice_respond",
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            temperature=0.0,
            timeout=30.0,
            # Opt-in prompt caching (cost lever F4) — same tenant KB/persona
            # prefix repeats across the 3-round Gather/Say loop for one call.
            # Anthropic caches on exact text hash: per-tenant isolation, no
            # shared key. Default 5-min TTL comfortably covers a live call.
            cache_system=True,
            metadata={
                "tenant_id": tenant_id,
                "call_sid": call_sid,
                "round": round_num,
                "history_count": len(messages),
                "faq_chars": faq_chars,
            },
        )
    except Exception:
        release_ai_token_reservation(reservation)
        raise

    record_ai_usage(
        reservation=reservation,
        result=resp,
        operation="calls.voice_respond",
        session_id=call_sid,
        model=model,
    )
    return resp


# Mounted by calls.py under its /api/v1/calls prefix.
router = APIRouter()



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
    # Live AI answering requires plan+flag AND remaining included minutes
    # (G3 Phase 3). Over-cap degrades to voicemail — never a dropped call.
    ai_mode = _ai_voice_mode(tenant)
    if ai_mode:
        try:
            from backend.services.voice_usage import voice_minutes_exhausted

            if voice_minutes_exhausted(tenant["id"]):
                ai_mode = False
        except Exception:
            logger.warning(
                "voice minutes check failed for tenant %s — allowing AI mode",
                tenant["id"],
                exc_info=True,
            )

    if not ai_mode:
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

    # AI-identification + recording disclosure (CR1/CR4) — spoken before the
    # first prompt, non-disableable. Voice AI consent (TCPA) + call-recording
    # consent must be given at the start of the call.
    greeting = (
        f"Thanks for calling {_xml_escape(business_name)}! "
        "You're speaking with an AI virtual assistant, and this call may be recorded. "
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
            "content": (
                f"Thanks for calling {business_name}! You're speaking with an "
                "AI virtual assistant, and this call may be recorded. "
                "How can I help you today?"
            ),
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
        "Voice respond: SID=%s, round=%d, speech_chars=%d",
        call_sid, round_num, len(speech_result),
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
    # Respond is an independently reachable Twilio webhook. Incoming's live-AI
    # gate is not inherited from the Gather action URL, so a signed but
    # out-of-flow callback (Voice URL pointed at /voice/respond, or a Gather
    # that never went through incoming AI mode) must not become a paid-Claude
    # bypass for voicemail-mode tenants. Re-check _ai_voice_mode here.
    #
    # Do NOT re-check voice_minutes_exhausted on each Gather: incoming already
    # committed to the live loop when minutes remained ("over-cap degrades to
    # voicemail — never a dropped call"). Mid-call minute burn is expected;
    # the token hard-cap is the per-round spend control. Minutes are a
    # start-of-call gate, not a Gather-round gate.
    if not _ai_voice_mode(tenant):
        logger.warning(
            "voice_respond: tenant not live-AI entitled tenant=%s call_sid=%s — "
            "refusing provider",
            tenant_id,
            call_sid,
        )
        return Response(
            content=_build_twiml_goodbye(
                "Sorry, I'm unable to assist right now. Goodbye!"
            ),
            media_type="application/xml",
        )

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

    # Booking (G3 Phase 1): when any caller turn shows booking intent and the
    # tenant has booking on, inject live slots + the BOOK_JSON marker contract
    # into the system prompt. History carries the flow across rounds/workers.
    booking_context = ""
    try:
        from backend.services.voice_booking import booking_prompt_context, wants_booking

        caller_turns = [
            m.get("content", "")
            for m in conversation_messages
            if m.get("role") == "user"
        ]
        if wants_booking(caller_turns):
            booking_context = booking_prompt_context(tenant_id) or ""
    except Exception:
        logger.warning(
            "voice_respond: booking context failed for call %s", call_sid, exc_info=True
        )

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

    # Ground on the vertical knowledge base like the widget does (the moat —
    # voice answers were FAQ-only and shallower than widget answers for the
    # same tenant, audit-voice-g3-scope-2026-07-09 gap #8).
    kb_text = ""
    try:
        from backend.routers.widget_chat_helpers import _query_kb_articles

        kb_refs = await _query_kb_articles(speech_result, match_count=3)
        if kb_refs:
            kb_text = "Knowledge base:\n" + "\n".join(
                f"- {(a.get('title') or '')[:80]}: {(a.get('summary') or '')[:280]}"
                for a in kb_refs
            )
    except Exception:
        logger.warning("Failed to load KB articles for voice AI", exc_info=True)

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
    if booking_context:
        system_prompt += f"\n\n{booking_context}"
    if guidance_text:
        system_prompt += f"\n\n{guidance_text}"
    if kb_text:
        system_prompt += f"\n\n{kb_text}"
    if faq_text:
        system_prompt += f"\n\n{faq_text}"

    # Call Claude for AI response — reserve first so live-AI voice is metered
    # the same way as widget chat. Twilio still always gets HTTP 200 TwiML.
    voice_model = resolve_string_setting("voice_chat_model", "claude-sonnet-4-6")
    voice_max_tokens = resolve_int_setting("voice_chat_max_tokens", 160)
    ai_response = ""
    end_call_now = False
    try:
        llm_result = await _call_voice_claude_with_budget(
            db=db,
            tenant_id=tenant_id,
            call_sid=call_sid,
            system=system_prompt,
            messages=conversation_messages,
            model=voice_model,
            max_tokens=voice_max_tokens,
            round_num=round_num,
            faq_chars=len(faq_text),
        )
        ai_response = (llm_result.text or "").strip()
        logger.info(
            "voice_respond: llm_result call_sid=%s round=%d llm_ms=%d response_chars=%d",
            call_sid,
            round_num,
            llm_result.duration_ms,
            len(ai_response),
        )
    except VoiceBudgetExceeded:
        logger.warning(
            "voice_respond: AI usage hard limit blocked tenant=%s call_sid=%s",
            tenant_id,
            call_sid,
        )
        ai_response = _VOICE_USAGE_PAUSED
        end_call_now = True
    except VoiceBudgetGuardUnavailable:
        logger.warning(
            "voice_respond: budget tenant unavailable tenant=%s call_sid=%s — "
            "failing closed before provider",
            tenant_id,
            call_sid,
        )
        ai_response = _VOICE_CLAUDE_FALLBACK
        end_call_now = True
    except Exception:
        logger.exception("Claude API call failed for voice respond, call %s", call_sid)
        ai_response = _VOICE_CLAUDE_FALLBACK

    # Booking (G3 Phase 1): strip the BOOK_JSON marker (caller must never hear
    # it) and create the appointment it describes. Never raises.
    if booking_context:
        try:
            from backend.services.voice_booking import handle_booking_marker

            ai_response, booked_appointment = handle_booking_marker(
                tenant_id, caller, ai_response
            )
            if booked_appointment:
                ai_response = (
                    f"{ai_response} You're all set - your appointment is "
                    "booked and confirmed."
                ).strip()
        except Exception:
            logger.exception(
                "voice_respond: booking marker handling failed for call %s", call_sid
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

    # Check if we should continue or end the conversation. Cap is a runtime
    # setting (G3 Phase 1) — the fixed 3-round cap ended calls mid-booking
    # (intent -> pick a time -> give name needs the full budget).
    max_rounds = resolve_int_setting("voice_max_rounds", _MAX_VOICE_ROUNDS)
    if booking_context and max_rounds < 5:
        max_rounds = 5
    if end_call_now or round_num >= max_rounds:
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
            .select("id, tenant_id, lead_id, transcript, summary")
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

    current_summary = call_record.get("summary")
    already_summarized = should_skip_summary_generation(current_summary)
    update_payload: dict[str, Any] = {"transcript": transcript_entry}
    if should_write_generating_placeholder(current_summary):
        update_payload["summary"] = "Transcription received. AI summary generating..."

    # Update the call record with the transcript
    try:
        db.table("calls").update(update_payload).eq("id", call_id).eq(
            "tenant_id", tenant_id
        ).execute()
        logger.info("Stored transcript for call %s (tenant %s)", call_id, tenant_id)
    except Exception:
        logger.warning(
            "transcription-complete: transcript persist skipped tenant=%s call=%s",
            tenant_id,
            call_id,
        )

    if already_summarized:
        logger.info(
            "transcription-complete: summary already claimed or persisted "
            "tenant=%s call=%s — skipping provider",
            tenant_id,
            call_id,
        )
        return Response(content="OK", media_type="text/plain")

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
