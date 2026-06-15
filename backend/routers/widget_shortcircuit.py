"""Widget chat short-circuit guards — skip Claude API for junk input.

Extracted from widget_chat.py — single concern: detect messages that
need no LLM call and return canned responses immediately.

Three guards in order:
    1. Single-char / empty messages (junk)
    2. Repeat greeting detection
    3. Null-state guard (widget not configured yet)

Public API:
    check_shortcircuit(...)  -> WidgetChatResponse | None
"""

import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetChatResponse
from backend.routers.widget_chat_helpers import (
    _CHAT_CACHE_TTL,
    _get_cached,
    _save_chat_messages,
    _set_cache,
)

logger = logging.getLogger(__name__)

_GREETINGS = {"hi", "hey", "hello", "yo", "sup", "hiya", "howdy", "hii", "helo"}


def check_shortcircuit(
    *,
    tenant: dict[str, Any],
    widget: dict[str, Any],
    session_id: str,
    message: str,
    messages: list[dict[str, Any]],
    watermark: bool,
) -> "WidgetChatResponse | None":
    """Run all short-circuit guards; return early response or None.

    Callers receive None when Claude should proceed normally. A non-None
    return value means the guard handled the message and the caller must
    return it immediately without calling Claude.

    Guards run in order:
    1. Junk/empty messages
    2. Repeat greetings
    3. Null-state (no KB, no business_type, no FAQs)
    """
    _stripped = message.strip()
    _normalized = re.sub(r"[^a-z]", "", _stripped.lower())

    # --- Guard 1: Junk / single-char messages ---
    if len(_normalized) <= 1 and len(messages) >= 2:
        _canned_junk = "Could you type out your question? I'm happy to help!"
        _save_chat_messages(tenant["id"], session_id, message, _canned_junk)
        logger.info(
            "widget_chat: junk_shortcircuit=True session=%s msg=%r (skipped Claude API)",
            session_id,
            _stripped,
        )
        return WidgetChatResponse(
            response=_canned_junk,
            session_id=session_id,
            lead_captured=False,
            show_watermark=watermark,
            handoff=False,
        )

    # --- Guard 2: Repeat greeting detection ---
    if _normalized in _GREETINGS:
        if len(messages) == 0:
            _biz_name = tenant.get("business_name") or "us"
            _opening = widget.get("greeting_message") or (
                f"Hi! Thanks for reaching out to {_biz_name}. How can I help today?"
            )
            _save_chat_messages(tenant["id"], session_id, message, _opening)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s first_turn=True (skipped Claude API)",
                session_id,
            )
            return WidgetChatResponse(
                response=_opening,
                session_id=session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            )

        # Session already has at least one exchange — check for repeat greeting
        _prior_user_greeted = any(
            m["role"] == "user"
            and re.sub(r"[^a-z]", "", m.get("content", "").strip().lower())
            in _GREETINGS
            for m in messages
        )
        if _prior_user_greeted:
            _biz_name = tenant.get("business_name") or "us"
            _canned = (
                f"I'm still here! Is there something specific I can help you with? "
                f"I can answer questions about {_biz_name} - pricing, services, how to get started, and more."
            )
            _save_chat_messages(tenant["id"], session_id, message, _canned)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s (skipped Claude API)",
                session_id,
            )
            return WidgetChatResponse(
                response=_canned,
                session_id=session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            )

    # --- Guard 3: Null-state guard ---
    # If widget has NO grounding at all show a graceful fallback.
    # Grounding sources: knowledge_base, custom_instructions, FAQs, or business_type
    # (business_type alone gives the bot enough vertical context to answer generically).
    _has_kb = bool((widget.get("knowledge_base") or "").strip())
    _has_ci = bool((widget.get("custom_instructions") or "").strip())
    _has_bt = (
        bool((tenant.get("business_type") or "").strip())
        and (tenant.get("business_type") or "").lower() != "other"
    )
    if not _has_kb and not _has_ci and not _has_bt and len(messages) == 0:
        # Final check: FAQs count as grounding too. Probe cheaply.
        _faq_probe_key = f"faq_count:{tenant['id']}"
        _faq_count = _get_cached(_faq_probe_key, _CHAT_CACHE_TTL)
        if _faq_count is None:
            try:
                _faq_probe = (
                    get_service_supabase()
                    .table("faq_entries")
                    .select("id", count="exact")
                    .eq("tenant_id", tenant["id"])
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )
                _faq_count = int(_faq_probe.count or 0)
            except Exception:
                logger.warning(
                    "faq count probe failed for tenant %s", tenant["id"], exc_info=True
                )
                _faq_count = 0
            _set_cache(_faq_probe_key, _faq_count)

        if _faq_count == 0:
            _biz = tenant.get("business_name") or "our team"
            _phone = tenant.get("phone") or ""
            _phone_msg = f" You can also reach us at {_phone}." if _phone else ""
            _setup_msg = (
                f"Thanks for reaching out! Our chat assistant is still being set up. "
                f"In the meantime, please contact {_biz} directly for assistance.{_phone_msg}"
            )
            _save_chat_messages(tenant["id"], session_id, message, _setup_msg)
            logger.info(
                "widget_chat: null_state_guard session=%s tenant=%s (no KB, CI, business_type, or FAQs)",
                session_id,
                tenant["id"],
            )
            return WidgetChatResponse(
                response=_setup_msg,
                session_id=session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            )

    return None
