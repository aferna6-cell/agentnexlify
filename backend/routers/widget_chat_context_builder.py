"""Widget chat context loader + system-prompt assembler.

Extracted from widget_chat.py to keep the route handler focused. Loads
tenant-scoped grounding (FAQ, business hours, corrections, website,
menu, jobs, bid templates, custom fields, active chat flow), assembles
the system prompt, and returns everything the handler needs downstream.

All Supabase calls and cache lookups stay self-contained — caller just
gets back the assembled prompt + the LLM message list.
"""


import logging
from time import perf_counter

from backend.routers.widget_chat_helpers import (
    _CHAT_CACHE_TTL,
    _build_flow_instructions,
    _build_intent_window,
    _build_system_prompt,
    _compact_messages_for_llm,
    _get_cached,
    _needs_bid_context,
    _needs_job_context,
    _set_cache,
)
from backend.services.llm_runtime import resolve_int_setting

logger = logging.getLogger(__name__)


def build_chat_context(
    *,
    tenant: dict,
    widget: dict,
    req,
    messages: list,
    db,
    is_new: bool,
    conversation_id: str,
) -> dict:
    """Load tenant grounding + assemble system prompt for one chat turn.

    Returns dict with:
        system_prompt: str — fully assembled system prompt
        llm_messages: list — compact history + the new user turn
        prompt_profile: dict — diagnostic counts (faq_count, history_messages…)
        context_duration_ms: int — wall-clock for the loading step
        active_flow_id: str | None — id of the chat_flow used, if any
        bh_data: dict | None — business hours row (handler still needs it
            downstream for the null-state guard)
    """
    tid = tenant["id"]
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
                db.table("lead_field_definitions")
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

    # Track flow usage in activity_log for new conversations. Look up
    # log_activity via widget_chat module dynamically so tests patching
    # `backend.routers.widget_chat.log_activity` flow through.
    if active_flow_id and is_new:
        try:
            from backend.routers import widget_chat as _wc

            _wc.log_activity(
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

    # Booking nudge — if online booking is enabled, tell the AI to suggest it
    if widget.get("booking_enabled") and bh_data:
        system_prompt += (
            "\n\nBOOKING: This business has online booking enabled. "
            "When the visitor shows interest in scheduling, mention they can book an appointment "
            "directly through the booking link. Don't push it — only suggest when relevant."
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

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "prompt_profile": prompt_profile,
        "context_duration_ms": context_duration_ms,
        "active_flow_id": active_flow_id,
        "bh_data": bh_data,
    }
