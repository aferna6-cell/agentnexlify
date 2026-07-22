"""Photo-quote pilot telemetry (#44) — feedback + error-rate + conversion.

Instrumentation logic behind the two GA-gate metrics from the spec: tenant
error rate (<5% goal) and quote->appointment conversion (30% goal). The feedback
+ conversion columns come from migration 185; every read/write here is fail-open,
so the code degrades to "no data" rather than erroring when the migration has not
been applied yet.

``quote_requests`` is ``client_id``-scoped (migration 108). Pure/injectable db so
the aggregation logic is unit-tested without a database.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

VALID_FEEDBACK = frozenset({"correct", "too_low", "too_high", "unclear"})
ERROR_RATE_THRESHOLD = 0.05  # 5% GA gate
DEFAULT_WINDOW_DAYS = 7


def _get_db(db):
    if db is not None:
        return db
    from backend.models.database import get_service_supabase

    return get_service_supabase()


def record_feedback(client_id: str, quote_id: str, feedback: str, *, db=None) -> bool:
    """Store a tenant's rating on a quote. Returns True on success.

    Rejects anything outside ``VALID_FEEDBACK``. Fail-open: a DB error (e.g. the
    column not yet migrated) is logged and returns False, never raised.
    """
    if feedback not in VALID_FEEDBACK:
        return False
    db = _get_db(db)
    try:
        (
            db.table("quote_requests")
            .update({"tenant_feedback": feedback})
            .eq("id", quote_id)
            .eq("client_id", client_id)
            .execute()
        )
        return True
    except Exception:
        logger.warning("photo_quote_telemetry: record_feedback failed for %s", client_id)
        return False


def mark_led_to_appointment(client_id: str, quote_id: str, *, db=None) -> bool:
    """Flag a quote as having converted to an appointment. Fail-open."""
    db = _get_db(db)
    try:
        (
            db.table("quote_requests")
            .update({"led_to_appointment": True})
            .eq("id", quote_id)
            .eq("client_id", client_id)
            .execute()
        )
        return True
    except Exception:
        logger.warning(
            "photo_quote_telemetry: mark_led_to_appointment failed for %s", client_id
        )
        return False


def _window_start(now: datetime, window_days: int) -> str:
    return (now - timedelta(days=window_days)).isoformat()


def compute_error_rate(
    client_id: str,
    *,
    db=None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    now: datetime | None = None,
) -> dict:
    """Rolling tenant-reported error rate: non-'correct' ratings / all ratings.

    Only rated rows count (an un-rated quote is neither correct nor an error).
    Returns ``{rated, errors, error_rate, over_threshold}``. Fail-open -> zeros.
    """
    now = now or datetime.now(timezone.utc)
    db = _get_db(db)
    since = _window_start(now, window_days)
    try:
        rows = (
            db.table("quote_requests")
            .select("tenant_feedback")
            .eq("client_id", client_id)
            .gte("created_at", since)
            .not_.is_("tenant_feedback", "null")
            .execute()
        ).data or []
    except Exception:
        logger.warning("photo_quote_telemetry: error-rate query failed for %s", client_id)
        return {"rated": 0, "errors": 0, "error_rate": 0.0, "over_threshold": False}

    rated = len(rows)
    errors = sum(1 for r in rows if r.get("tenant_feedback") != "correct")
    rate = round(errors / rated, 4) if rated else 0.0
    return {
        "rated": rated,
        "errors": errors,
        "error_rate": rate,
        "over_threshold": rated > 0 and rate > ERROR_RATE_THRESHOLD,
    }


def compute_conversion_rate(
    client_id: str,
    *,
    db=None,
    window_days: int = 30,
    now: datetime | None = None,
) -> dict:
    """Quote->appointment conversion: led_to_appointment / total quotes in window.

    Returns ``{total, converted, conversion_rate}``. Fail-open -> zeros.
    """
    now = now or datetime.now(timezone.utc)
    db = _get_db(db)
    since = _window_start(now, window_days)
    try:
        rows = (
            db.table("quote_requests")
            .select("led_to_appointment")
            .eq("client_id", client_id)
            .gte("created_at", since)
            .execute()
        ).data or []
    except Exception:
        logger.warning("photo_quote_telemetry: conversion query failed for %s", client_id)
        return {"total": 0, "converted": 0, "conversion_rate": 0.0}

    total = len(rows)
    converted = sum(1 for r in rows if r.get("led_to_appointment"))
    rate = round(converted / total, 4) if total else 0.0
    return {"total": total, "converted": converted, "conversion_rate": rate}
