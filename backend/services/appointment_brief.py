"""Pre-appointment briefs + post-appointment follow-up drafts.

Gives the owner a one-page brief before each appointment (who the customer
is, what they asked about in chat, suggested talking points) and an
AI-drafted follow-up email after it. Drafts are returned for approval —
nothing here ever sends.

Schema notes: appointments use tenant_id; leads/conversations use client_id
(handled via tenant_scope helpers — see .claude/rules/schema-discipline.md).
"""

import logging
from typing import Any

from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

BRIEF_MODEL = "claude-sonnet-5"
_TRANSCRIPT_MESSAGES = 30
_TRANSCRIPT_CHARS = 4000


class AppointmentBriefError(Exception):
    """Raised when the brief context cannot be assembled (maps to 4xx)."""


class AppointmentBudgetExceeded(Exception):
    """Raised when the monthly AI hard cap blocks the Claude call (maps to 429)."""


class AppointmentBudgetGuardUnavailable(Exception):
    """Raised when tenant/policy cannot be loaded (maps to 503, not 429)."""


def _load_budget_tenant(db: Any, tenant_id: str) -> dict[str, Any] | None:
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
            "appointment brief tenant load failed tenant=%s",
            tenant_id,
        )
        return None
    if not rows:
        logger.warning(
            "appointment brief tenant missing tenant=%s — failing closed before provider",
            tenant_id,
        )
        return None
    return {**rows[0], "id": tenant_id}


async def _call_claude_with_budget(
    *,
    db: Any,
    tenant_id: str,
    appointment_id: str,
    operation: str,
    system: str,
    user_content: str,
    max_tokens: int,
):
    """Reserve → Claude → record, or release on provider/error.

    llm_runtime only times/logs the provider call. Reservation + recording
    live here so appointment spend uses the same contract as widget chat.

    Tenant/policy load failure fails closed here (no provider call). A
    later reserve RPC outage is different: reserve_ai_tokens returns
    allowed=True / reason=guard_unavailable and the shared helper may
    still call the provider without persisting usage.
    """
    messages = [{"role": "user", "content": user_content}]
    tenant = _load_budget_tenant(db, tenant_id)
    if tenant is None:
        logger.warning(
            "appointment brief budget tenant unavailable tenant=%s op=%s — "
            "failing closed before provider",
            tenant_id,
            operation,
        )
        raise AppointmentBudgetGuardUnavailable(
            "AI usage guard unavailable — tenant policy could not be loaded"
        )
    reservation = reserve_ai_tokens(
        tenant=tenant,
        estimated_tokens=estimate_widget_chat_tokens(
            system_prompt=system,
            messages=messages,
            max_tokens=max_tokens,
        ),
        operation=operation,
        session_id=appointment_id,
    )
    if not reservation.allowed:
        raise AppointmentBudgetExceeded(
            "Monthly AI usage limit reached — add a usage pack or wait for the next cycle"
        )

    try:
        resp = await call_claude_messages(
            operation=operation,
            model=BRIEF_MODEL,
            max_tokens=max_tokens,
            temperature=0,
            timeout=20.0,
            system=system,
            messages=messages,
            metadata={"tenant_id": tenant_id, "appointment_id": appointment_id},
        )
    except Exception:
        if reservation is not None:
            release_ai_token_reservation(reservation)
        raise

    if reservation is not None:
        record_ai_usage(
            reservation=reservation,
            result=resp,
            operation=operation,
            session_id=appointment_id,
            model=BRIEF_MODEL,
        )
    return resp


