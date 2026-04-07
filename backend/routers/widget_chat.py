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
from backend.models.database import get_supabase
from backend.models.schemas import WidgetChatRequest, WidgetChatResponse
from backend.services.activity import log_activity
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers.widget_helpers import (
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    _CHAT_CACHE_TTL,
    _build_flow_instructions,
    _build_intent_window,
    _build_system_prompt,
    _compact_messages_for_llm,
    _capture_leads_from_session,
    _categorize_conversation,
    _check_origin,
    _extract_action_items,
    _extract_lead_info,
    _get_cached,
    _get_or_create_conversation,
    _get_tenant,
    _get_widget_config,
    _load_chat_history,
    _needs_bid_context,
    _needs_job_context,
    _record_response_metric,
    _save_chat_messages,
    _set_cache,
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


@router.post("/chat", response_model=WidgetChatResponse)
@limiter.limit("60/minute")
async def widget_chat(request: Request, req: WidgetChatRequest, background_tasks: BackgroundTasks):
    """Process a chat message through the multi-tenant widget pipeline."""
    request_started = perf_counter()
    logger.info("widget_chat: received request session=%s api_key=%s...%s",
                req.session_id, req.api_key[:8] if req.api_key else "NONE",
                req.api_key[-4:] if req.api_key else "")

    # 1. Look up widget config + tenant
    widget = _get_widget_config(req.api_key)
    tenant = _get_tenant(widget["tenant_id"])
    logger.info("widget_chat: tenant=%s business=%s", tenant["id"], tenant.get("business_name"))

    # 2. Origin check
    _check_origin(request, widget.get("allowed_domains"))

    # 2b. Free trial expiry check
    if (tenant.get("plan") or "free") == "free" and tenant.get("free_trial_started_at"):
        from datetime import datetime, timezone
        trial_started = tenant["free_trial_started_at"]
        if isinstance(trial_started, str):
            trial_started = datetime.fromisoformat(trial_started.replace("Z", "+00:00"))
        if trial_started.tzinfo is None:
            trial_started = trial_started.replace(tzinfo=timezone.utc)
        elapsed_days = (datetime.now(timezone.utc) - trial_started).days
        if elapsed_days >= 14:
            return WidgetChatResponse(
                response="Your free trial has expired. Upgrade your plan to continue using your AI assistant.",
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=True,
                trial_expired=True,
            )

    # 3. All plans now have unlimited conversations (limit check removed).

    # 4. Get or create conversation
    conversation_id, is_new = _get_or_create_conversation(tenant["id"], req.session_id)
    logger.info("widget_chat: conversation=%s is_new=%s", conversation_id, is_new)

    # Fire conversation.started webhook for new sessions
    if is_new:
        fire_event_background(tenant["id"], "conversation.started", {
            "session_id": req.session_id,
            "conversation_id": conversation_id,
        })

    # Get DB handle for conversation operations
    db = get_supabase()

    # Increment usage counter only for new conversations
    if is_new:
        try:
            current_used = tenant.get("conversations_used_this_month", 0) or 0
            db.table("tenants").update(
                {"conversations_used_this_month": current_used + 1}
            ).eq("id", tenant["id"]).execute()
        except Exception:
            logger.warning("Failed to increment usage counter for tenant %s", tenant["id"], exc_info=True)

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
        logger.warning("handoff check failed for session %s", req.session_id, exc_info=True)

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
            pass

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
    _content_mode_keywords = ["repurpose", "content mode", "turn this into", "create content from"]
    _yt_pattern = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")
    _msg_lower = req.message.lower()
    _content_mode = getattr(req, "content_mode", False)
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
        plan = (tenant.get("plan") or "free")
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
            from backend.services.content_repurposer import extract_source, repurpose as do_repurpose
            source = await extract_source(_src_type, req.message.strip())
            outputs = await do_repurpose(
                source_content=source["content"],
                title=source["title"],
                tenant_id=tenant["id"],
                tone="professional",
            )
            db.table("repurpose_jobs").insert({
                "tenant_id": tenant["id"],
                "source_type": _src_type,
                "source_url": source["source_url"],
                "source_content": source["content"],
                "source_title": source["title"],
                "outputs": outputs,
                "status": "completed",
                "created_via": "widget",
            }).execute()
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
        req.session_id, len(messages),
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
        logger.info("widget_chat: junk_shortcircuit=True session=%s msg=%r (skipped Claude API)", req.session_id, _stripped)
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
            logger.info("widget_chat: greeting_shortcircuit=True session=%s first_turn=True (skipped Claude API)", req.session_id)
            return WidgetChatResponse(
                response=_opening,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=_watermark,
                handoff=False,
            )

        # Session already has at least one exchange - this is a repeat greeting
        _prior_user_greeted = any(
            m["role"] == "user" and re.sub(r"[^a-z]", "", m.get("content", "").strip().lower()) in _GREETINGS
            for m in messages
        )
        if _prior_user_greeted:
            _biz_name = tenant.get("business_name") or "us"
            _canned = (
                f"I'm still here! Is there something specific I can help you with? "
                f"I can answer questions about {_biz_name} - pricing, services, how to get started, and more."
            )
            _save_chat_messages(tenant["id"], req.session_id, req.message, _canned)
            logger.info("widget_chat: greeting_shortcircuit=True session=%s (skipped Claude API)", req.session_id)
            return WidgetChatResponse(
                response=_canned,
                session_id=req.session_id,
                lead_captured=False,
                show_watermark=_watermark,
                handoff=False,
            )

    # 5c. Null-state guard — if bot has no knowledge at all, show a graceful fallback
    _has_kb = bool(widget.get("knowledge_base"))
    _has_ci = bool(widget.get("custom_instructions"))
    if not _has_kb and not _has_ci and len(messages) == 0:
        _biz = tenant.get("business_name") or "our team"
        _phone = tenant.get("phone") or ""
        _phone_msg = f" You can also reach us at {_phone}." if _phone else ""
        _setup_msg = (
            f"Thanks for reaching out! Our chat assistant is still being set up. "
            f"In the meantime, please contact {_biz} directly for assistance.{_phone_msg}"
        )
        _save_chat_messages(tenant["id"], req.session_id, req.message, _setup_msg)
        logger.info("widget_chat: null_state_guard session=%s tenant=%s (no KB or CI)", req.session_id, tenant["id"])
        return WidgetChatResponse(
            response=_setup_msg,
            session_id=req.session_id,
            lead_captured=False,
            show_watermark=_watermark,
            handoff=False,
        )

    # 6. Build system prompt with compact, intent-aware context.
    tid = tenant["id"]
    db = get_supabase()
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
            logger.warning("business_hours query failed for tenant %s", tid, exc_info=True)
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
                .not_.is_("correction", "null")
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
                logger.warning("website_content load failed for tenant %s", tid, exc_info=True)
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
            logger.warning("menu_items query failed for tenant %s", tenant["id"], exc_info=True)

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
            logger.warning("jobs query failed for tenant %s", tenant["id"], exc_info=True)

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
                logger.warning("bid_templates query failed for tenant %s", tid, exc_info=True)
                bid_templates = []
            _set_cache(f"bidtpl:{tid}", bid_templates)

    custom_field_defs = []
    if needs_bid_context:
        try:
            cf_result = (
                db.table("lead_field_definitions")
                .select("field_name, field_type, options, is_required")
                .eq("tenant_id", tid)
                .order("sort_order")
                .limit(20)
                .execute()
            )
            custom_field_defs = cf_result.data if cf_result.data else []
        except Exception:
            logger.debug("custom field defs query failed for tenant %s", tid, exc_info=True)

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
        logger.warning("chat_flows query failed for tenant %s", tenant["id"], exc_info=True)

    system_prompt = _build_system_prompt(
        tenant, faq_data, bh_data, corrections, website_content,
        menu_items, job_listings, bid_templates=bid_templates or None,
        custom_field_defs=custom_field_defs or None,
        custom_instructions=widget.get("custom_instructions") or None,
        knowledge_base=widget.get("knowledge_base") or None,
    )

    # Inject active flow instructions into system prompt
    if active_flow and active_flow.get("nodes"):
        flow_instructions = _build_flow_instructions(active_flow)
        if flow_instructions:
            flow_chars = resolve_int_setting("widget_prompt_flow_chars", 1500)
            if len(flow_instructions) > flow_chars:
                flow_instructions = flow_instructions[: flow_chars - 18].rstrip() + "\n[Flow truncated]"
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
                description=f"Chat flow used in conversation",
                metadata={
                    "flow_id": active_flow_id,
                    "session_id": req.session_id,
                    "conversation_id": conversation_id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to log flow_used for tenant %s flow %s",
                tenant["id"], active_flow_id, exc_info=True,
            )

    # Use bot_name from widget config in the system prompt
    if widget.get("bot_name"):
        system_prompt = system_prompt.replace("AI Assistant", widget["bot_name"], 1)

    # 7. Append user message to the compact LLM history
    llm_messages = history_for_model + [{"role": "user", "content": req.message}]

    # 8. Call Anthropic through the shared runtime so the event loop is not blocked.
    api_key_present = bool(settings.anthropic_api_key)
    api_key_status = "CONFIGURED" if api_key_present else "MISSING"
    widget_model = resolve_string_setting("widget_chat_model", MODEL)
    widget_max_tokens = resolve_int_setting("widget_chat_max_tokens", MAX_TOKENS)
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
    except anthropic.AuthenticationError as e:
        logger.error("widget_chat: Anthropic AUTH error - API key invalid: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.RateLimitError as e:
        logger.error("widget_chat: Anthropic RATE LIMIT: %s", e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except anthropic.APIError as e:
        logger.error("widget_chat: Anthropic API error status=%s: %s", getattr(e, 'status_code', '?'), e)
        assistant_text = (
            "I'm sorry, I'm having trouble right now. "
            "Please try again in a moment or contact us directly."
        )
    except Exception as e:
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
            _process_order_from_chat, tenant["id"], req.session_id, order_data,
        )

    # 9b. Extract bid request from AI response (contractor quick-bid flow)
    bid_request_data = _extract_bid_request_from_response(assistant_text)
    if bid_request_data:
        assistant_text = _strip_bid_request_from_response(assistant_text)
        background_tasks.add_task(
            _process_bid_request_from_chat, tenant["id"], req.session_id, bid_request_data,
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
            logger.warning("Failed to tag conversation as handoff for session %s", req.session_id, exc_info=True)

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
                        f"<p>A customer on your website chat is asking to speak with a team member.</p>"
                        f"<p>Open the <a href='https://app.agentnexlify.com/dashboard/conversations'>Conversations inbox</a> to reply.</p>"
                    ),
                    tenant_id=tenant["id"],
                )
        except Exception:
            logger.warning("Failed to send handoff email notification", exc_info=True)

        fire_event_background(tenant["id"], "conversation.handoff", {
            "session_id": req.session_id,
            "conversation_id": conversation_id,
        })

    # 10. Save user + assistant messages to chat_messages table
    _save_chat_messages(tenant["id"], req.session_id, req.message, assistant_text)

    # Fire conversation.message webhook
    fire_event_background(tenant["id"], "conversation.message", {
        "session_id": req.session_id,
        "user_message": req.message,
        "assistant_message": assistant_text[:500],
    })

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
        _capture_leads_from_session, tenant["id"], req.session_id, conversation_id,
    )

    # 12. AI conversation categorization (every 5th message to save API calls)
    total_msgs = len(messages) + 2  # current user message + assistant reply
    if total_msgs >= 4 and total_msgs % 5 == 0:
        all_msgs = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _categorize_conversation, tenant["id"], req.session_id, all_msgs,
        )

    # 13. AI action item extraction (every 8th message to save API calls)
    if total_msgs >= 6 and total_msgs % 8 == 0:
        all_msgs_for_actions = messages + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_text},
        ]
        background_tasks.add_task(
            _extract_action_items, tenant["id"], req.session_id, all_msgs_for_actions,
        )

    # 14. Response time tracking (first message → first response)
    if total_msgs <= 2:  # First exchange — record response time
        background_tasks.add_task(
            _record_response_metric, tenant["id"], req.session_id, conversation_id,
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
    )
