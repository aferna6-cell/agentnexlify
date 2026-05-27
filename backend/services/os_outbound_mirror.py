"""Agent OS outbound mirror — Group C bi-directional sync.

When the OS orchestrator produces an assistant reply on a thread that was
opened by an inbound channel (widget/email/sms/facebook), the customer reads
from the legacy channel store, not from ``os_messages``. Without a mirror
hop the customer never sees the OS reply.

Phase 1 (shipped): widget threads → ``chat_messages`` (DB write only —
the widget polls ``chat_messages`` already).

Phase 2 (this module, SMS + email shipped): outbound SMS via tenant's
Twilio subaccount (preferred) with fallback to the platform pool, plus
outbound email via Resend with ``In-Reply-To`` / ``References`` headers
threaded against the original inbound message id. Facebook still returns
``skipped:outbound_not_implemented`` until its phase-2 outbound sender
lands.

Idempotency: the widget mirror tags ``chat_messages`` rows with
``os_message_id``; a replay finds the existing row and reports
``skipped:already_mirrored``. SMS outbound has no DB mirror row — the
runner calls this function exactly once per orchestrator turn, so
in-process idempotency is the caller's responsibility. Cross-process
replay protection for SMS is a phase-3 concern (`os_outbound_log`).

Failure semantics: NEVER raise. Mirror is best-effort; the OS reply is
already persisted in ``os_messages``. A failed mirror returns
``error:<reason>`` so the caller can log and continue.

STOP-keyword guard: if the inbound that opened or last touched the thread
was a TCPA STOP keyword (``stop_keyword=True`` in ``source_metadata``),
SMS outbound is skipped with ``skipped:stop_keyword``. Sending after
unsubscribe is a compliance violation, not a transport failure.
"""

import logging
from typing import Any

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