def gather_context(db: Any, tenant_id: str, appointment_id: str) -> dict[str, Any]:
    """Collect the appointment, its linked lead, and the chat transcript.

    Raises AppointmentBriefError when the appointment does not exist.
    Lead and transcript are optional — a walk-in booking with no chat
    history still gets a (thinner) brief.
    """
    appt_rows = (
        tenant_select(
            db,
            "appointments",
            tenant_id,
            "id, customer_name, customer_email, customer_phone, start_time, "
            "end_time, status, notes, lead_id",
        )
        .eq("id", appointment_id)
        .limit(1)
        .execute()
    ).data or []
    if not appt_rows:
        raise AppointmentBriefError("Appointment not found")
    appointment = appt_rows[0]

    lead: dict[str, Any] = {}
    transcript = ""
    lead_id = appointment.get("lead_id")
    if lead_id:
        lead_rows = (
            tenant_select(
                db,
                "leads",
                tenant_id,
                "id, name, email, phone, status, areas_of_interest, "
                "conversation_summary, conversation_id, created_at",
            )
            .eq("id", lead_id)
            .limit(1)
            .execute()
        ).data or []
        lead = lead_rows[0] if lead_rows else {}

        conv_id = lead.get("conversation_id")
        if conv_id:
            conv_rows = (
                tenant_select(db, "conversations", tenant_id, "messages")
                .eq("id", conv_id)
                .limit(1)
                .execute()
            ).data or []
            messages = (conv_rows[0].get("messages") or []) if conv_rows else []
            transcript = "\n".join(
                f"{'Visitor' if m.get('role') == 'user' else 'Agent'}: {m.get('content', '')}"
                for m in messages[-_TRANSCRIPT_MESSAGES:]
            )[:_TRANSCRIPT_CHARS]

    return {"appointment": appointment, "lead": lead, "transcript": transcript}


def _context_block(context: dict[str, Any], business_name: str) -> str:
    appt = context["appointment"]
    lead = context["lead"]
    lines = [
        f"Business: {business_name or 'this business'}",
        f"Customer: {appt.get('customer_name') or 'Unknown'}",
        f"Appointment: {appt.get('start_time') or 'unscheduled'}",
    ]
    if appt.get("notes"):
        lines.append(f"Booking notes: {appt['notes']}")
    if lead:
        if lead.get("status"):
            lines.append(f"Lead status: {lead['status']}")
        if lead.get("areas_of_interest"):
            lines.append(f"Interested in: {lead['areas_of_interest']}")
        if lead.get("conversation_summary"):
            lines.append(f"Earlier summary: {lead['conversation_summary']}")
    if context["transcript"]:
        lines.append("Chat transcript:\n" + context["transcript"])
    else:
        lines.append("No chat history on file for this customer.")
    return "\n".join(lines)


async def generate_brief(
    db: Any, tenant_id: str, appointment_id: str, business_name: str = ""
) -> dict[str, Any]:
    """One-page brief for an upcoming appointment.

    Returns {brief, has_history} — brief is markdown the dashboard renders.
    """
    context = gather_context(db, tenant_id, appointment_id)
    system = (
        "You brief a small-business owner before a customer appointment. "
        "From the context, write a compact markdown brief with exactly "
        "three sections: '## Who they are' (1-2 sentences), "
        "'## What they want' (what they asked about, decisions made), "
        "'## Talking points' (3 short bullets — questions to ask or "
        "things to confirm). Only use facts from the context; if history "
        "is thin, say so and keep it short. No preamble."
    )
    resp = await _call_claude_with_budget(
        db=db,
        tenant_id=tenant_id,
        appointment_id=appointment_id,
        operation="appointments.brief",
        system=system,
        user_content=_context_block(context, business_name),
        max_tokens=500,
    )
    return {"brief": resp.text.strip(), "has_history": bool(context["transcript"])}


async def draft_followup(
    db: Any, tenant_id: str, appointment_id: str, business_name: str = ""
) -> dict[str, Any]:
    """Draft (never send) a post-appointment follow-up email.

    Returns {subject, body, customer_email} for the owner to review, edit,
    and send from their own flow — approval-first by design.
    """
    context = gather_context(db, tenant_id, appointment_id)
    appt = context["appointment"]
    system = (
        "Draft a short, warm follow-up email from a small business to a "
        "customer after their appointment. Reference what they came in "
        "for when the context shows it. Invite questions and a next "
        "step. Plain text, under 120 words, no placeholders like "
        "[NAME] — use the real names from the context. First line must "
        "be 'Subject: <subject>' followed by a blank line, then the body."
    )
    resp = await _call_claude_with_budget(
        db=db,
        tenant_id=tenant_id,
        appointment_id=appointment_id,
        operation="appointments.followup_draft",
        system=system,
        user_content=_context_block(context, business_name),
        max_tokens=400,
    )
    subject, body = _split_subject(resp.text.strip())
    return {
        "subject": subject,
        "body": body,
        "customer_email": appt.get("customer_email"),
    }


def _split_subject(text: str) -> tuple[str, str]:
    """Split a 'Subject: ...' first line from the body; tolerate absence."""
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
        return subject or "Following up on your appointment", body
    return "Following up on your appointment", text
