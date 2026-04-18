"""Compatibility re-export barrel for the widget helpers module family.

The 1,673-line god class was split on 2026-04-18 into:
  - widget_chat_helpers.py  — prompt building, conversation history, cache, DB config fetchers
  - widget_lead_helpers.py  — lead extraction, enrichment, capture, notifications
  - widget_booking_helpers.py — booking prep (landing zone; booking logic already in widget_booking.py)

This file re-exports every public name so existing callers — including tests,
branding_service.py, and the four primary routers — continue to import from
`backend.routers.widget_helpers` without modification.

New code should import directly from the specific sub-module:
  from backend.routers.widget_chat_helpers import _build_system_prompt
  from backend.routers.widget_lead_helpers import _capture_leads_from_session

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

# ruff: noqa: F401  (re-exports — all names are intentionally imported)

from backend.routers.widget_chat_helpers import (
    # AI model constants
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    # Cache constants + internals
    _WIDGET_CACHE_TTL,
    _CHAT_CACHE_TTL,
    _cache,
    _get_cached,
    _set_cache,
    _invalidate_cache,
    # Branding
    _BRANDING_PLAN_FIELDS,
    _DANGEROUS_CSS_RE,
    _CSS_URL_RE,
    _FONT_URL_RE,
    _sanitize_css,
    _filter_branding_for_plan,
    # Intent heuristics
    _JOB_CONTEXT_KEYWORDS,
    _BID_CONTEXT_KEYWORDS,
    _build_intent_window,
    _needs_job_context,
    _needs_bid_context,
    # Prompt text helpers
    _truncate_for_prompt,
    _sanitize_reference_text,
    _format_reference_block,
    _format_industry_persona_block,
    _compact_messages_for_llm,
    # DB helpers
    _get_widget_config,
    _get_tenant,
    _normalize_origin_host,
    _check_origin,
    # Conversation history
    _get_or_create_conversation,
    _load_chat_history,
    _save_chat_messages,
    # System prompt
    _format_hours_block,
    _build_system_prompt,
    # Flow builder
    _build_flow_instructions,
    # Metrics
    _record_response_metric,
)

from backend.routers.widget_lead_helpers import (
    # Regex patterns
    NAME_RE,
    STANDALONE_NAME_RE,
    EMAIL_RE,
    PHONE_RE,
    # Constants
    SYSTEM_TAGS,
    _ENRICHMENT_FIELD_MAP,
    # Extraction
    _extract_lead_info,
    _extract_service_interest,
    _build_conversation_summary,
    _extract_tags_from_conversation,
    _categorize_conversation,
    _extract_action_items,
    # Lead capture + notifications
    _capture_leads_from_session,
    _send_new_lead_sms_notification,
    _send_new_lead_email_notification,
    # Enrichment
    _enrich_lead_from_message,
)
