"""Widget chat endpoint — main /api/v1/widget/chat POST handler.

Split per issue #472: this module keeps the route orchestration + the
Claude call; the pipeline stages live in sibling modules:

  - widget_chat_guards.py   — pre-LLM short-circuits (handoff-mode,
                              content-mode, junk/greeting, null-state,
                              turn-budget, input screen)
  - widget_chat_context.py  — grounding loads + system-prompt assembly
  - widget_chat_effects.py  — usage counter, handoff detection/notify,
                              post-response background fan-out
  - widget_chat_fallback.py — second-tier managed-agent fallback

The Claude call (`call_claude_messages`) and per-message KB retrieval
(`_query_kb_articles`) are invoked from THIS module on purpose — tests
patch them at `backend.routers.widget_chat.*`.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging
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
from backend.services.webhook_dispatcher import fire_event_background
from backend.routers import widget_chat_effects, widget_chat_guards
from backend.routers.widget_chat_context import build_chat_context
from backend.routers.widget_chat_fallback import (  # noqa: F401 - re-exported
    FALLBACK_MARKER,
    FALLBACK_TIMEOUT_SECONDS,
    _run_support_fallback,
)
from backend.routers.widget_chat_helpers import (
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    _check_origin,
    _get_or_create_conversation,
    _get_tenant,
    _get_widget_config,
    _load_chat_history,
    _query_kb_articles,
    _save_chat_messages,
    is_low_confidence_turn,
    LOW_CONFIDENCE_FALLBACK_TEXT,
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

    db = get_service_supabase()

    if is_new:
        widget_chat_effects.on_new_conversation(
            background_tasks, tenant, req, conversation_id
        )
        widget_chat_effects.increment_usage_counter(db, tenant)

    # 4b. Check if conversation is in handoff mode (team member handling)
    guard_response = widget_chat_guards.check_handoff_mode(db, tenant, widget, req)
    if guard_response is not None:
        return guard_response

    # 4c. Content mode detection — repurpose content instead of chatting
    guard_response = await widget_chat_guards.maybe_run_content_mode(
        db, tenant, widget, req
    )
    if guard_response is not None:
        return guard_response

    # 5. Load message history from chat_messages table (last 20 messages)
    messages = _load_chat_history(tenant["id"], req.session_id)
    logger.info(
        "widget_chat: session=%s loaded %d previous messages, first_role=%s",
        req.session_id,
        len(messages),
        messages[0]["role"] if messages else "NONE",
    )

    _watermark = widget_chat_guards.early_watermark(tenant, widget)

    # 5b. Spam short-circuit — skip Claude API for junk and repeat greetings
    guard_response = widget_chat_guards.junk_or_greeting_shortcircuit(
        tenant, widget, req, messages, _watermark
    )
    if guard_response is not None:
        return guard_response

    # 5c. Null-state guard — bot with NO grounding shows a graceful fallback.
    guard_response = widget_chat_guards.null_state_guard(
        tenant, widget, req, messages, _watermark
    )
    if guard_response is not None:
        return guard_response

    # 5d. Turn budget + prompt-injection/abuse guard — runs right before the
    # expensive context build + Sonnet call so short-circuited turns above
    # never pay for it. Both fail open on error (widget_guard.py).
    guard_response = widget_chat_guards.turn_budget_guard(tenant, req, _watermark)
    if guard_response is not None:
        return guard_response

    guard_response = await widget_chat_guards.input_screen_guard(
        tenant, req, _watermark
    )
    if guard_response is not None:
        return guard_response

    # 6. KB article retrieval — one DB/FTS round trip per message.
    # Gated on widget_kb_articles_enabled (default 1 = ON). Failures yield []
    # so the chat response is never blocked. Stays in this module: tests patch
    # `backend.routers.widget_chat._query_kb_articles`.
    kb_article_refs = []
    _kb_retrieval_enabled = bool(resolve_int_setting("widget_kb_articles_enabled", 1))
    if _kb_retrieval_enabled:
        try:
            kb_article_refs = await _query_kb_articles(req.message)
        except Exception:
            logger.warning(
                "widget_chat: kb_articles retrieval failed for session=%s — "
                "continuing without KB augmentation",
                req.session_id,
                exc_info=True,
            )

    # 6b. Build system prompt with compact, intent-aware context.
    ctx = build_chat_context(
        db=db,
        tenant=tenant,
        widget=widget,
        req=req,
        messages=messages,
        kb_article_refs=kb_article_refs,
        conversation_id=conversation_id,
        is_new=is_new,
    )
    system_prompt = ctx.system_prompt

    # 7. Append user message to the compact LLM history
    llm_messages = ctx.history_for_model + [{"role": "user", "content": req.message}]

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
        ctx.context_duration_ms,
        ctx.prompt_profile,
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
            # Opt-in Anthropic prompt caching (cost lever F4): the tenant KB +
            # persona block above is the stable prefix repeated on every turn
            # of a conversation. Default 5-min ephemeral TTL matches this
            # always-on FastAPI process's turn cadence. Anthropic caches on
            # the exact text hash, so each tenant's distinct system_prompt
            # gets its own cache entry — no cross-tenant leak, no shared key.
            cache_system=True,
            metadata={
                "tenant_id": tenant["id"],
                "session_id": req.session_id,
                "prompt_profile": ctx.prompt_profile,
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
    # so rollout is per-tenant. See widget_chat_fallback.py.
    assistant_text, ai_fallback_fired = await _run_support_fallback(
        assistant_text=assistant_text,
        widget=widget,
        tenant_id=tenant["id"],
        session_id=req.session_id,
        customer_message=req.message,
    )

    # 9bb. Confidence-gated retrieval — when this turn's per-message KB
    # article search came back thin AND the model's own answer already
    # reads uncertain, hand off to a human instead of risking a
    # hallucinated answer. Skipped when the managed-agent fallback (9ba)
    # already replaced this turn, or when the model already asked for a
    # human itself. Non-fatal: any error here falls back to the model's
    # answer unchanged. See widget_chat_helpers.is_low_confidence_turn for
    # the full signal rationale.
    if not ai_fallback_fired and "HANDOFF_REQUESTED" not in assistant_text:
        try:
            if is_low_confidence_turn(
                message=req.message,
                kb_article_refs=kb_article_refs,
                kb_retrieval_attempted=_kb_retrieval_enabled,
                assistant_text=assistant_text,
            ):
                logger.info(
                    "widget_chat: confidence_gate LOW_CONFIDENCE session=%s — "
                    "routing to human handoff instead of model answer",
                    req.session_id,
                )
                assistant_text = LOW_CONFIDENCE_FALLBACK_TEXT
        except Exception:
            logger.warning(
                "widget_chat: confidence gate check failed for session=%s — "
                "falling back to model answer unchanged",
                req.session_id,
                exc_info=True,
            )

    # 9c. Detect handoff request from AI response (tag + owner notify)
    assistant_text, handoff_triggered = (
        await widget_chat_effects.handle_handoff_detection(
            db, tenant, req, conversation_id, assistant_text
        )
    )

    # 10. Save user + assistant messages to chat_messages table
    saved_rows = _save_chat_messages(
        tenant["id"], req.session_id, req.message, assistant_text
    )

    # 10b-14. Post-response fan-out: OS bridge, message webhook, lead capture,
    # enrichment, categorization, action items, first-response metric.
    _has_contact = widget_chat_effects.schedule_post_response_effects(
        background_tasks,
        tenant=tenant,
        widget=widget,
        req=req,
        conversation_id=conversation_id,
        messages=messages,
        assistant_text=assistant_text,
        saved_rows=saved_rows,
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
        ctx.context_duration_ms,
        len(ctx.history_for_model),
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
