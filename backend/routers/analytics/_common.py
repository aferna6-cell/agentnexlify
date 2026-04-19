"""Shared imports, constants, and helper functions for analytics sub-modules."""

import logging
import time

from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes

# Safety cap for unbounded queries — prevents timeouts on large tenants
_QUERY_LIMIT = 10000


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    # Evict old entries if cache grows too large
    if len(_cache) > 500:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (time.time(), data)


def _period_to_days(period: str) -> int:
    mapping = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    return mapping.get(period, 30)


def _date_range(days: int) -> tuple[str, str]:
    """Return (start_iso, prev_start_iso) for current and previous period."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days * 2)).isoformat()
    return start, prev_start


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


_PRICING_KEYWORDS = [
    "price", "pricing", "cost", "costs", "quote", "estimate",
    "how much", "rate", "rates", "fee", "fees", "charge", "charges",
    "budget", "affordable", "expensive", "cheap", "discount",
]
_BOOKING_KEYWORDS = [
    "book", "booking", "appointment", "schedule", "scheduled", "availability",
    "available", "tomorrow", "today", "this week", "next week", "come in",
]
_URGENT_KEYWORDS = [
    "urgent", "asap", "right away", "immediately", "emergency", "tonight",
    "today", "now", "soon as possible",
]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _score_status(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 60:
        return "watch"
    return "at_risk"


def _first_response_seconds(messages: list[dict]) -> float | None:
    first_user = None
    for message in messages:
        role = message.get("role")
        created_at = _parse_dt(message.get("created_at"))
        if not created_at:
            continue
        if role == "user" and first_user is None:
            first_user = created_at
            continue
        if first_user is not None and role == "assistant":
            return round((created_at - first_user).total_seconds(), 1)
    return None


def _preview_text(text: str | None, limit: int = 140) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit - 3]}..."


def _build_control_center_recommendations(
    total_conversations: int,
    assisted_conversations: int,
    lead_count: int,
    booked_count: int,
    recovery_queue: list[dict],
    pricing_gap_count: int,
    no_response_count: int,
    at_risk_pipeline_value: float,
) -> list[str]:
    recommendations: list[str] = []

    if recovery_queue:
        recommendations.append(
            f"Work the {len(recovery_queue)} live recovery conversations first; they still have customer intent and need a fast follow-up."
        )
    if total_conversations and assisted_conversations < total_conversations:
        coverage_gap = total_conversations - assisted_conversations
        recommendations.append(
            f"Improve assistant coverage on {coverage_gap} conversations that never received a reply, especially after-hours and urgent sessions."
        )
    if lead_count and booked_count < lead_count:
        recommendations.append(
            "Tighten the booking handoff after lead capture so high-intent conversations move directly into an appointment CTA."
        )
    if pricing_gap_count > 0:
        recommendations.append(
            "Add a stronger pricing-to-booking play so quote questions end with a booking link or team handoff instead of stalling."
        )
    if no_response_count > 0:
        recommendations.append(
            "Route unanswered customer-last conversations into a same-day owner queue so no prospect waits without a response."
        )
    if at_risk_pipeline_value > 0:
        recommendations.append(
            f"Protect the ${at_risk_pipeline_value:,.0f} currently sitting in the recovery queue by assigning ownership and triggering follow-up automations."
        )

    if not recommendations:
        recommendations.append(
            "Your recent conversations look healthy; keep reviewing the strongest sessions and use them as templates for prompt and flow improvements."
        )

    return recommendations[:4]
