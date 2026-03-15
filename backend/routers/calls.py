"""AI Answering Service — voice call handling and call management endpoints.

Twilio voice webhooks for incoming calls (greeting + recording + AI conversation),
plus dashboard endpoints for listing, viewing, and aggregating call data.
"""

import asyncio
import logging
from datetime import datetime, timezone
from functools import partial
from typing import Any
from urllib.parse import parse_qs

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

# Max AI conversation rounds before ending the call
_MAX_VOICE_ROUNDS = 3

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
    db = get_supabase()
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, owner_email, notification_phone, sms_notifications_enabled")
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


def _build_twiml_greeting(business_name: str, recording_callback_url: str) -> str:
    """Build a TwiML response that greets the caller and records their message."""
    # XML-escape the business name to prevent injection
    safe_name = (
        business_name
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
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
# Twilio voice webhooks
# ---------------------------------------------------------------------------


@router.post("/voice/incoming")
@limiter.limit("30/minute")
async def handle_incoming_call(request: Request):
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

    business_name = tenant.get("business_name", "our business")

    # Build the respond URL for the Gather action
    base_url = str(request.base_url).rstrip("/")
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
        db = get_supabase()
        db.table("chat_messages").insert({
            "tenant_id": tenant["id"],
            "session_id": session_id,
            "role": "assistant",
            "content": f"Thanks for calling {business_name}! How can I help you today?",
        }).execute()
    except Exception:
        logger.exception("Failed to save greeting message for call %s", call_sid)

    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/recording-complete")
@limiter.limit("30/minute")
async def handle_recording_complete(request: Request):
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
    business_name = tenant.get("business_name", "us")
    db = get_supabase()

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

    db = get_supabase()
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

    db = get_supabase()
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

    db = get_supabase()
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
