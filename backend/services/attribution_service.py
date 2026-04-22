"""Attribution service — dollar recovery + hours saved calculations.

Phase 2: computes per-tenant dollars recovered this month and hours saved
this week from automation activity events.

YAML configs loaded once via functools.lru_cache (process-lifetime cache).
Never raises — all public functions return 0 / 0.0 on error.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from functools import lru_cache

import yaml

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Path to config YAMLs — resolved relative to project root
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_VERTICAL_DEFAULTS_PATH = os.path.join(
    _PROJECT_ROOT, "config", "vertical_defaults.yaml"
)
_HOURS_FORMULA_PATH = os.path.join(_PROJECT_ROOT, "config", "hours_saved_formula.yaml")


@lru_cache(maxsize=1)
def _load_vertical_defaults() -> dict:
    """Load config/vertical_defaults.yaml once per process."""
    try:
        with open(_VERTICAL_DEFAULTS_PATH, "r") as f:
            data = yaml.safe_load(f)
        return data.get("avg_ticket", {})
    except Exception:
        logger.warning("Failed to load vertical_defaults.yaml", exc_info=True)
        return {"default": 200}


@lru_cache(maxsize=1)
def _load_hours_formula() -> dict:
    """Load config/hours_saved_formula.yaml once per process."""
    try:
        with open(_HOURS_FORMULA_PATH, "r") as f:
            data = yaml.safe_load(f)
        return data.get("hours_per_event", {})
    except Exception:
        logger.warning("Failed to load hours_saved_formula.yaml", exc_info=True)
        return {"default": 0.2}


def get_avg_ticket(
    tenant_id: str,
    vertical: str | None,
    override: float | None,
) -> float:
    """Return average ticket value for attribution.

    Priority: override column > YAML vertical default > global default $200.

    Args:
        tenant_id: Tenant UUID (unused directly — passed for logging context).
        vertical: Value from tenants.business_type column.
        override: Value from tenants.avg_ticket_override column (None if not set).

    Returns:
        Dollar amount as float.
    """
    if override is not None:
        return float(override)

    defaults = _load_vertical_defaults()
    if vertical and vertical in defaults:
        return float(defaults[vertical])

    return float(defaults.get("default", 200))


def _fetch_tenant(tenant_id: str) -> dict | None:
    """Fetch tenant row with business_type + avg_ticket_override."""
    try:
        db = get_service_supabase()
        result = (
            db.table("tenants")
            .select("id, business_type, avg_ticket_override")
            .eq("id", tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "Failed to fetch tenant %s for attribution", tenant_id, exc_info=True
        )
        return None


def _count_events_this_month(tenant_id: str) -> int:
    """Count activity_log events for tenant in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        db = get_service_supabase()
        result = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", month_start.isoformat())
            .execute()
        )
        return result.count if result.count is not None else len(result.data or [])
    except Exception:
        logger.warning(
            "Failed to count events this month tenant=%s", tenant_id, exc_info=True
        )
        return 0


def _get_events_this_week(tenant_id: str) -> list[dict]:
    """Return activity_log rows for tenant in the last 7 days."""
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        db = get_service_supabase()
        result = (
            db.table("activity_log")
            .select("activity_type")
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_start.isoformat())
            .execute()
        )
        return result.data or []
    except Exception:
        logger.warning(
            "Failed to get events this week tenant=%s", tenant_id, exc_info=True
        )
        return []


def compute_dollars_this_month(tenant_id: str) -> float:
    """Return estimated dollars recovered this month for a tenant.

    Formula: avg_ticket * count(activity_log rows this calendar month).

    Returns 0.0 on any error.
    """
    try:
        tenant = _fetch_tenant(tenant_id)
        if not tenant:
            return 0.0

        avg_ticket = get_avg_ticket(
            tenant_id=tenant_id,
            vertical=tenant.get("business_type"),
            override=tenant.get("avg_ticket_override"),
        )
        event_count = _count_events_this_month(tenant_id)
        return float(avg_ticket * event_count)
    except Exception:
        logger.warning(
            "compute_dollars_this_month failed tenant=%s", tenant_id, exc_info=True
        )
        return 0.0


def compute_hours_this_week(tenant_id: str) -> float:
    """Return estimated staff hours saved this week for a tenant.

    Formula: sum(hours_per_event[activity_type]) for events in last 7 days.
    Unknown activity types use the 'default' formula value.

    Returns 0.0 on any error.
    """
    try:
        events = _get_events_this_week(tenant_id)
        formula = _load_hours_formula()
        default_hours = formula.get("default", 0.2)

        total = sum(
            formula.get(event.get("activity_type", ""), default_hours)
            for event in events
        )
        return round(float(total), 2)
    except Exception:
        logger.warning(
            "compute_hours_this_week failed tenant=%s", tenant_id, exc_info=True
        )
        return 0.0
