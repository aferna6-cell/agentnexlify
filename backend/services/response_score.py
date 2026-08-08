"""Nexlify Score — tenant-facing composite responsiveness score (0-100).

One number the owner can grow (AURA-Index-style retention mechanic), built
deterministically from data we already store — no LLM, no new tables:

  responsiveness (40%) — % of last-30d leads older than an hour that got a
                         first touch (status moved past 'new'). Weighted
                         heaviest because speed-to-lead drives conversion.
  momentum       (25%) — % of open warm/hot leads touched in the last 7
                         days (inverse of the cold-lead ratio; same 7-day
                         bar as the opportunity scanner).
  conversion     (20%) — appointments booked per lead over 30d, scaled so
                         30%+ booking rate = full marks.
  reliability    (15%) — completed vs no-show rate on past appointments.

Empty pipelines score neutral (100 for that component) rather than
punishing brand-new tenants. Every query degrades to neutral on failure —
the endpoint never 500s.

Schema notes: leads use client_id; appointments use tenant_id (handled via
tenant_scope helpers). leads.status is the pipeline column (never
lead_stage).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.os_opportunities import _COLD_DAYS
from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "responsiveness": 0.40,
    "momentum": 0.25,
    "conversion": 0.20,
    "reliability": 0.15,
}
_CONVERSION_TARGET = 0.30  # 30% lead->appointment rate earns full marks
_FIRST_TOUCH_GRACE_HOURS = 1
_WINDOW_DAYS = 30
_ROW_LIMIT = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _pct(numerator: int, denominator: int) -> float:
    """0-100 ratio; empty denominators score neutral (100)."""
    if denominator <= 0:
        return 100.0
    return round(min(100.0, (numerator / denominator) * 100.0), 1)


def compute_response_score(db: Any, tenant_id: str) -> dict[str, Any]:
    """Composite score + per-component breakdown for the dashboard card."""
    window_start = (_now() - timedelta(days=_WINDOW_DAYS)).isoformat()

    # responsiveness — leads older than the grace hour that left 'new'
    responsiveness = 100.0
    try:
        rows = (
            tenant_select(db, "leads", tenant_id, "id, status, created_at")
            .gte("created_at", window_start)
            .limit(_ROW_LIMIT)
            .execute()
        ).data or []
        grace = _now() - timedelta(hours=_FIRST_TOUCH_GRACE_HOURS)
        due = [
            r
            for r in rows
            if (r.get("created_at") or "") < grace.isoformat()
        ]
        touched = [r for r in due if (r.get("status") or "new") != "new"]
        responsiveness = _pct(len(touched), len(due))
        lead_count = len(rows)
    except Exception:
        logger.warning("response_score: responsiveness failed for %s", tenant_id, exc_info=True)
        lead_count = 0

    # momentum — open warm/hot leads NOT gone quiet
    momentum = 100.0
    try:
        warm = (
            tenant_select(db, "leads", tenant_id, "id, updated_at")
            .in_("lead_temperature", ["warm", "hot"])
            .limit(_ROW_LIMIT)
            .execute()
        ).data or []
        cold_cutoff = (_now() - timedelta(days=_COLD_DAYS)).isoformat()
        active = [r for r in warm if (r.get("updated_at") or "") >= cold_cutoff]
        momentum = _pct(len(active), len(warm))
    except Exception:
        logger.warning("response_score: momentum failed for %s", tenant_id, exc_info=True)

    # conversion — appointments per lead, scaled to the 30% target
    conversion = 100.0
    appt_rows: list[dict] = []
    try:
        appt_rows = (
            tenant_select(db, "appointments", tenant_id, "id, status, start_time")
            .gte("created_at", window_start)
            .limit(_ROW_LIMIT)
            .execute()
        ).data or []
        if lead_count > 0:
            rate = len(appt_rows) / lead_count
            conversion = round(min(100.0, (rate / _CONVERSION_TARGET) * 100.0), 1)
    except Exception:
        logger.warning("response_score: conversion failed for %s", tenant_id, exc_info=True)

    # reliability — completed vs no-show on appointments already past
    reliability = 100.0
    try:
        finished = [
            a for a in appt_rows if a.get("status") in ("completed", "no_show")
        ]
        completed = [a for a in finished if a.get("status") == "completed"]
        reliability = _pct(len(completed), len(finished))
    except Exception:
        logger.warning("response_score: reliability failed for %s", tenant_id, exc_info=True)

    components = {
        "responsiveness": responsiveness,
        "momentum": momentum,
        "conversion": conversion,
        "reliability": reliability,
    }
    score = round(sum(components[k] * w for k, w in _WEIGHTS.items()), 1)

    return {
        "score": score,
        "grade": _grade(score),
        "components": components,
        "weights": _WEIGHTS,
        "window_days": _WINDOW_DAYS,
    }
