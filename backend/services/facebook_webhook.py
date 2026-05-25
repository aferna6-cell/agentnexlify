"""Facebook Messenger webhook helpers — signature verification + event processing.

Extracted from backend/routers/channels_facebook.py to keep the router under the
god-class threshold and isolate signature math + ingestion for direct testing.
"""

import hashlib
import hmac
import logging

from backend.config import settings
from backend.services.channel_manager import ingest_channel_message

logger = logging.getLogger(__name__)


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Validate X-Hub-Signature-256 HMAC; absent/malformed header is invalid."""
    app_secret = getattr(settings, "facebook_app_secret", "")
    if not app_secret:
        # Fail closed when secret missing
        logger.warning("facebook_app_secret not configured; rejecting inbound webhook")
        return False

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


async def process_event(payload: dict) -> None:
    """Parse Messenger 'entry' list and ingest text messages via channel_manager.

    Skips echoes, attachments-only, and missing-text events. Runs as a
    BackgroundTasks callback so the HTTP response returns 200 immediately —
    Facebook will retry any non-200.
    """
    entries = payload.get("entry", [])
    for entry in entries:
        page_id: str = str(entry.get("id", ""))
        for event in entry.get("messaging", []):
            message_obj = event.get("message", {})

            if message_obj.get("is_echo"):
                continue

            sender_psid: str = str(event.get("sender", {}).get("id", ""))
            text: str = message_obj.get("text", "")
            timestamp_ms: int | None = event.get("timestamp")

            if not sender_psid or not text:
                continue

            try:
                result = ingest_channel_message(
                    provider="facebook",
                    page_id=page_id,
                    sender_id=sender_psid,
                    sender_name=None,
                    text=text,
                    timestamp_ms=timestamp_ms,
                )
            except Exception:
                logger.exception(
                    "channel_manager.ingest_channel_message failed for page=%s sender=%s",
                    page_id,
                    sender_psid,
                )
                continue

            if result:
                logger.info(
                    "Facebook message ingested: tenant=%s conversation=%s",
                    result.get("tenant_id"),
                    result.get("conversation_id"),
                )
