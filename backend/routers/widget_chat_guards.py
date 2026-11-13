"""Pre-LLM guard stages for the widget chat pipeline (issue #472 split).

Each guard inspects the incoming turn and either short-circuits it with a
finished `WidgetChatResponse` (returned to the visitor without ever paying
for a Claude call) or returns None so the pipeline continues. Moved
verbatim from the widget_chat route body; the route orchestrates the order:

    handoff-mode -> junk/greeting -> null-state -> turn-budget -> input-screen

The public widget is customer-facing: no guard here may run an owner/dashboard
tool (content repurpose, campaigns, settings, ...). See
backend/tests/test_widget_public_scope.py.

Do not enable postponed annotation evaluation here; it breaks Pydantic on FastAPI.
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
            "handoff check failed for tenant %s", tenant["id"], exc_info=True
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
            "Failed to fetch latest team reply for tenant %s",
            tenant["id"],
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
            "widget_chat: junk_shortcircuit=True msg_len=%d (skipped Claude API)",
            len(stripped),
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
                "widget_chat: greeting_shortcircuit=True first_turn=True (skipped Claude API)"
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
                "widget_chat: greeting_shortcircuit=True (skipped Claude API)"
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
        "widget_chat: null_state_guard tenant=%s (no KB, CI, business_type, or FAQs)",
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
            "widget_chat: turn budget check failed — proceeding normally",
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
        "widget_chat: turn_budget_exceeded (skipped Claude API)",
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
        guard_result = await screen_widget_input(
            req.message,
            tenant_id=tenant["id"],
            session_id=req.session_id,
        )
    except Exception:
        logger.warning(
            "widget_chat: input guard raised unexpectedly — proceeding normally",
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
        "widget_chat: input_guard_blocked reason=%s (skipped Claude API)",
        guard_result.get("reason"),
    )
    return WidgetChatResponse(
        response=guard_blocked_text,
        session_id=req.session_id,
        lead_captured=False,
        show_watermark=watermark,
        handoff=False,
    )
