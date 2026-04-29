"""Dollar/hours attribution from activity_log.

Phase 2 of ops-automation surfacing. Reads:
- tenants.avg_ticket_override (per-tenant override, mig 111)
- tenants.business_type (vertical lookup, mig 078)
- activity_log rows in current calendar month (UTC) → dollars
- activity_log rows in current ISO week (Mon-Sun UTC) → hours

YAML configs at config/vertical_defaults.yaml + config/hours_saved_formula.yaml,
loaded once via functools.lru_cache.
"""

import functools
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import yaml

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_DEFAULT_AVG_TICKET = Decimal("200")
_DEFAULT_MINUTES = 5


@functools.lru_cache(maxsize=1)
def _load_vertical_defaults() -> dict:
    path = _CONFIG_DIR / "vertical_defaults.yaml"
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


@functools.lru_cache(maxsize=1)
def _load_hours_formula() -> dict:
    path = _CONFIG_DIR / "hours_saved_formula.yaml"
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def _calendar_month_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _iso_week_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def get_avg_ticket(tenant_id: str) -> Decimal:
    """Resolve avg ticket: tenant override → vertical default → 200."""
    try:
        db = get_service_supabase()
        result = (
            db.table("tenants")
            .select("avg_ticket_override, business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
    except Exception:
        logger.warning("get_avg_ticket query failed tenant=%s", tenant_id, exc_info=True)
        return _DEFAULT_AVG_TICKET

    if not rows:
        return _DEFAULT_AVG_TICKET

    row = rows[0]
    override = row.get("avg_ticket_override")
    if override is not None:
        try:
            return Decimal(str(override))
        except Exception:
            logger.warning("avg_ticket_override invalid tenant=%s value=%r", tenant_id, override)

    config = _load_vertical_defaults()
    vertical = row.get("business_type")
    if vertical and vertical in config:
        return Decimal(str(config[vertical]))
    return Decimal(str(config.get("default", _DEFAULT_AVG_TICKET)))


def compute_dollars_this_month(tenant_id: str) -> Decimal:
    """Sum: count(events this calendar month UTC) × avg_ticket."""
    try:
        db = get_service_supabase()
        start = _calendar_month_start_utc()
        result = (
            db.table("activity_log")
            .select("id, activity_type")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start.isoformat())
            .execute()
        )
        rows = result.data or []
    except Exception:
        logger.warning(
            "compute_dollars_this_month query failed tenant=%s", tenant_id, exc_info=True
        )
        return Decimal("0")

    if not rows:
        return Decimal("0")

    avg = get_avg_ticket(tenant_id)
    return avg * Decimal(len(rows))


def compute_hours_this_week(tenant_id: str) -> Decimal:
    """Sum minutes per event type (default 5) → hours, quantized to 0.01."""
    try:
        db = get_service_supabase()
        start = _iso_week_start_utc()
        result = (
            db.table("activity_log")
            .select("activity_type")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start.isoformat())
            .execute()
        )
        rows = result.data or []
    except Exception:
        logger.warning(
            "compute_hours_this_week query failed tenant=%s", tenant_id, exc_info=True
        )
        return Decimal("0")

    if not rows:
        return Decimal("0")

    formula = _load_hours_formula()
    minutes_per_type = formula.get("minutes_per_event_type") or {}
    default_minutes = formula.get("default_minutes", _DEFAULT_MINUTES)

    total_minutes = 0
    for row in rows:
        event_type = row.get("activity_type")
        total_minutes += minutes_per_type.get(event_type, default_minutes)

    hours = Decimal(total_minutes) / Decimal(60)
    return hours.quantize(Decimal("0.01"))
