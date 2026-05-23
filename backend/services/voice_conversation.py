"""Voice conversation orchestration for the calls router.

Pulled out of `backend.routers.calls` so the router stays focused on Twilio
TwiML I/O. Functions here own conversation history loading, business-context
loading, system-prompt building, and the Claude LLM call for voice replies.
"""

import logging

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)

logger = logging.getLogger(__name__)


def save_voice_message(tenant_id: str, session_id: str, role: str, content: str) -> None:
    """Persist a single voice-conversation message to chat_messages."""
    db = get_service_supabase()
    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": role,
            "content": content,
        }).execute()
    except Exception:
        logger.exception(
            "Failed to save voice message (tenant=%s role=%s)", tenant_id, role
        )


def load_voice_history(
    tenant_id: str,
    session_id: str,
    fallback_message: str,
) -> list[dict[str, str]]:
    """Load and compact conversation history from chat_messages.

    Returns a compact list of role/content dicts truncated to the configured
    history window. On DB error falls back to a single-message list containing
    only the caller's current utterance.
    """
    db = get_service_supabase()
    messages: list[dict[str, str]] = []
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
            messages.append({"role": msg["role"], "content": msg["content"]})
    except Exception:
        logger.exception(
            "Failed to load conversation history (tenant=%s session=%s)",
            tenant_id, session_id,
        )
        messages = [{"role": "user", "content": fallback_message}]

    history_limit = resolve_int_setting("widget_prompt_history_messages", 8)
    message_chars = min(resolve_int_setting("widget_prompt_message_chars", 420), 320)
    compact: list[dict[str, str]] = []
    for msg in messages[-history_limit:]:
        content = (msg.get("content") or "").strip()
        if len(content) > message_chars:
            content = content[: message_chars - 3].rstrip() + "..."
        compact.append({
            "role": msg.get("role") or "user",
            "content": content,
        })
    return compact


def load_voice_business_context(tenant_id: str) -> tuple[str, str]:
    """Return (business_info, faq_text) used in the voice AI system prompt."""
    db = get_service_supabase()
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

    return business_info, faq_text


def build_voice_system_prompt(business_name: str, business_info: str, faq_text: str) -> str:
    """Compose the voice AI system prompt from tenant context + FAQ."""
    prompt = (
        f"You are a helpful phone assistant for {business_name}. {business_info}"
        "You are speaking with a caller on the phone. Keep your responses concise "
        "and conversational -- ideally 1-3 sentences since this will be spoken aloud. "
        "Be warm and helpful. If you don't know the answer, offer to have someone "
        "call them back. Never say you are an AI unless directly asked."
    )
    if faq_text:
        prompt += f"\n\n{faq_text}"
    return prompt


async def generate_voice_response(
    tenant_id: str,
    call_sid: str,
    round_num: int,
    system_prompt: str,
    messages: list[dict[str, str]],
    faq_chars: int,
) -> str:
    """Call Claude for the voice AI response. Returns text or safe fallback."""
    try:
        llm_result = await call_claude_messages(
            operation="calls.voice_respond",
            model=resolve_string_setting("voice_chat_model", "claude-sonnet-4-6"),
            max_tokens=resolve_int_setting("voice_chat_max_tokens", 160),
            system=system_prompt,
            messages=messages,
            temperature=0.0,
            timeout=30.0,
            metadata={
                "tenant_id": tenant_id,
                "call_sid": call_sid,
                "round": round_num,
                "history_count": len(messages),
                "faq_chars": faq_chars,
            },
        )
        ai_response = llm_result.text.strip()
        logger.info(
            "voice_respond: llm_result call_sid=%s round=%d llm_ms=%d response_chars=%d",
            call_sid,
            round_num,
            llm_result.duration_ms,
            len(ai_response),
        )
        return ai_response
    except Exception:
        logger.exception("Claude API call failed for voice respond, call %s", call_sid)
        return (
            "I'm sorry, I'm having a little trouble right now. "
            "Let me have someone call you back as soon as possible."
        )
