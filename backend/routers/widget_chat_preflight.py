"""Widget chat preflight guards.

Extracted from widget_chat.py to keep the route handler focused. Runs
the four early-exit checks that bypass the Claude API entirely:

  1. handoff_active — conversation tagged for team takeover
  2. content_mode  — repurpose content instead of chatting (async)
  3. spam/greeting — junk + repeat-greeting short circuits
  4. null_state    — no grounding (no KB, CI, business_type, or FAQs)

Returns either a WidgetChatResponse the handler should return
immediately, or None (continue to the main pipeline) plus the loaded
chat history.
"""


import logging
import re
from typing import Optional

from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetChatResponse
from backend.routers.widget_chat_helpers import (
    _CHAT_CACHE_TTL,
    _get_cached,
    _load_chat_history,
    _save_chat_messages,
    _set_cache,
)

logger = logging.getLogger(__name__)


_CONTENT_MODE_KEYWORDS = (
    "repurpose",
    "content mode",
    "turn this into",
    "create content from",
)
_YT_PATTERN = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")
_GREETINGS = {"hi", "hey", "hello", "yo", "sup", "hiya", "howdy", "hii", "helo"}


async def run_preflight(
    *,
    tenant: dict,
    widget: dict,
    req,
    db,
) -> tuple[Optional[WidgetChatResponse], list]:
    """Run all preflight guards. Returns (response, messages).

    If response is not None, the handler should return it immediately
    (the guard fired and chat history may or may not have been loaded
    — caller does not need it). If response is None, messages is the
    loaded chat history for the main pipeline.
    """
    # 4b. Handoff mode — team member is handling this conversation
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

    if handoff_active:
        _save_chat_messages(tenant["id"], req.session_id, req.message, None)
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
                if last_reply and "team member" not in last_reply.lower():
                    return (
                        WidgetChatResponse(
                            response=last_reply,
                            session_id=req.session_id,
                            lead_captured=False,
                            show_watermark=widget.get("show_watermark", True),
                            handoff=True,
                        ),
                        [],
                    )
        except Exception:
            logger.warning(
                "Failed to fetch latest team reply for session %s",
                req.session_id,
                exc_info=True,
            )

        waiting_msg = (
            "A team member is reviewing your conversation and will respond "
            "shortly. Thank you for your patience."
        )
        _save_chat_messages(tenant["id"], req.session_id, None, waiting_msg)
        return (
            WidgetChatResponse(
                response=waiting_msg,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=widget.get("show_watermark", True),
                handoff=True,
            ),
            [],
        )

    # 4c. Content mode — repurpose content instead of chatting
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

    if content_mode:
        plan = tenant.get("plan") or "free"
        if plan not in ("professional", "enterprise"):
            _save_chat_messages(tenant["id"], req.session_id, req.message, None)
            return (
                WidgetChatResponse(
                    response=(
                        "Content repurposing is available on Professional "
                        "and Enterprise plans. Upgrade to unlock this feature!"
                    ),
                    session_id=req.session_id,
                    lead_captured=False,
                    show_watermark=widget.get("show_watermark", True),
                ),
                [],
            )
        if _YT_PATTERN.search(req.message):
            src_type = "youtube"
        elif req.message.strip().startswith(("http://", "https://")):
            src_type = "url"
        else:
            src_type = "text"
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
            resp_text = (
                "Sorry, I had trouble repurposing that content. Please try "
                "again or paste the text directly."
            )
        _save_chat_messages(tenant["id"], req.session_id, req.message, resp_text)
        return (
            WidgetChatResponse(
                response=resp_text,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=widget.get("show_watermark", True),
            ),
            [],
        )

    # 5. Load message history (needed for the remaining guards + main pipeline)
    messages = _load_chat_history(tenant["id"], req.session_id)
    logger.info(
        "widget_chat: session=%s loaded %d previous messages, first_role=%s",
        req.session_id,
        len(messages),
        messages[0]["role"] if messages else "NONE",
    )

    # 5b. Spam short-circuit + repeat-greeting detection
    stripped = req.message.strip()
    normalized = re.sub(r"[^a-z]", "", stripped.lower())
    is_free = (tenant.get("plan") or "free") == "free"
    watermark = True if is_free else widget.get("show_watermark", True)

    if len(normalized) <= 1 and len(messages) >= 2:
        canned_junk = "Could you type out your question? I'm happy to help!"
        _save_chat_messages(tenant["id"], req.session_id, req.message, canned_junk)
        logger.info(
            "widget_chat: junk_shortcircuit=True session=%s msg=%r (skipped Claude API)",
            req.session_id,
            stripped,
        )
        return (
            WidgetChatResponse(
                response=canned_junk,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=watermark,
                handoff=False,
            ),
            messages,
        )

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
            return (
                WidgetChatResponse(
                    response=opening,
                    session_id=req.session_id,
                    lead_captured=False,
                    show_watermark=watermark,
                    handoff=False,
                ),
                messages,
            )

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
            return (
                WidgetChatResponse(
                    response=canned,
                    session_id=req.session_id,
                    lead_captured=False,
                    show_watermark=watermark,
                    handoff=False,
                ),
                messages,
            )

    # 5c. Null-state guard — bot has no grounding at all
    has_kb = bool((widget.get("knowledge_base") or "").strip())
    has_ci = bool((widget.get("custom_instructions") or "").strip())
    has_bt = (
        bool((tenant.get("business_type") or "").strip())
        and (tenant.get("business_type") or "").lower() != "other"
    )
    if not has_kb and not has_ci and not has_bt and len(messages) == 0:
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
                    "faq count probe failed for tenant %s",
                    tenant["id"],
                    exc_info=True,
                )
                faq_count = 0
            _set_cache(faq_probe_key, faq_count)

        if faq_count == 0:
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
            return (
                WidgetChatResponse(
                    response=setup_msg,
                    session_id=req.session_id,
                    lead_captured=False,
                    show_watermark=watermark,
                    handoff=False,
                ),
                messages,
            )

    return None, messages
