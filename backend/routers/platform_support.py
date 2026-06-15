"""Public support chatbot for the AgentNexLiFy marketing site.

The widget embedded on agentnexlify.com lets visitors ask product questions and
report issues. Three endpoints:

- ``POST /chat``   answer a message (Claude), store it, email the owner on the
  first message of a session.
- ``POST /report`` a visitor explicitly reports an issue with their email —
  emails the owner immediately with the transcript attached.
- ``POST /end``    widget close beacon — emails the owner the full transcript
  once per session (idempotent).

These are platform-level (not tenant-scoped) — the operator's own support inbox.
All Claude/email work is best-effort and never 500s the visitor.
"""

import html
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, EmailStr

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.platform_mailer import send_platform_email, text_attachment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/platform-support", tags=["platform-support"])

_MAX_CONTENT = 4000
_HISTORY_LIMIT = 20

_FALLBACK_REPLY = (
    "Sorry — I'm having trouble right now. Email help@agentnexlify.com or use "
    "“Report an issue” and the team will follow up."
)

SUPPORT_SYSTEM_PROMPT = """You are the support assistant for AgentNexLiFy, an \
AI-powered customer-service and lead-capture platform for small businesses. Help \
visitors with questions about the product and let them report issues.

What AgentNexLiFy does:
- An embeddable AI chat widget that answers customer questions, captures leads, \
books appointments, and automates follow-ups.
- A dashboard to manage leads, conversations, appointments, and automations.

Plans:
- Free: chat widget, lead capture, FAQ knowledge base, up to 50 conversations/month.
- Growth $99/mo: 7-day free trial, booking, SMS, automation, basic SEO, AI content writer.
- Professional $150/mo: full SEO suite, social media marketing, email/SMS campaigns, advanced analytics.
- Enterprise $250/mo: AI visibility tracking, team accounts, webhooks, white-label branding.

Guidelines:
- Be concise, direct, and friendly. Short answers.
- Answer from the facts above and general product knowledge. When you do not \
know, say so and invite the visitor to describe the issue so the team can follow up.
- When the visitor reports a bug or wants a human, ask for their email and a \
short description so the team can reach them.
- You cannot access account data or make account changes."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_transcript(messages: list[dict[str, Any]]) -> str:
    lines = []
    for m in messages:
        role = (m.get("role") or "?").upper()
        ts = m.get("created_at") or ""
        content = (m.get("content") or "").strip()
        lines.append(f"[{ts}] {role}:\n{content}\n")
    return "\n".join(lines) if lines else "(no messages found)"


# --- request / response models ---------------------------------------------


class ChatRequest(BaseModel):
    session_id: str
    message: str
    page_url: str | None = None


class ChatResponse(BaseModel):
    reply: str


class ReportRequest(BaseModel):
    session_id: str
    email: EmailStr
    message: str
    page_url: str | None = None


class EndRequest(BaseModel):
    session_id: str


class AckResponse(BaseModel):
    ok: bool
    message: str = ""


# --- AI reply ----------------------------------------------------------------


async def _generate_reply(messages: list[dict[str, str]]) -> str:
    try:
        result = await call_claude_messages(
            operation="platform_support_chat",
            model=settings.widget_chat_model,
            max_tokens=400,
            system=SUPPORT_SYSTEM_PROMPT,
            messages=messages,
            temperature=0.3,
            timeout=20.0,
        )
        return (result.text or "").strip() or _FALLBACK_REPLY
    except Exception:
        logger.warning("platform_support: claude call failed", exc_info=True)
        return _FALLBACK_REPLY


# --- email helpers (best-effort, never raise) --------------------------------


async def _notify_new_chat(session_id: str, first_message: str, page_url: str | None) -> None:
    try:
        body = (
            "<p>A new support conversation just started on the AgentNexLiFy site.</p>"
            f"<p><strong>First message:</strong><br>{html.escape(first_message)}</p>"
        )
        if page_url:
            body += f"<p><strong>Page:</strong> {html.escape(page_url)}</p>"
        body += f"<p><strong>Session:</strong> {html.escape(session_id)}</p>"
        await send_platform_email(
            subject="[Support chat] New conversation", body_html=body
        )
    except Exception:
        logger.warning("platform_support: new-chat notify failed", exc_info=True)


async def _email_report(
    session_id: str, email: str, message: str, page_url: str | None
) -> None:
    try:
        db = get_service_supabase()
        msgs = (
            db.table("platform_support_messages")
            .select("role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        body = (
            "<p>A visitor reported an issue via the AgentNexLiFy support chat.</p>"
            f"<p><strong>From:</strong> {html.escape(email)}</p>"
            "<p><strong>Issue:</strong><br>"
            f"{html.escape(message).replace(chr(10), '<br>')}</p>"
        )
        if page_url:
            body += f"<p><strong>Page:</strong> {html.escape(page_url)}</p>"
        attachment = text_attachment(
            f"support-chat-{session_id}.txt", _build_transcript(msgs)
        )
        await send_platform_email(
            subject=f"[Support issue] {email}"[:120],
            body_html=body,
            attachments=[attachment],
            reply_to=email,
        )
        db.table("platform_support_sessions").update({"reporter_email": email}).eq(
            "session_id", session_id
        ).execute()
    except Exception:
        logger.warning("platform_support: report email failed", exc_info=True)


async def _email_transcript_once(session_id: str) -> None:
    """Email the full transcript once per session (idempotent)."""
    try:
        db = get_service_supabase()
        rows = (
            db.table("platform_support_sessions")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return
        session = rows[0]
        if session.get("transcript_sent_at"):
            return
        msgs = (
            db.table("platform_support_messages")
            .select("role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        if not any(m.get("role") == "user" for m in msgs):
            return
        # Claim the idempotency slot before sending so a duplicate close beacon
        # can't double-send the transcript.
        db.table("platform_support_sessions").update(
            {"transcript_sent_at": _now()}
        ).eq("session_id", session_id).execute()

        body = (
            "<p>A support conversation on the AgentNexLiFy site ended.</p>"
            f"<p><strong>Messages:</strong> {len(msgs)}</p>"
        )
        if session.get("page_url"):
            body += f"<p><strong>Page:</strong> {html.escape(session['page_url'])}</p>"
        if session.get("reporter_email"):
            body += (
                "<p><strong>Reporter email:</strong> "
                f"{html.escape(session['reporter_email'])}</p>"
            )
        attachment = text_attachment(
            f"support-chat-{session_id}.txt", _build_transcript(msgs)
        )
        await send_platform_email(
            subject="[Support chat] Conversation transcript",
            body_html=body,
            attachments=[attachment],
        )
    except Exception:
        logger.warning("platform_support: transcript email failed", exc_info=True)


# --- endpoints ---------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def platform_support_chat(
    payload: ChatRequest, request: Request, background_tasks: BackgroundTasks
):
    session_id = (payload.session_id or "").strip()
    message = (payload.message or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    db = get_service_supabase()
    existing = (
        db.table("platform_support_sessions")
        .select("session_id")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    is_new = not existing
    now = _now()
    if is_new:
        db.table("platform_support_sessions").insert(
            {
                "session_id": session_id,
                "page_url": payload.page_url,
                "started_at": now,
                "last_activity_at": now,
            }
        ).execute()
    else:
        db.table("platform_support_sessions").update({"last_activity_at": now}).eq(
            "session_id", session_id
        ).execute()

    db.table("platform_support_messages").insert(
        {"session_id": session_id, "role": "user", "content": message[:_MAX_CONTENT]}
    ).execute()

    history = (
        db.table("platform_support_messages")
        .select("role, content")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .limit(_HISTORY_LIMIT)
        .execute()
        .data
        or []
    )
    messages = [{"role": h["role"], "content": h["content"]} for h in history]

    reply = await _generate_reply(messages)

    db.table("platform_support_messages").insert(
        {"session_id": session_id, "role": "assistant", "content": reply}
    ).execute()

    if is_new:
        background_tasks.add_task(
            _notify_new_chat, session_id, message, payload.page_url
        )

    return ChatResponse(reply=reply)


@router.post("/report", response_model=AckResponse)
@limiter.limit("10/minute")
async def platform_support_report(
    payload: ReportRequest, request: Request, background_tasks: BackgroundTasks
):
    session_id = (payload.session_id or "").strip()
    message = (payload.message or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    db = get_service_supabase()
    # Ensure a session row exists so the report attaches to a transcript.
    existing = (
        db.table("platform_support_sessions")
        .select("session_id")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not existing:
        db.table("platform_support_sessions").insert(
            {"session_id": session_id, "page_url": payload.page_url}
        ).execute()
    db.table("platform_support_messages").insert(
        {
            "session_id": session_id,
            "role": "user",
            "content": f"[ISSUE REPORT from {payload.email}] {message}"[:_MAX_CONTENT],
        }
    ).execute()

    background_tasks.add_task(
        _email_report, session_id, str(payload.email), message, payload.page_url
    )
    return AckResponse(
        ok=True,
        message="Thanks — your report is on its way. We'll email you back.",
    )


@router.post("/end", response_model=AckResponse)
@limiter.limit("30/minute")
async def platform_support_end(
    payload: EndRequest, request: Request, background_tasks: BackgroundTasks
):
    session_id = (payload.session_id or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    background_tasks.add_task(_email_transcript_once, session_id)
    return AckResponse(ok=True)
