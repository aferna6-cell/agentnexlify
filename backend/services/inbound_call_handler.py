"""Inbound call processing helpers for the calls router.

Pure DB/HTTP helpers extracted from `backend.routers.calls.handle_recording_complete`
so the router stays focused on Twilio webhook I/O and orchestration. Functions
here own lead lookup/create from caller phone, call record persistence, and the
Twilio transcription request handshake.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def find_or_create_lead_for_caller(db: Any, tenant_id: str, caller: str) -> str | None:
    """Find an existing lead by caller phone or create a new one.

    Returns the lead id, or None if both lookup and create fail. Uses the
    `client_id` column per schema discipline (leads table is `client_id`-keyed).
    """
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
            return existing_lead.data[0]["id"]

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
            logger.info(
                "Created lead %s from caller %s for tenant %s",
                lead_id, caller, tenant_id,
            )
            return lead_id
    except Exception:
        logger.exception(
            "Failed to create/find lead for caller %s, tenant %s",
            caller, tenant_id,
        )
    return None


def store_inbound_call_record(
    db: Any,
    *,
    tenant_id: str,
    lead_id: str | None,
    call_sid: str,
    caller: str,
    called: str,
    duration: int,
    recording_url: str,
) -> str | None:
    """Insert a row into the `calls` table for an inbound voicemail.

    NOTE: For v1, summary is a placeholder. Future enhancement: use a speech-to-text
    service (e.g., Twilio intelligence, Deepgram, or Whisper) to transcribe the
    recording, then pass the transcript to Claude for summarization.
    """
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

    try:
        result = db.table("calls").insert(call_data).execute()
        call_id = result.data[0]["id"] if result.data else None
        logger.info("Stored call record %s for tenant %s", call_id, tenant_id)
        return call_id
    except Exception:
        logger.exception("Failed to store call record for SID %s", call_sid)
        return None


async def request_twilio_transcription(
    *,
    recording_sid: str,
    transcription_url: str,
    account_sid: str,
    auth_token: str,
    call_sid: str,
) -> None:
    """Ask Twilio to transcribe a recording and POST the result back to us."""
    twilio_api_url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{account_sid}/Recordings/"
        f"{recording_sid}/Transcriptions.json"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                twilio_api_url,
                data={"TranscriptionUrl": transcription_url},
                auth=(account_sid, auth_token),
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
