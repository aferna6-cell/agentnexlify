"""Pre-LLM guard stages for the widget chat pipeline (issue #472 split).

Each guard inspects the incoming turn and either short-circuits it with a
finished `WidgetChatResponse` (returned to the visitor without ever paying
for a Claude call) or returns None so the pipeline continues. Moved
verbatim from the widget_chat route body; the route orchestrates the order:

    handoff-mode -> content-mode -> junk/greeting -> null-state ->
    turn-budget -> input-screen

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
import re

from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetChatRequest, WidgetChatResponse
from backend.services.widget_guard import check_turn_budget, screen_widget_input
from backend.routers.widget_chat_helpers import (
    _CHAT_CACHE_TTL,
    _get_cached,
    _save_chat_messages,
    _set_cache,
)

logger = logging.getLogger(__name__)

_CONTENT_MODE_KEYWORDS = [
    "repurpose",
    "content mode",
    "turn this into",
    "create content from",
]
_YT_PATTERN = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")

_GREETINGS = {"hi", "hey", "hello", "yo", "sup", "hiya", "howdy", "hii", "helo"}


def early_watermark(tenant: dict, widget: dict) -> bool:
    """Watermark shown on short-circuited turns (free plan always shows it)."""
    is_free = (tenant.get("plan") or "free") == "free"
    return True if is_free else widget.get("show_watermark", True)


def check_handoff_mode(
    db, tenant: dict, widget: dict, req: WidgetChatRequest
) -> WidgetChatResponse | None:
    """Stage 4b — conversation tagged 'handoff': a team member owns it.

    Saves the user message, surfaces the latest team reply if one exists,
    otherwise returns the canned waiting message. Never calls Claude.
    """
    handoff_active = False
    try:
        conv_tags = (
            db.table("conversations")
            .select("tags")
            .eq("client_id", tenant["id"])
            .eq("session_id", req.session_id)
            .limit(1)
            .execute()
        )
        if conv_tags.data:
            tags = conv_tags.data[0].get("tags") or []
            handoff_active = "handoff" in tags
    except Exception:
        logger.warning(
            "handoff check failed for session %s", req.session_id, exc_info=True
        )

    if not handoff_active:
        return None

    # Save user message, skip Claude, return waiting message
    _save_chat_messages(tenant["id"], req.session_id, req.message, None)
    # Check for any team replies since last user message
    try:
        recent = (
            db.table("chat_messages")
            .select("content, created_at")
            .eq("tenant_id", tenant["id"])
            .eq("session_id", req.session_id)
            .eq("role", "assistant")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent.data:
            last_reply = recent.data[0]["content"]
            # If the last assistant message is NOT the handoff message, it's a team reply
            if last_reply and "team member" not in last_reply.lower():
                return WidgetChatResponse(
                    response=last_reply,
                    session_id=req.session_id,
                    lead_captured=False,
                    show_watermark=widget.get("show_watermark", True),
                    handoff=True,
                )
    except Exception:
        logger.warning(
            "Failed to fetch latest team reply for session %s",
            req.session_id,
            exc_info=True,
        )

    waiting_msg = "A team member is reviewing your conversation and will respond shortly. Thank you for your patience."
    _save_chat_messages(tenant["id"], req.session_id, None, waiting_msg)
    return WidgetChatResponse(
        response=waiting_msg,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=widget.get("show_watermark", True),
        handoff=True,
    )


async def maybe_run_content_mode(
    db, tenant: dict, widget: dict, req: WidgetChatRequest
) -> WidgetChatResponse | None:
    """Stage 4c — content-mode detection: repurpose content instead of chat.

    Plan-gated to professional/enterprise; runs the repurposer inline and
    stores a repurpose_jobs row. Returns None when the message is a normal
    chat turn.
    """
    msg_lower = req.message.lower()
    content_mode = req.content_mode
    if not content_mode:
        for kw in _CONTENT_MODE_KEYWORDS:
            if kw in msg_lower:
                content_mode = True
                break
    if not content_mode and _YT_PATTERN.search(req.message):
        content_mode = True
    if not content_mode and len(req.message) > 500 and "?" not in req.message:
        content_mode = True

    if not content_mode:
        return None

    plan = tenant.get("plan") or "free"
    if plan not in ("professional", "enterprise"):
        _save_chat_messages(tenant["id"], req.session_id, req.message, None)
        return WidgetChatResponse(
            response="Content repurposing is available on Professional and Enterprise plans. Upgrade to unlock this feature!",
            session_id=req.session_id,
            lead_captured=False,
            show_watermark=widget.get("show_watermark", True),
        )
    # Determine source type
    if _YT_PATTERN.search(req.message):
        src_type = "youtube"
    elif req.message.strip().startswith(("http://", "https://")):
        src_type = "url"
    else:
        src_type = "text"
    # Create repurpose job
    try:
        from backend.services.content_repurposer import (
            extract_source,
            repurpose as do_repurpose,
        )

        source = await extract_source(src_type, req.message.strip())
        outputs = await do_repurpose(
            source_content=source["content"],
            title=source["title"],
            tenant_id=tenant["id"],
            tone="professional",
        )
        db.table("repurpose_jobs").insert(
            {
                "tenant_id": tenant["id"],
                "source_type": src_type,
                "source_url": source["source_url"],
                "source_content": source["content"],
                "source_title": source["title"],
                "outputs": outputs,
                "status": "completed",
                "created_via": "widget",
            }
        ).execute()
        resp_text = (
            f"Done! I've repurposed \"{source['title']}\" into:\n\n"
            "- X/Twitter thread (7-10 tweets)\n"
            "- LinkedIn carousel\n"
            "- Email sequence (3-5 emails)\n"
            "- TikTok/Reels scripts\n"
            "- Social posts (Facebook, Instagram, Google Business)\n\n"
            "View and edit your results in the Content Repurpose page on your dashboard."
        )
    except Exception as e:
        logger.error("Content mode repurpose failed: %s", e, exc_info=True)
        resp_text = "Sorry, I had trouble repurposing that content. Please try again or paste the text directly."
    _save_chat_messages(tenant["id"], req.session_id, req.message, resp_text)
    return WidgetChatResponse(
        response=resp_text,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=widget.get("show_watermark", True),
    )


def junk_or_greeting_shortcircuit(
    tenant: dict,
    widget: dict,
    req: WidgetChatRequest,
    messages: list[dict],
    watermark: bool,
) -> WidgetChatResponse | None:
    """Stage 5b — spam short-circuit: junk and repeat greetings skip Claude."""
    stripped = req.message.strip()
    normalized = re.sub(r"[^a-z]", "", stripped.lower())

    # Single-character or empty messages - never worth a Claude API call
    if len(normalized) <= 1 and len(messages) >= 2:
        canned_junk = "Could you type out your question? I'm happy to help!"
        _save_chat_messages(tenant["id"], req.session_id, req.message, canned_junk)
        logger.info(
            "widget_chat: junk_shortcircuit=True session=%s msg=%r (skipped Claude API)",
            req.session_id,
            stripped,
        )
        return WidgetChatResponse(
            response=canned_junk,
            session_id=req.session_id,
            lead_captured=False,
            show_watermark=watermark,
            handoff=False,
        )

    # Repeat greeting detection
    if normalized in _GREETINGS:
        if len(messages) == 0:
            biz_name = tenant.get("business_name") or "us"
            opening = widget.get("greeting_message") or (
                f"Hi! Thanks for reaching out to {biz_name}. How can I help today?"
            )
            _save_chat_messages(tenant["id"], req.session_id, req.message, opening)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s first_turn=True (skipped Claude API)",
                req.session_id,
            )
            return WidgetChatResponse(
                response=opening,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            )

        # Session already has at least one exchange - this is a repeat greeting
        prior_user_greeted = any(
            m["role"] == "user"
            and re.sub(r"[^a-z]", "", m.get("content", "").strip().lower())
            in _GREETINGS
            for m in messages
        )
        if prior_user_greeted:
            biz_name = tenant.get("business_name") or "us"
            canned = (
                f"I'm still here! Is there something specific I can help you with? "
                f"I can answer questions about {biz_name} - pricing, services, how to get started, and more."
            )
            _save_chat_messages(tenant["id"], req.session_id, req.message, canned)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s (skipped Claude API)",
                req.session_id,
            )
            return WidgetChatResponse(
                response=canned,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            )

    return None


def null_state_guard(
    tenant: dict,
    widget: dict,
    req: WidgetChatRequest,
    messages: list[dict],
    watermark: bool,
) -> WidgetChatResponse | None:
    """Stage 5c — bot has NO grounding at all: graceful setup fallback.

    Grounding sources: knowledge_base, custom_instructions, FAQs, or
    business_type (business_type alone gives the bot enough vertical
    context to answer generically).
    """
    has_kb = bool((widget.get("knowledge_base") or "").strip())
    has_ci = bool((widget.get("custom_instructions") or "").strip())
    has_bt = (
        bool((tenant.get("business_type") or "").strip())
        and (tenant.get("business_type") or "").lower() != "other"
    )
    if has_kb or has_ci or has_bt or len(messages) != 0:
        return None

    # Final check: FAQs count as grounding too. Probe cheaply.
    faq_probe_key = f"faq_count:{tenant['id']}"
    faq_count = _get_cached(faq_probe_key, _CHAT_CACHE_TTL)
    if faq_count is None:
        try:
            faq_probe = (
                get_service_supabase()
                .table("faq_entries")
                .select("id", count="exact")
                .eq("tenant_id", tenant["id"])
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            faq_count = int(faq_probe.count or 0)
        except Exception:
            logger.warning(
                "faq count probe failed for tenant %s", tenant["id"], exc_info=True
            )
            faq_count = 0
        _set_cache(faq_probe_key, faq_count)

    if faq_count != 0:
        return None

    biz = tenant.get("business_name") or "our team"
    phone = tenant.get("phone") or ""
    phone_msg = f" You can also reach us at {phone}." if phone else ""
    setup_msg = (
        f"Thanks for reaching out! Our chat assistant is still being set up. "
        f"In the meantime, please contact {biz} directly for assistance.{phone_msg}"
    )
    _save_chat_messages(tenant["id"], req.session_id, req.message, setup_msg)
    logger.info(
        "widget_chat: null_state_guard session=%s tenant=%s (no KB, CI, business_type, or FAQs)",
        req.session_id,
        tenant["id"],
    )
    return WidgetChatResponse(
        response=setup_msg,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=watermark,
        handoff=False,
    )


def turn_budget_guard(
    tenant: dict, req: WidgetChatRequest, watermark: bool
) -> WidgetChatResponse | None:
    """Stage 5d (part 1) — per-session turn budget. Fails open on error so a
    broken guard never blocks a real customer."""
    try:
        turn_budget_ok = check_turn_budget(req.session_id)
    except Exception:
        logger.warning(
            "widget_chat: turn budget check failed session=%s — proceeding normally",
            req.session_id,
            exc_info=True,
        )
        turn_budget_ok = True

    if turn_budget_ok:
        return None

    turn_budget_text = (
        "Let me connect you with our team — this conversation has been "
        "going a while and they can help you directly."
    )
    _save_chat_messages(tenant["id"], req.session_id, req.message, turn_budget_text)
    logger.info(
        "widget_chat: turn_budget_exceeded session=%s (skipped Claude API)",
        req.session_id,
    )
    return WidgetChatResponse(
        response=turn_budget_text,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=watermark,
        handoff=True,
    )


async def input_screen_guard(
    tenant: dict, req: WidgetChatRequest, watermark: bool
) -> WidgetChatResponse | None:
    """Stage 5d (part 2) — prompt-injection/abuse screen. Fails open on error."""
    try:
        guard_result = await screen_widget_input(req.message)
    except Exception:
        logger.warning(
            "widget_chat: input guard raised unexpectedly session=%s — "
            "proceeding normally",
            req.session_id,
            exc_info=True,
        )
        guard_result = {"allow": True, "reason": "guard_exception"}

    if guard_result.get("allow", True):
        return None

    biz_name = tenant.get("business_name") or "us"
    guard_blocked_text = (
        f"I can only help with questions about {biz_name}. Could you "
        "rephrase that?"
    )
    _save_chat_messages(tenant["id"], req.session_id, req.message, guard_blocked_text)
    logger.info(
        "widget_chat: input_guard_blocked session=%s reason=%s (skipped Claude API)",
        req.session_id,
        guard_result.get("reason"),
    )
    return WidgetChatResponse(
        response=guard_blocked_text,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=watermark,
        handoff=False,
    )
