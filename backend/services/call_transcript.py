"""Call transcript helpers for the calls router.

Pulled out of `handle_transcription_complete` so the router stays focused on
Twilio webhook I/O. Functions here own call-record lookup by Twilio SID,
transcript merging, and the calls-table update.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def find_call_by_twilio_sid(db: Any, call_sid: str) -> dict | None:
    """Look up the calls row that owns a given Twilio CallSid."""
    try:
        result = (
            db.table("calls")
            .select("id, tenant_id, lead_id, transcript")
            .eq("twilio_call_sid", call_sid)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        logger.exception("Failed to find call record for SID %s", call_sid)
    return None


def merge_call_transcript(
    existing: Any,
    new_text: str,
) -> list[dict[str, Any]]:
    """Append a new caller utterance to any existing transcript array.

    Twilio provides the full transcription as one block of text. We store it
    as a structured array for consistency with the schema (matches the AI
    conversation path that builds the same JSONB shape).
    """
    new_entry: dict[str, Any] = {
        "timestamp": 0,
        "speaker": "caller",
        "text": new_text.strip(),
    }
    if existing and isinstance(existing, list):
        return list(existing) + [new_entry]
    return [new_entry]


def update_call_transcript(
    db: Any,
    *,
    call_id: str,
    tenant_id: str,
    transcript: list[dict[str, Any]],
) -> None:
    """Write merged transcript back to the calls row."""
    try:
        db.table("calls").update({
            "transcript": transcript,
            "summary": "Transcription received. AI summary generating...",
        }).eq("id", call_id).eq("tenant_id", tenant_id).execute()
        logger.info("Stored transcript for call %s (tenant %s)", call_id, tenant_id)
    except Exception:
        logger.exception("Failed to update call %s with transcript", call_id)


def build_full_transcript_text(existing: Any, new_text: str) -> str:
    """Flatten existing transcript entries + new caller text for Claude.

    Returns a newline-joined string suitable for passing to the AI summary
    background task. If there is no prior transcript, returns just the
    cleaned new text.
    """
    cleaned_new = new_text.strip()
    if existing and isinstance(existing, list):
        prior_parts = [
            f"[{entry.get('speaker', 'unknown')}]: {entry.get('text', '')}"
            for entry in existing
            if entry.get("text")
        ]
        if prior_parts:
            return "\n".join(prior_parts) + "\n[caller]: " + cleaned_new
    return cleaned_new
