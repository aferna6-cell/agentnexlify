"""Missed-call recovery — voicemail becomes an Agent OS callback draft (G3 P1).

After a voicemail is transcribed and summarized, the AI staff drafts a
personalized text back to the caller and files it through the EXISTING
Agent OS approval flow:

  - an os_threads row ("Missed call from ...") so the owner sees the
    voicemail summary as a conversation in the OS,
  - an os_agent_runs row (agent_name='lead_nurture') carrying the SMS
    draft as a deliverable. resolve_deliverable_status decides
    pending_approval vs auto-send exactly like every other draft — the
    owner's per-agent auto-send rules (G6) apply, and auto-approved
    drafts dispatch through os_action_dispatch immediately.

Deterministic-first: the draft text is composed from the summary the
call pipeline already produced — no extra LLM call.

Schema notes: os_* tables use client_id; every step is fault-tolerant —
a failure here never breaks the Twilio webhook that triggered it.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.agent_os_bridge import resolve_deliverable_status
from backend.services.os_action_dispatch import queue_action_for_run
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_TRANSCRIPT_EXCERPT_CHARS = 400


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compose_callback_text(
    business_name: str, summary: str, follow_up: str
) -> str:
    """Deterministic SMS draft from the call-summary pipeline's output."""
    base = f"Hi, this is {business_name}. Sorry we missed your call!"
    detail = (follow_up or "").strip() or (summary or "").strip()
    if detail:
        # Keep SMS-sized; the owner edits before approving if needed.
        detail = detail[:280]
        return f"{base} {detail} Reply here or call us back anytime."
    return f"{base} How can we help? Reply here or call us back anytime."


async def create_missed_call_followup(
    db: Any,
    *,
    tenant_id: str,
    business_name: str,
    caller: str,
    call_id: str | None,
    lead_id: str | None,
    summary: str,
    follow_up: str,
    transcript_excerpt: str = "",
) -> str | None:
    """File the callback-text draft into the Agent OS. Returns run id or None."""
    if not caller:
        return None

    # 1. OS thread so the owner sees the voicemail in their staff inbox
    thread_id = None
    try:
        thread = (
            tenant_table(db, "os_threads", tenant_id)
            .insert(
                {
                    "title": f"Missed call from {caller}",
                    "source": "voice",
                    "status": "open",
                    "created_by": "system",
                }
            )
            .execute()
        )
        thread_id = thread.data[0]["id"] if thread.data else None
    except Exception:
        logger.warning(
            "voice_recovery: thread insert failed tenant=%s", tenant_id, exc_info=True
        )

    if thread_id:
        try:
            excerpt = (transcript_excerpt or "").strip()[:_TRANSCRIPT_EXCERPT_CHARS]
            content = f"Voicemail from {caller}."
            if summary:
                content += f"\n\nSummary: {summary}"
            if excerpt:
                content += f'\n\nThey said: "{excerpt}"'
            tenant_table(db, "os_messages", tenant_id).insert(
                {
                    "thread_id": thread_id,
                    "role": "user",
                    "content": content,
                    "inbound_kind": "voicemail",
                    "source_ref": call_id,
                }
            ).execute()
        except Exception:
            logger.warning(
                "voice_recovery: message insert failed tenant=%s",
                tenant_id,
                exc_info=True,
            )

    # 2. The deliverable — same shape the engine produces, same approval gate
    sms_body = compose_callback_text(business_name, summary, follow_up)
    deliverable = {
        "title": f"Text back {caller} about their voicemail",
        "body": f"{sms_body}\n\nRecipient: {caller}",
        "channel": "sms",
        "metadata": {
            "recipient": caller,
            "call_id": call_id,
            "lead_id": lead_id,
            "source": "missed_call_recovery",
        },
    }
    deliverable_status = resolve_deliverable_status(
        db, tenant_id, "lead_nurture", requires_approval=False
    )

    run_row: dict[str, Any] = {
        "agent_name": "lead_nurture",
        "status": "succeeded",
        "action_type": "sms.send",
        "deliverable": deliverable,
        "deliverable_status": deliverable_status,
        "completed_at": _now(),
        "thought_process": [
            {
                "step": "missed_call_recovery",
                "detail": "Drafted callback text from voicemail transcription",
            }
        ],
    }
    if thread_id:
        run_row["thread_id"] = thread_id

    try:
        created = (
            tenant_table(db, "os_agent_runs", tenant_id).insert(run_row).execute()
        )
        run = created.data[0] if created.data else None
    except Exception:
        logger.warning(
            "voice_recovery: run insert failed tenant=%s", tenant_id, exc_info=True
        )
        return None
    if not run:
        return None

    # 3. Auto-approved (per G6 rules) -> dispatch now; else it waits in the
    #    pending-approvals UI like any other draft.
    if deliverable_status == "approved":
        try:
            await queue_action_for_run(db, tenant_id, run, background=None)
        except Exception:
            logger.warning(
                "voice_recovery: auto-send dispatch failed tenant=%s run=%s",
                tenant_id,
                run.get("id"),
                exc_info=True,
            )

    logger.info(
        "voice_recovery: filed callback draft tenant=%s run=%s status=%s",
        tenant_id,
        run.get("id"),
        deliverable_status,
    )
    return run.get("id")
