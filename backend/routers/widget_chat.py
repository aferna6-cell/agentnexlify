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
from backend.services.activity import log_activity  # noqa: F401 — re-exported for sibling modules
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.widget_chat_helpers import (
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    _CHAT_CACHE_TTL,
    _check_origin,
    _get_cached,
    _get_or_create_conversation,
    _get_tenant,
    _get_widget_config,
    _load_chat_history,
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


# FALLBACK_MARKER / FALLBACK_TIMEOUT_SECONDS / _run_support_fallback live in
# widget_chat_fallback.py. Re-exported here so tests can still patch
# `backend.routers.widget_chat.FALLBACK_MARKER` and
# `backend.routers.widget_chat._run_support_fallback`.
from backend.routers.widget_chat_fallback import (  # noqa: F401, E402
    FALLBACK_MARKER,
    FALLBACK_TIMEOUT_SECONDS,
    _run_support_fallback,
)
from backend.routers.widget_chat_context_builder import build_chat_context


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

    # 6. Build system prompt with compact, intent-aware context. All
    # tenant-grounding loads + system-prompt assembly live in
    # widget_chat_context_builder.build_chat_context.
    db = get_service_supabase()
    _ctx = build_chat_context(
        tenant=tenant,
        widget=widget,
        req=req,
        messages=messages,
        db=db,
        is_new=is_new,
        conversation_id=conversation_id,
    )
    system_prompt = _ctx["system_prompt"]
    llm_messages = _ctx["llm_messages"]
    prompt_profile = _ctx["prompt_profile"]
    context_duration_ms = _ctx["context_duration_ms"]
    active_flow_id = _ctx["active_flow_id"]
    bh_data = _ctx["bh_data"]

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
    _save_chat_messages(tenant["id"], req.session_id, req.message, assistant_text)

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
        prompt_profile["history_messages"],
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