async def mirror_assistant_message(
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
        ``{"status": <one of>, ...}`` — never raises. Statuses:
          - ``mirrored`` — successfully delivered to the channel
          - ``skipped:no_channel`` — owner thread, no inbound source
          - ``skipped:no_session`` — channel source but no recipient identifier
          - ``skipped:empty_content`` — assistant reply was blank
          - ``skipped:stop_keyword`` — recipient sent STOP; outbound suppressed
          - ``skipped:outbound_not_implemented`` — email/facebook (phase 2 pending)
          - ``skipped:already_mirrored`` — widget replay of an already-mirrored OS message
          - ``error:<reason>`` — DB failure, provider failure, or unexpected exception
    """
    source = thread.get("source")
    if not source:
        return {"status": "skipped:no_channel"}

    if source == "widget":
        return _mirror_widget(db, client_id, thread, assistant_message)

    if source == "sms":
        return await _mirror_sms(client_id, thread, assistant_message)

    if source == "email":
        return await _mirror_email(client_id, thread, assistant_message)

    return {"status": "skipped:outbound_not_implemented"}


def _mirror_widget(
    db: Any,
    client_id: str,
    thread: dict,
    assistant_message: dict,
) -> dict:
    """Insert the OS reply into ``chat_messages`` so the widget polls it."""
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
            "os_outbound_mirror: widget mirror failed client_id=%s os_msg=%s",
            client_id,
            os_msg_id,
            exc_info=True,
        )
        return {"status": f"error:{str(exc)[:200]}"}


async def _mirror_sms(
    client_id: str,
    thread: dict,
    assistant_message: dict,
) -> dict:
    """Send the OS reply as an outbound SMS via tenant Twilio (BYO → platform)."""
    meta = thread.get("source_metadata") or {}
    if not isinstance(meta, dict):
        return {"status": "skipped:no_session"}

    if meta.get("stop_keyword"):
        return {"status": "skipped:stop_keyword"}

    to_phone = meta.get("from") or meta.get("sender_phone")
    if not to_phone:
        return {"status": "skipped:no_session"}

    content = (assistant_message.get("content") or "").strip()
    if not content:
        return {"status": "skipped:empty_content"}

    # Lazy imports keep the mirror module decoupled from Twilio at import
    # time — tests that don't exercise SMS never trigger settings/httpx
    # initialization.
    try:
        from backend.services.twilio_service import send_sms as send_sms_platform
        from backend.services.twilio_tenant import (
            is_connected as twilio_byo_connected,
            send_sms_via_tenant,
        )
    except Exception as exc:
        logger.warning(
            "os_outbound_mirror: twilio import failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return {"status": f"error:sms_send:import:{str(exc)[:160]}"}

    try:
        use_byo = bool(twilio_byo_connected(client_id))
    except Exception:
        logger.warning(
            "os_outbound_mirror: twilio_byo connectivity check failed client_id=%s",
            client_id,
            exc_info=True,
        )
        use_byo = False

    try:
        if use_byo:
            result = await send_sms_via_tenant(
                tenant_id=client_id, to=to_phone, body=content
            )
            if result.get("success"):
                return {
                    "status": "mirrored",
                    "provider": "twilio_byo",
                    "message_sid": result.get("message_sid", ""),
                }
            detail = (result.get("detail") or "byo send reported failure")[:200]
            return {"status": f"error:sms_send:{detail}"}

        sent = await send_sms_platform(to=to_phone, body=content)
        if sent:
            return {"status": "mirrored", "provider": "twilio_platform"}
        return {"status": "error:sms_send:platform_send_failed"}
    except Exception as exc:
        logger.warning(
            "os_outbound_mirror: sms send failed client_id=%s os_msg=%s",
            client_id,
            assistant_message.get("id"),
            exc_info=True,
        )
        return {"status": f"error:sms_send:{str(exc)[:200]}"}


async def _mirror_email(
    client_id: str,
    thread: dict,
    assistant_message: dict,
) -> dict:
    """Send the OS reply as a threaded email via Resend.

    Threading: ``In-Reply-To`` and ``References`` are set from the
    originating inbound message id (stored on the thread row as
    ``source_thread_id``). The customer's mail client groups the reply
    with the original inbound thread.

    Subject: prepends ``Re: `` when the inbound subject doesn't already
    start with one (case-insensitive). Empty inbound subject falls back
    to ``Re: your message``.
    """
    meta = thread.get("source_metadata") or {}
    if not isinstance(meta, dict):
        return {"status": "skipped:no_session"}

    to_addr = meta.get("from") or meta.get("sender_email")
    if not to_addr:
        return {"status": "skipped:no_session"}

    content = (assistant_message.get("content") or "").strip()
    if not content:
        return {"status": "skipped:empty_content"}

    inbound_subject = (meta.get("subject") or "").strip()
    if inbound_subject:
        subject = (
            inbound_subject
            if inbound_subject.lower().startswith("re:")
            else f"Re: {inbound_subject}"
        )
    else:
        subject = "Re: your message"

    in_reply_to = thread.get("source_thread_id") or ""

    try:
        from backend.services.email_sender import send_email_reply
    except Exception as exc:
        logger.warning(
            "os_outbound_mirror: email_sender import failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return {"status": f"error:email_send:import:{str(exc)[:160]}"}

    try:
        result = await send_email_reply(
            to=to_addr,
            subject=subject,
            body_text=content,
            tenant_id=client_id,
            in_reply_to=in_reply_to,
        )
        if result.get("success"):
            return {
                "status": "mirrored",
                "provider": "resend",
                "resend_id": result.get("resend_id", ""),
            }
        detail = (result.get("detail") or "resend reported failure")[:200]
        return {"status": f"error:email_send:{detail}"}
    except Exception as exc:
        logger.warning(
            "os_outbound_mirror: email send failed client_id=%s os_msg=%s",
            client_id,
            assistant_message.get("id"),
            exc_info=True,
        )
        return {"status": f"error:email_send:{str(exc)[:200]}"}
