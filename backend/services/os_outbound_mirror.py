"""Agent OS outbound mirror — Group C bi-directional sync.

When the OS orchestrator produces an assistant reply on a thread that was
opened by an inbound channel (widget/email/sms/facebook), the customer reads
from the legacy channel store, not from ``os_messages``. Without a mirror
hop the customer never sees the OS reply.

Phase 1 (this module): widget threads → ``chat_messages`` (DB write only —
the widget polls ``chat_messages`` already).

Phase 2 (TODO): sms/email/facebook → actual outbound provider send
(Twilio SMS, Postmark/Mailgun email, Messenger send API). Mirror currently
returns ``skipped:outbound_not_implemented`` so callers can distinguish
"channel has no mirror yet" from "channel has no session id".

Idempotency: every mirrored row carries ``os_message_id`` matching the OS
message it came from. Replay safe — a second call with the same OS message
finds the existing row and reports ``skipped:already_mirrored``.

Failure semantics: NEVER raise. Mirror is best-effort; the OS reply is
already persisted in ``os_messages``. A failed mirror returns
``error:<reason>`` so the caller can log and continue.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def mirror_assistant_message(
    db: Any,
    client_id: str,
    thread: dict,
    assistant_message: dict,
) -> dict:
    """Mirror an OS assistant message back to the originating channel store.

    Args:
        db: Supabase client (or test fake).
        client_id: Tenant id owning the thread.
        thread: ``os_threads`` row dict — needs ``source`` + ``source_metadata``.
        assistant_message: ``os_messages`` row dict — needs ``id`` + ``content``.

    Returns:
        ``{"status": <one of>}`` — never raises. Statuses:
          - ``mirrored`` — chat_messages row inserted
          - ``skipped:no_channel`` — owner thread, no inbound source
          - ``skipped:no_session`` — widget source but no session_id in metadata
          - ``skipped:outbound_not_implemented`` — sms/email/facebook (phase 2)
          - ``skipped:already_mirrored`` — replay of an already-mirrored message
          - ``error:<reason>`` — DB failure or unexpected exception
    """
    source = thread.get("source")
    if not source:
        return {"status": "skipped:no_channel"}

    if source != "widget":
        return {"status": "skipped:outbound_not_implemented"}

    meta = thread.get("source_metadata") or {}
    session_id = meta.get("session_id") if isinstance(meta, dict) else None
    if not session_id:
        return {"status": "skipped:no_session"}

    os_msg_id = assistant_message.get("id")
    if not os_msg_id:
        return {"status": "error:missing_os_message_id"}

    try:
        existing = (
            tenant_table(db, "chat_messages", client_id)
            .select("id")
            .eq("os_message_id", os_msg_id)
            .limit(1)
            .execute()
        )
        if getattr(existing, "data", None):
            return {"status": "skipped:already_mirrored"}

        tenant_table(db, "chat_messages", client_id).insert(
            {
                "session_id": session_id,
                "role": "assistant",
                "content": assistant_message.get("content", ""),
                "os_message_id": os_msg_id,
            }
        ).execute()
        return {"status": "mirrored"}
    except Exception as exc:
        logger.warning(
            "os_outbound_mirror: mirror failed client_id=%s os_msg=%s",
            client_id,
            os_msg_id,
            exc_info=True,
        )
        return {"status": f"error:{str(exc)[:200]}"}
