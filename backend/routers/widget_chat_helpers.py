"""Widget chat helpers — re-export shim.

This module was split 2026-05-24 into three focused modules:
- widget_chat_prompt.py — sanitization, system prompt, flow, intent window
- widget_chat_cache.py — TTL cache, widget config + tenant fetchers, origin check
- widget_chat_history.py — conversation lookup, history load/save, response metrics

All names below are re-imported here to preserve patch paths used by tests
and existing call sites (widget_chat.py, widget_config.py, widget_lead.py,
twilio_webhooks.py, widget_lead_helpers.py).

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from backend.routers.widget_chat_cache import (
    _CHAT_CACHE_TTL,
    _WIDGET_CACHE_TTL,
    _cache,
    _check_origin,
    _get_cached,
    _get_tenant,
    _get_widget_config,
    _invalidate_cache,
    _normalize_origin_host,
    _set_cache,
)
from backend.routers.widget_chat_history import (
    _get_or_create_conversation,
    _load_chat_history,
    _record_response_metric,
    _save_chat_messages,
)
from backend.routers.widget_chat_prompt import (
    MAX_TOKENS,
    MODEL,
    TEMPERATURE,
    _BID_CONTEXT_KEYWORDS,
    _JOB_CONTEXT_KEYWORDS,
    _build_flow_instructions,
    _build_intent_window,
    _build_system_prompt,
    _compact_messages_for_llm,
    _format_hours_block,
    _format_industry_persona_block,
    _format_reference_block,
    _needs_bid_context,
    _needs_job_context,
    _sanitize_reference_text,
    _truncate_for_prompt,
)

__all__ = [
    "MAX_TOKENS",
    "MODEL",
    "TEMPERATURE",
    "_BID_CONTEXT_KEYWORDS",
    "_CHAT_CACHE_TTL",
    "_JOB_CONTEXT_KEYWORDS",
    "_WIDGET_CACHE_TTL",
    "_build_flow_instructions",
    "_build_intent_window",
    "_build_system_prompt",
    "_cache",
    "_check_origin",
    "_compact_messages_for_llm",
    "_format_hours_block",
    "_format_industry_persona_block",
    "_format_reference_block",
    "_get_cached",
    "_get_or_create_conversation",
    "_get_tenant",
    "_get_widget_config",
    "_invalidate_cache",
    "_load_chat_history",
    "_needs_bid_context",
    "_needs_job_context",
    "_normalize_origin_host",
    "_record_response_metric",
    "_sanitize_reference_text",
    "_save_chat_messages",
    "_set_cache",
    "_truncate_for_prompt",
]
