"""Re-export shim — canonical module is backend.services.analytics_common.

Kept so the analytics router modules' existing `from ._common import ...`
lines stay valid; the shim imports DOWNWARD from services (correct layer
direction, audit 2026-07-14 M2). Aliased names share object identity with the
service module, so the mutable `_cache` stays a single shared dict.
"""

from backend.services.analytics_common import (  # noqa: F401
    _BOOKING_KEYWORDS,
    _CACHE_TTL,
    _PRICING_KEYWORDS,
    _QUERY_LIMIT,
    _URGENT_KEYWORDS,
    _build_control_center_recommendations,
    _cache,
    _clamp_score,
    _date_range,
    _first_response_seconds,
    _get_cached,
    _parse_dt,
    _pct_change,
    _period_to_days,
    _preview_text,
    _ratio,
    _safe_float,
    _score_status,
    _set_cache,
    logger,
)
