"""Attribution service — computes dollar and hour estimates from activity_log.

Uses vertical_defaults.yaml for avg_ticket and hours_saved_per_event.
Tenants may override avg_ticket via avg_ticket_override column on tenants table.
"""

import functools
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def get_service_supabase():
    # Deferred import — keeps module importable without supabase credentials at test time.
    from backend.models.database import get_service_supabase as _get

    return _get()


_YAML_PATH = Path(__file__).parent.parent.parent / "config" / "vertical_defaults.yaml"


@functools.lru_cache(maxsize=1)
def _load_defaults() -> dict:
    with open(_YAML_PATH) as f:
        return yaml.safe_load(f)["verticals"]


def get_avg_ticket(vertical: str | None) -> float:
    defaults = _load_defaults()
    v = (vertical or "").lower().replace(" ", "_")
    entry = defaults.get(v) or defaults.get("default", {})
    return float(entry.get("avg_ticket", 200))


def _hours_saved_per_event(vertical: str | None) -> float:
    defaults = _load_defaults()
    v = (vertical or "").lower().replace(" ", "_")
    entry = defaults.get(v) or defaults.get("default", {})
    return float(entry.get("hours_saved_per_event", 0.5))


def compute_dollars_this_month(tenant_id: str) -> float:
    """Sum avg_ticket * missed_call_textback events this calendar month."""
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        tenant = (
            db.table("tenants")
            .select("avg_ticket_override, vertical")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        row = tenant.data[0] if tenant.data else {}
        override = row.get("avg_ticket_override")
        vertical = row.get("vertical")
        ticket = float(override) if override else get_avg_ticket(vertical)

        events = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("action", "missed_call_textback")
            .gte("created_at", month_start.isoformat())
            .execute()
        )
        count = events.count if events.count is not None else len(events.data or [])
        return round(ticket * count, 2)
    except Exception:
        logger.warning(
            "attribution: compute_dollars failed tenant=%s", tenant_id, exc_info=True
        )
        return 0.0


def compute_hours_this_week(tenant_id: str) -> float:
    """Sum hours_saved_per_event * all automation events this week."""
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        tenant = (
            db.table("tenants")
            .select("vertical")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        row = tenant.data[0] if tenant.data else {}
        vertical = row.get("vertical")
        hrs = _hours_saved_per_event(vertical)

        events = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_start.isoformat())
            .execute()
        )
        count = events.count if events.count is not None else len(events.data or [])
        return round(hrs * count, 2)
    except Exception:
        logger.warning(
            "attribution: compute_hours failed tenant=%s", tenant_id, exc_info=True
        )
        return 0.0
