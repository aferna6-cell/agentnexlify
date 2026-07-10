"""Widget chat endpoint — main /api/v1/widget/chat POST handler.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging
import re
from time import perf_counter

import anthropic
from fastapi import APIRouter, BackgroundTasks, Request

from backend.config import settings
from backend.limiter import limiter
from backend.middleware.rate_limit import get_client_id_key, get_tier_limit
from backend.models.database import get_service_supabase
from backend.models.schemas import WidgetChatRequest, WidgetChatResponse
from backend.services.activity import log_activity
from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)
from backend.services.os_inbound_bridge import bridge_widget, is_bridge_enabled
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.widget_chat_helpers import (
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    _CHAT_CACHE_TTL,
    _build_flow_instructions,
    _build_intent_window,
    _build_system_prompt,
    _compact_messages_for_llm,
    _check_origin,
    _get_cached,
    _get_or_create_conversation,
    _get_tenant,
    _get_widget_config,
    _load_chat_history,
    _needs_bid_context,
    _needs_job_context,
    _query_kb_articles,
    _record_response_metric,
    _save_chat_messages,
    _set_cache,
)
from backend.routers.widget_lead_helpers import (
    _capture_leads_from_session,
    _categorize_conversation,
    _enrich_lead_from_message,
    _extract_action_items,
    _extract_lead_info,
)
from backend.routers.widget_booking import (
    _extract_order_from_response,
    _strip_order_json_from_response,
    _process_order_from_chat,
    _extract_bid_request_from_response,
    _strip_bid_request_from_response,
    _process_bid_request_from_chat,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])


# Token the first-tier Claude emits to ask for the managed-agent fallback.
# Defined at module level so tests can patch it if needed and so the two
# call sites (prompt-builder + detector) stay in sync.
FALLBACK_MARKER = "FALLBACK_TO_SUPPORT_AGENT"

# Hard ceiling for the managed-agent fallback round-trip. support_agent's
# 50th percentile is 4.6s on the 2026-04-10 smoke but Opus-heavy cases can
# push toward 15s. 8s keeps the widget responsive — over-budget means human
# handoff, which is the same degradation the user would get if first-tier
# Claude had said HANDOFF_REQUESTED directly.
FALLBACK_TIMEOUT_SECONDS = 8.0


async def _run_support_fallback(
    *,
    assistant_text: str,
    widget: dict,
    tenant_id: str,
    session_id: str,
    customer_message: str,
) -> tuple[str, bool]:
    """Second-tier managed-agent fallback for widget chat.

    When the first-tier Claude reply contains the FALLBACK_MARKER and the
    widget config has enable_ai_fallback=True, call the support_agent
    managed agent (with an 8s timeout) and either:

    - high / medium confidence → replace assistant_text with the agent answer
    - low confidence / timeout / error → force HANDOFF_REQUESTED

    Returns (new_assistant_text, ai_fallback_fired).

    If the flag is off but the marker leaked anyway, the marker is stripped
    and no fallback call is made. If neither condition is true the input
    text and False are returned unchanged.

    Imports for asyncio / run_in_threadpool / support_agent are lazy so
    this helper stays cheap on the happy path where the marker is absent.
    """
    has_marker = FALLBACK_MARKER in assistant_text
    fallback_enabled = bool(widget.get("enable_ai_fallback"))

    if not has_marker:
        return assistant_text, False

    if not fallback_enabled:
        # Flag off but first-tier Claude leaked the marker anyway. Strip
        # it so end users never see internal control tokens.
        return assistant_text.replace(FALLBACK_MARKER, "").strip(), False

    # Strip the marker up-front. If the fallback fails we still need a
    # clean base string to attach the human-handoff prefix to.
    assistant_text = assistant_text.replace(FALLBACK_MARKER, "").strip()

    import asyncio
    from fastapi.concurrency import run_in_threadpool
    from backend.services.managed_agents_registry import (
        ManagedAgentNotConfigured,
    )
    from backend.services import support_agent as _support_agent_mod
    from backend.services import agent_sdk_client as _agent_sdk

    fallback_start = perf_counter()
    fallback_confidence: str | None = None
    fallback_escalate_reason: str | None = None
    fallback_success = False
    fallback_answer: str | None = None
    fallback_error: str | None = None
    generic_handoff_text = (
        "Let me connect you with our team so you get the right answer "
        "faster.\nHANDOFF_REQUESTED"
    )

    # --- agent-service path (preferred when AGENT_SERVICE_URL is set) ---
    # Build the support prompt once (Supabase context load) then try the
    # SDK-backed widget-support agent. Falls through to managed-agents on
    # any failure so existing behavior is fully preserved.
    _sdk_result = None
    if _agent_sdk.is_configured():
        try:
            _sdk_prompt = await asyncio.wait_for(
                run_in_threadpool(
                    _support_agent_mod.build_support_prompt,
                    tenant_id,
                    customer_message,
                    session_id,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
            _sdk_raw = await asyncio.wait_for(
                run_in_threadpool(
                    _agent_sdk.run_agent_sync,
                    "widget-support",
                    _sdk_prompt,
                    timeout=FALLBACK_TIMEOUT_SECONDS - 1.0,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
            if _sdk_raw and not _sdk_raw.get("is_error"):
                _sdk_result = _support_agent_mod.parse_support_reply(
                    _sdk_raw.get("result") or ""
                )
                logger.info(
                    "widget_chat: agent_sdk_fallback session=%s turns=%s cost_usd=%.4f",
                    session_id,
                    _sdk_raw.get("turns"),
                    _sdk_raw.get("cost_usd", 0),
                )
        except Exception:
            logger.warning(
                "widget_chat: agent_sdk_fallback failed session=%s — "
                "falling back to managed agents",
                session_id,
                exc_info=True,
            )

    try:
        if _sdk_result is not None:
            fallback_result = _sdk_result
        else:
            fallback_result = await asyncio.wait_for(
                run_in_threadpool(
                    _support_agent_mod.run_support_query,
                    tenant_id,
                    customer_message,
                    session_id,
                ),
                timeout=FALLBACK_TIMEOUT_SECONDS,
            )
        fallback_confidence = fallback_result.get("confidence", "low")
        fallback_escalate_reason = fallback_result.get("escalate_reason")
        fallback_answer = fallback_result.get("answer")

        if fallback_confidence in ("high", "medium") and fallback_answer:
            assistant_text = fallback_answer.strip()
            fallback_success = True
            logger.info(
                "widget_chat: managed_agent_fallback SUCCESS session=%s "
                "confidence=%s",
                session_id,
                fallback_confidence,
            )
        else:
            # Low confidence — force human handoff. Attach the agent's
            # best-effort answer (if any) so the customer sees something
            # useful while the team is paged.
            handoff_prefix = (
                fallback_answer.strip()
                if isinstance(fallback_answer, str) and fallback_answer.strip()
                else (
                    "I don't have a confident answer for that — let me "
                    "connect you with our team right away."
                )
            )
            assistant_text = f"{handoff_prefix}\nHANDOFF_REQUESTED"
            logger.info(
                "widget_chat: managed_agent_fallback LOW_CONFIDENCE "
                "session=%s reason=%s",
                session_id,
                fallback_escalate_reason,
            )
    except asyncio.TimeoutError:
        fallback_error = "timeout"
        assistant_text = generic_handoff_text
        logger.warning(
            "widget_chat: managed_agent_fallback TIMEOUT session=%s — "
            "forcing human handoff",
            session_id,
        )
    except ManagedAgentNotConfigured as exc:
        fallback_error = f"not_configured: {exc}"
        assistant_text = generic_handoff_text
        logger.warning(
            "widget_chat: managed_agent_fallback NOT_CONFIGURED "
            "session=%s — forcing human handoff (%s)",
            session_id,
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        fallback_error = f"exception: {type(exc).__name__}"
        assistant_text = generic_handoff_text
        logger.exception(
            "widget_chat: managed_agent_fallback ERROR session=%s — "
            "forcing human handoff",
            session_id,
        )
    finally:
        fallback_duration_ms = int((perf_counter() - fallback_start) * 1000)
        try:
            log_activity(
                tenant_id=tenant_id,
                activity_type="ai_fallback_fired",
                description=("Widget chat escalated to support_agent managed agent"),
                metadata={
                    "session_id": session_id,
                    "confidence": fallback_confidence,
                    "escalate_reason": fallback_escalate_reason,
                    "duration_ms": fallback_duration_ms,
                    "success": fallback_success,
                    "error": fallback_error,
                },
            )
        except Exception:
            logger.warning(
                "widget_chat: failed to log ai_fallback_fired activity "
                "for session %s",
                session_id,
                exc_info=True,
            )

    return assistant_text, True


def _chat_rate_limit(key: str) -> str:
    """Dynamic per-tenant rate limit based on plan tier.

    slowapi calls this with the result of key_function (the api_key string)
    when the limit provider's signature includes a `key` parameter
    (slowapi/wrappers.py:86-92). Looks up tenant plan via api_key, falls
    back to free-tier (30/minute) if the plan cannot be resolved.
    """
    try:
        from backend.routers.widget_chat_helpers import _get_widget_config, _get_tenant

        widget = _get_widget_config(key)
        tenant = _get_tenant(widget["tenant_id"])
        plan = tenant.get("plan", "free") or "free"
    except Exception as exc:
        logger.warning(
            "_chat_rate_limit fallback to free tier for key=%s: %s", key, exc
        )
        plan = "free"
    return get_tier_limit(plan)


@router.post("/chat", response_model=WidgetChatResponse)
@limiter.limit(_chat_rate_limit, key_func=get_client_id_key)
async def widget_chat(
    request: Request, req: WidgetChatRequest, background_tasks: BackgroundTasks
):
    """Process a chat message through the multi-tenant widget pipeline."""
    request_started = perf_counter()
    logger.info("widget_chat: received request session=%s", req.session_id)

    # 1. Look up widget config + tenant
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])
    logger.info(
        "widget_chat: tenant=%s business=%s", tenant["id"], tenant.get("business_name")
    )

    # 2. Origin check
    _check_origin(request, widget.get("allowed_domains"))

    # 3. All plans now have unlimited conversations (limit check removed).

    # 4. Get or create conversation
    conversation_id, is_new = _get_or_create_conversation(tenant["id"], req.session_id)
    logger.info("widget_chat: conversation=%s is_new=%s", conversation_id, is_new)

    # Fire conversation.started webhook for new sessions
    if is_new:
        fire_event_background(
            tenant["id"],
            "conversation.started",
            {
                "session_id": req.session_id,
                "conversation_id": conversation_id,
            },
        )
        # Email the owner that a new conversation came in (opt-in; background
        # so it never delays the visitor reply). Lightweight: first message +
        # inbox link, not a transcript.
        if tenant.get("conversation_email_notify_enabled"):
            from backend.services.conversation_notify import notify_new_conversation

            background_tasks.add_task(notify_new_conversation, tenant, req.message)

    # Get DB handle for conversation operations
    db = get_service_supabase()

    # Increment usage counter only for new conversations
    # Uses compare-and-swap to avoid lost increments under concurrent requests.
    if is_new:
        try:
            for _attempt in range(3):
                row = (
                    db.table("tenants")
                    .select("conversations_used_this_month")
                    .eq("id", tenant["id"])
                    .limit(1)
                    .execute()
                    .data
                )
                old_val = (
                    (row[0].get("conversations_used_this_month") or 0) if row else 0
                )
                # Conditional update: only succeeds if the value hasn't changed
                query = (
                    db.table("tenants")
                    .update({"conversations_used_this_month": old_val + 1})
                    .eq("id", tenant["id"])
                )
                if old_val == 0:
                    # NULL and 0 both need to match — use is_ for NULL
                    query = query.is_("conversations_used_this_month", "null")
                else:
                    query = query.eq("conversations_used_this_month", old_val)
                result = query.execute()
                if result.data:
                    break  # update succeeded
            else:
                logger.warning(
                    "Usage counter CAS failed for tenant %s after 3 attempts",
                    tenant["id"],
                )
        except Exception:
            logger.warning(
                "Failed to increment usage counter for tenant %s",
                tenant["id"],
                exc_info=True,
            )

    # 4b. Check if conversation is in handoff mode (team member handling)
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

    # 4c. Content mode detection — repurpose content instead of chatting
    _content_mode_keywords = [
        "repurpose",
        "content mode",
        "turn this into",
        "create content from",
    ]
    _yt_pattern = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")
    _msg_lower = req.message.lower()
    _content_mode = req.content_mode
    if not _content_mode:
        for _kw in _content_mode_keywords:
            if _kw in _msg_lower:
                _content_mode = True
                break
    if not _content_mode and _yt_pattern.search(req.message):
        _content_mode = True
    if not _content_mode and len(req.message) > 500 and "?" not in req.message:
        _content_mode = True

    if _content_mode:
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
        if _yt_pattern.search(req.message):
            _src_type = "youtube"
        elif req.message.strip().startswith(("http://", "https://")):
            _src_type = "url"
        else:
            _src_type = "text"
        # Create repurpose job
        try:
            from backend.services.content_repurposer import (
                extract_source,
                repurpose as do_repurpose,
            )

            source = await extract_source(_src_type, req.message.strip())
            outputs = await do_repurpose(
                source_content=source["content"],
                title=source["title"],
                tenant_id=tenant["id"],
                tone="professional",
            )
            db.table("repurpose_jobs").insert(
                {
                    "tenant_id": tenant["id"],
                    "source_type": _src_type,
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

    # 5. Load message history from chat_messages table (last 20 messages)
    messages = _load_chat_history(tenant["id"], req.session_id)
    logger.info(
        "widget_chat: session=%s loaded %d previous messages, first_role=%s",
        req.session_id,
        len(messages),
        messages[0]["role"] if messages else "NONE",
    )

    # 5b. Spam short-circuit — skip Claude API for junk and repeat greetings
    _stripped = req.message.strip()
    _normalized = re.sub(r"[^a-z]", "", _stripped.lower())
    _is_free = (tenant.get("plan") or "free") == "free"
    _watermark = True if _is_free else widget.get("show_watermark", True)

    # Single-character or empty messages - never worth a Claude API call
    if len(_normalized) <= 1 and len(messages) >= 2:
        _canned_junk = "Could you type out your question? I'm happy to help!"
        _save_chat_messages(tenant["id"], req.session_id, req.message, _canned_junk)
        logger.info(
            "widget_chat: junk_shortcircuit=True session=%s msg=%r (skipped Claude API)",
            req.session_id,
            _stripped,
        )
        return WidgetChatResponse(
            response=_canned_junk,
            session_id=req.session_id,
            lead_captured=False,
            show_watermark=_watermark,
            handoff=False,
        )

    # Repeat greeting detection
    _GREETINGS = {"hi", "hey", "hello", "yo", "sup", "hiya", "howdy", "hii", "helo"}
    if _normalized in _GREETINGS:
        if len(messages) == 0:
            _biz_name = tenant.get("business_name") or "us"
            _opening = widget.get("greeting_message") or (
                f"Hi! Thanks for reaching out to {_biz_name}. How can I help today?"
            )
            _save_chat_messages(tenant["id"], req.session_id, req.message, _opening)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s first_turn=True (skipped Claude API)",
                req.session_id,
            )
            return WidgetChatResponse(
                response=_opening,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=_watermark,
                handoff=False,
            )

        # Session already has at least one exchange - this is a repeat greeting
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
            _save_chat_messages(tenant["id"], req.session_id, req.message, _canned)
            logger.info(
                "widget_chat: greeting_shortcircuit=True session=%s (skipped Claude API)",
                req.session_id,
            )
            return WidgetChatResponse(
                response=_canned,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=_watermark,
                handoff=False,
            )

    # 5c. Null-state guard — if bot has NO grounding at all, show a graceful fallback.
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
            _save_chat_messages(tenant["id"], req.session_id, req.message, _setup_msg)
            logger.info(
                "widget_chat: null_state_guard session=%s tenant=%s (no KB, CI, business_type, or FAQs)",
                req.session_id,
                tenant["id"],
            )
            return WidgetChatResponse(
                response=_setup_msg,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=_watermark,
                handoff=False,
            )

    # 6. Build system prompt with compact, intent-aware context.
    tid = tenant["id"]
    db = get_service_supabase()
    context_started = perf_counter()
    intent_window = _build_intent_window(req.message, messages)
    needs_job_context = _needs_job_context(intent_window)
    needs_bid_context = _needs_bid_context(intent_window)
    history_for_model = _compact_messages_for_llm(messages)

    faq_data = _get_cached(f"faq:{tid}", _CHAT_CACHE_TTL)
    if faq_data is None:
        try:
            faq_result = (
                db.table("faq_entries")
                .select("question, answer")
                .eq("tenant_id", tid)
                .eq("is_active", True)
                .execute()
            )
            faq_data = faq_result.data or []
        except Exception:
            logger.warning("faq_entries query failed for tenant %s", tid, exc_info=True)
            faq_data = []
        _set_cache(f"faq:{tid}", faq_data)

    bh_cache_key = f"bh:{tid}"
    bh_data = _get_cached(bh_cache_key, _CHAT_CACHE_TTL)
    if bh_data is None:
        try:
            bh_result = (
                db.table("business_hours")
                .select("timezone, hours")
                .eq("tenant_id", tid)
                .limit(1)
                .execute()
            )
            bh_data = bh_result.data[0] if bh_result.data else False
        except Exception:
            logger.warning(
                "business_hours query failed for tenant %s", tid, exc_info=True
            )
            bh_data = False
        _set_cache(bh_cache_key, bh_data)
    if bh_data is False:
        bh_data = None

    corrections = _get_cached(f"corr:{tid}", _CHAT_CACHE_TTL)
    if corrections is None:
        try:
            fb_result = (
                db.table("ai_feedback")
                .select("correction")
                .eq("tenant_id", tid)
                .eq("rating", "thumbs_down")
                .filter("correction", "not.is", "null")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            corrections = fb_result.data or []
        except Exception:
            logger.warning("ai_feedback query failed for tenant %s", tid, exc_info=True)
            corrections = []
        _set_cache(f"corr:{tid}", corrections)

    website_content = None
    if not widget.get("knowledge_base"):
        website_content = _get_cached(f"wsc:{tid}", _CHAT_CACHE_TTL)
        if website_content is None:
            try:
                from backend.services.website_crawler import get_crawled_content

                website_content = get_crawled_content(tid) or False
            except Exception:
                logger.warning(
                    "website_content load failed for tenant %s", tid, exc_info=True
                )
                website_content = False
            _set_cache(f"wsc:{tid}", website_content)
        if website_content is False:
            website_content = None

    menu_items = None
    if (tenant.get("business_type") or "").lower() == "restaurant":
        try:
            menu_result = (
                db.table("menu_items")
                .select("name, description, price, category, available")
                .eq("tenant_id", tenant["id"])
                .order("category")
                .order("sort_order")
                .execute()
            )
            if menu_result.data:
                menu_items = menu_result.data
        except Exception:
            logger.warning(
                "menu_items query failed for tenant %s", tenant["id"], exc_info=True
            )

    job_listings = None
    if needs_job_context:
        try:
            jobs_result = (
                db.table("jobs")
                .select("title, pay_range, schedule, location")
                .eq("tenant_id", tenant["id"])
                .eq("is_active", True)
                .limit(20)
                .execute()
            )
            if jobs_result.data:
                job_listings = jobs_result.data
        except Exception:
            logger.warning(
                "jobs query failed for tenant %s", tenant["id"], exc_info=True
            )

    bid_templates = None
    if needs_bid_context:
        bid_templates = _get_cached(f"bidtpl:{tid}", _CHAT_CACHE_TTL)
        if bid_templates is None:
            try:
                bt_result = (
                    db.table("bid_templates")
                    .select("name, description")
                    .eq("tenant_id", tid)
                    .limit(20)
                    .execute()
                )
                bid_templates = bt_result.data if bt_result.data else []
            except Exception:
                logger.warning(
                    "bid_templates query failed for tenant %s", tid, exc_info=True
                )
                bid_templates = []
            _set_cache(f"bidtpl:{tid}", bid_templates)

    custom_field_defs = []
    if needs_bid_context:
        try:
            cf_result = (
                db.table("custom_field_definitions")
                .select("field_name, field_type, options, is_required")
                .eq("tenant_id", tid)
                .order("sort_order")
                .limit(20)
                .execute()
            )
            custom_field_defs = cf_result.data if cf_result.data else []
        except Exception:
            logger.debug(
                "custom field defs query failed for tenant %s", tid, exc_info=True
            )

    # Load active chat flow
    active_flow = None
    active_flow_id = None
    try:
        flow_result = (
            db.table("chat_flows")
            .select("id, flow_json")
            .eq("tenant_id", tenant["id"])
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if flow_result.data:
            active_flow = flow_result.data[0].get("flow_json")
            active_flow_id = flow_result.data[0].get("id")
    except Exception:
        logger.warning(
            "chat_flows query failed for tenant %s", tenant["id"], exc_info=True
        )

    # KB article retrieval — one DB/FTS round trip per message.
    # Gated on widget_kb_articles_enabled (default 1 = ON).
    # Failures yield [] so the chat response is never blocked.
    # Latency note: adds ~15-80ms per message (pgvector semantic search or
    # Postgres FTS). Acceptable for this path; can be disabled per-deployment
    # by setting widget_kb_articles_enabled=0 in llm_runtime settings.
    kb_article_refs = []
    if resolve_int_setting("widget_kb_articles_enabled", 1):
        try:
            kb_article_refs = await _query_kb_articles(req.message)
        except Exception:
            logger.warning(
                "widget_chat: kb_articles retrieval failed for session=%s — "
                "continuing without KB augmentation",
                req.session_id,
                exc_info=True,
            )

    system_prompt = _build_system_prompt(
        tenant,
        faq_data,
        bh_data,
        corrections,
        website_content,
        menu_items,
        job_listings,
        bid_templates=bid_templates or None,
        custom_field_defs=custom_field_defs or None,
        custom_instructions=widget.get("custom_instructions") or None,
        knowledge_base=widget.get("knowledge_base") or None,
        kb_article_refs=kb_article_refs or None,
    )

    # Inject active flow instructions into system prompt
    if active_flow and active_flow.get("nodes"):
        flow_instructions = _build_flow_instructions(active_flow)
        if flow_instructions:
            flow_chars = resolve_int_setting("widget_prompt_flow_chars", 1500)
            if len(flow_instructions) > flow_chars:
                flow_instructions = (
                    flow_instructions[: flow_chars - 18].rstrip() + "\n[Flow truncated]"
                )
            system_prompt += flow_instructions

    prompt_profile = {
        "history_messages": len(history_for_model),
        "faq_count": len(faq_data or []),
        "has_hours": bool(bh_data),
        "has_corrections": bool(corrections),
        "has_website": bool(website_content),
        "has_kb": bool(widget.get("knowledge_base")),
        "menu_items": len(menu_items or []),
        "jobs": len(job_listings or []),
        "bid_templates": len(bid_templates or []),
        "custom_fields": len(custom_field_defs or []),
        "has_flow": bool(active_flow_id),
    }
    context_duration_ms = int((perf_counter() - context_started) * 1000)

    # Track flow usage in activity_log for new conversations
    if active_flow_id and is_new:
        try:
            log_activity(
                tenant_id=tenant["id"],
                activity_type="flow_used",
                description="Chat flow used in conversation",
                metadata={
                    "flow_id": active_flow_id,
                    "session_id": req.session_id,
                    "conversation_id": conversation_id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to log flow_used for tenant %s flow %s",
                tenant["id"],
                active_flow_id,
                exc_info=True,
            )

    # Use bot_name from widget config in the system prompt
    if widget.get("bot_name"):
        system_prompt = system_prompt.replace("AI Assistant", widget["bot_name"], 1)

    # Booking nudge — if online booking is enabled, tell the AI to actively offer
    # booking. Two-thirds of captured leads were not booking; a passive "mention
    # it" prompt under-converts, so this proactively offers a slot once there is
    # any service/pricing/scheduling interest or once contact info is shared.
    if widget.get("booking_enabled"):
        system_prompt += (
            "\n\nBOOKING: This business has online booking enabled. "
            "When the visitor shows any interest in a service, pricing, or scheduling — or once "
            "they have shared their name and contact info — actively offer to book them an "
            "appointment through the booking link and ask for their preferred day and time. "
            "Make booking the clear next step rather than waiting for them to ask."
        )

    # AI fallback protocol — when enabled, a second-tier managed agent can
    # take over hard questions. Tell first-tier Claude to emit an explicit
    # marker instead of guessing.
    if widget.get("enable_ai_fallback"):
        system_prompt += (
            "\n\nFALLBACK PROTOCOL: If the visitor asks a factual question "
            "about this business (hours, pricing, services, policies, "
            "availability, refunds, guarantees) and the knowledge base above "
            "does not contain enough information to answer confidently, do "
            "NOT guess and do NOT apologize. Instead, end your response with "
            "the exact token `FALLBACK_TO_SUPPORT_AGENT` on its own line. A "
            "more capable agent with tool access will then take over for "
            "that specific question. Only use HANDOFF_REQUESTED if the "
            "customer explicitly asks for a human, shows frustration, or "
            "raises a safety/legal concern. Never include both tokens in "
            "the same message."
        )

    # 7. Append user message to the compact LLM history
    llm_messages = history_for_model + [{"role": "user", "content": req.message}]

    # 8. Reserve this turn against the tenant AI usage guard before calling Claude.
    api_key_present = bool(settings.anthropic_api_key)
    api_key_status = "CONFIGURED" if api_key_present else "MISSING"
    widget_model = resolve_string_setting("widget_chat_model", MODEL)
    widget_max_tokens = resolve_int_setting("widget_chat_max_tokens", MAX_TOKENS)
    usage_reservation = reserve_ai_tokens(
        tenant=tenant,
        estimated_tokens=estimate_widget_chat_tokens(
            system_prompt=system_prompt,
            messages=llm_messages,
            max_tokens=widget_max_tokens,
        ),
        operation="widget_chat.reply",
        session_id=req.session_id,
    )
    if not usage_reservation.allowed:
        usage_limited_text = (
            "Thanks for reaching out. This assistant is temporarily paused "
            "because monthly AI usage is unusually high. The team has been "
            "notified and can follow up directly."
        )
        _save_chat_messages(
            tenant["id"], req.session_id, req.message, usage_limited_text
        )
        fire_event_background(
            tenant["id"],
            "ai_usage.blocked",
            {
                "session_id": req.session_id,
                "conversation_id": conversation_id,
                "reason": usage_reservation.reason,
            },
        )
        return WidgetChatResponse(
            response=usage_limited_text,
            session_id=req.session_id,
            lead_captured=False,
            show_watermark=_watermark,
            handoff=True,
        )

    # 8b. Call Anthropic through the shared runtime so the event loop is not blocked.
    logger.info(
        "widget_chat: calling Anthropic model=%s api_key=%s msg_count=%d system_chars=%d context_ms=%d prompt_profile=%s",
        widget_model,
        api_key_status,
        len(llm_messages),
        len(system_prompt),
        context_duration_ms,
        prompt_profile,
    )
    try:
        llm_result = await call_claude_messages(
            operation="widget_chat.reply",
            model=widget_model,
            max_tokens=widget_max_tokens,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=llm_messages,
            timeout=30.0,
            # Retry transient Anthropic 429/overload once or twice with backoff
            # (runs in the executor thread) so a single blip doesn't dead-end a
            # visitor on the revenue path (audit H3). Retry logic lives in
            # llm_runtime; it defaults to 0 and must be opted into here.
            max_retries=2,
            metadata={
                "tenant_id": tenant["id"],
                "session_id": req.session_id,
                "prompt_profile": prompt_profile,
            },
        )
        assistant_text = llm_result.text or (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
        logger.info(
            "widget_chat: Anthropic success, response_len=%d llm_ms=%d input_tokens=%s output_tokens=%s",
            len(assistant_text),
            llm_result.duration_ms,
            llm_result.input_tokens,
            llm_result.output_tokens,
        )
        usage_record = record_ai_usage(
            reservation=usage_reservation,
            result=llm_result,
            operation="widget_chat.reply",
            session_id=req.session_id,
            model=widget_model,
        )
        if usage_record and usage_record.alert_triggered:
            logger.warning(
                "widget_chat: tenant=%s crossed AI usage alert threshold total_tokens=%s",
                tenant["id"],
                usage_record.total_tokens,
            )
    except anthropic.AuthenticationError as e:
        release_ai_token_reservation(usage_reservation)
        logger.error("widget_chat: Anthropic AUTH error - API key invalid: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.RateLimitError as e:
        release_ai_token_reservation(usage_reservation)
        logger.error("widget_chat: Anthropic RATE LIMIT: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.APIError as e:
        release_ai_token_reservation(usage_reservation)
        logger.error(
            "widget_chat: Anthropic API error status=%s: %s",
            getattr(e, "status_code", "?"),
            e,
        )
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except Exception as e:
        release_ai_token_reservation(usage_reservation)
        logger.exception("widget_chat: unexpected error calling Anthropic: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )

    # 9. Extract order from AI response (restaurant ordering flow)
    order_data = _extract_order_from_response(assistant_text)
    if order_data:
        assistant_text = _strip_order_json_from_response(assistant_text)
        background_tasks.add_task(
            _process_order_from_chat,
            tenant["id"],
            req.session_id,
            order_data,
        )

    # 9b. Extract bid request from AI response (contractor quick-bid flow)
    bid_request_data = _extract_bid_request_from_response(assistant_text)
    if bid_request_data:
        assistant_text = _strip_bid_request_from_response(assistant_text)
        background_tasks.add_task(
            _process_bid_request_from_chat,
            tenant["id"],
            req.session_id,
            bid_request_data,
        )

    # 9ba. Managed-agent fallback (support_agent) — second-tier retry when
    # the first-tier Claude reply explicitly signals it can't answer from
    # the tenant KB alone. Gated on `enable_ai_fallback` per widget config
    # so rollout is per-tenant. See _run_support_fallback below.
    assistant_text, ai_fallback_fired = await _run_support_fallback(
        assistant_text=assistant_text,
        widget=widget,
        tenant_id=tenant["id"],
        session_id=req.session_id,
        customer_message=req.message,
    )

    # 9c. Detect handoff request from AI response
    handoff_triggered = False
    if "HANDOFF_REQUESTED" in assistant_text:
        handoff_triggered = True
        assistant_text = assistant_text.replace("HANDOFF_REQUESTED", "").strip()
        # Tag conversation as handoff
        try:
            conv_result = (
                db.table("conversations")
                .select("id, tags")
                .eq("client_id", tenant["id"])
                .eq("session_id", req.session_id)
                .limit(1)
                .execute()
            )
            if conv_result.data:
                existing_tags = conv_result.data[0].get("tags") or []
                if "handoff" not in existing_tags:
                    updated_tags = existing_tags + ["handoff"]
                    db.table("conversations").update({"tags": updated_tags}).eq(
                        "id", conv_result.data[0]["id"]
                    ).execute()
        except Exception:
            logger.warning(
                "Failed to tag conversation as handoff for session %s",
                req.session_id,
                exc_info=True,
            )

        # Send notification to team (SMS + email + webhook)
        try:
            owner_phone = tenant.get("notification_phone")
            if owner_phone and tenant.get("sms_notifications_enabled"):
                from backend.services.twilio_service import send_sms

                await send_sms(
                    owner_phone,
                    f"[{tenant.get('business_name') or 'Business'}] A customer requested to speak with a team member. Check your inbox.",
                    tenant_id=tenant.get("id"),
                )
        except Exception:
            logger.warning("Failed to send handoff SMS notification", exc_info=True)

        try:
            owner_email = tenant.get("owner_email")
            if owner_email:
                from backend.services.email_sender import send_email

                biz = tenant.get("business_name") or "Your business"
                await send_email(
                    to=owner_email,
                    subject=f"[{biz}] Customer requesting a human",
                    body_html=(
                        "<p>A customer on your website chat is asking to speak with a team member.</p>"
                        "<p>Open the <a href='https://app.agentnexlify.com/dashboard/conversations'>Conversations inbox</a> to reply.</p>"
                    ),
                    tenant_id=tenant["id"],
                )
        except Exception:
            logger.warning("Failed to send handoff email notification", exc_info=True)

        fire_event_background(
            tenant["id"],
            "conversation.handoff",
            {
                "session_id": req.session_id,
                "conversation_id": conversation_id,
            },
        )

    # 10. Save user + assistant messages to chat_messages table
    saved_rows = _save_chat_messages(
        tenant["id"], req.session_id, req.message, assistant_text
    )

    # 10b. Bridge user-side message into the Agent OS inbox (background, opt-in
    # per tenant). The bridge dedup-anchors on chat_messages.id so retries from
    # this same request are idempotent. Skipped silently when toggle is off or
    # the user row didn't insert.
    user_row = next(
        (r for r in saved_rows if r.get("role") == "user"),
        None,
    )
    if user_row and req.message:
        try:
            db_for_bridge = get_service_supabase()
            if is_bridge_enabled(db_for_bridge, tenant["id"], "widget"):
                background_tasks.add_task(
                    bridge_widget,
                    db_for_bridge,
                    tenant["id"],
                    conversation_id,
                    str(user_row["id"]),
                    req.message,
                    {"session_id": req.session_id},
                )
        except Exception:
            logger.warning("os_bridge: widget bridge scheduling failed", exc_info=True)

    # Fire conversation.message webhook
    fire_event_background(
        tenant["id"],
        "conversation.message",
        {
            "session_id": req.session_id,
            "user_message": req.message,
            "assistant_message": assistant_text[:500],
        },
    )

    # 11. Lead capture — runs in background so it doesn't slow the response.
    # Scans ALL messages in the session (not just the current one) for
    # email, phone, and name.  Deduplicates by email + tenant_id.

    # Synchronously detect whether contact info is present so the response
    # can set lead_captured=True immediately (background task does the actual
    # DB write; this check only affects what we report back to the caller).
    _has_contact = bool(_extract_lead_info(req.message))
    if not _has_contact:
        for _m in messages[-5:]:  # scan last 5 messages for prior contact info
            if _m.get("role") == "user" and _extract_lead_info(_m.get("content", "")):
                _has_contact = True
                break

    background_tasks.add_task(
        _capture_leads_from_session,
        tenant["id"],
        req.session_id,
        conversation_id,
    )

    # 11b. Structured-extractor lead enrichment (opt-in per tenant).
    # Runs the structured_extractor managed agent on this single message
    # to fill in name/email/phone/interest/timeline/budget fields the
    # regex parser missed. Background task → zero latency impact on the
    # response. Gated on widget_configs.enable_structured_lead_parser
    # (migration 103, default false). See specs/lead-parser-replacement_spec.md.
    if widget.get("enable_structured_lead_parser"):
        background_tasks.add_task(
            _enrich_lead_from_message,
            tenant["id"],
            req.session_id,
            req.message,
            _extract_lead_info(req.message),
        )

    # 12. AI conversation categorization (every 5th message to save API calls)
    total_msgs = len(messages) + 2  # current user message + assistant reply
    if total_msgs >= 4 and total_msgs % 5 == 0:
        all_msgs = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _categorize_conversation,
            tenant["id"],
            req.session_id,
            all_msgs,
        )

    # 13. AI action item extraction (every 8th message to save API calls)
    if total_msgs >= 6 and total_msgs % 8 == 0:
        all_msgs_for_actions = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _extract_action_items,
            tenant["id"],
            req.session_id,
            all_msgs_for_actions,
        )

    # 14. Response time tracking (first message → first response)
    if total_msgs <= 2:  # First exchange — record response time
        background_tasks.add_task(
            _record_response_metric,
            tenant["id"],
            req.session_id,
            conversation_id,
        )

    # 15. Watermark logic (treat NULL plan as free)
    if (tenant.get("plan") or "free") == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    total_duration_ms = int((perf_counter() - request_started) * 1000)
    logger.info(
        "widget_chat: timing_summary session=%s total_ms=%d context_ms=%d final_history_count=%d handoff=%s",
        req.session_id,
        total_duration_ms,
        context_duration_ms,
        len(history_for_model),
        handoff_triggered,
    )

    return WidgetChatResponse(
        response=assistant_text,
        session_id=req.session_id,
        lead_captured=_has_contact,
        show_watermark=show_watermark,
        handoff=handoff_triggered,
        ai_fallback_fired=ai_fallback_fired,
    )
