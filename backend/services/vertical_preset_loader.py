"""Vertical preset loader — DB-first with YAML fallback.

Loads trade vertical defaults (services, FAQs, hours) from the vertical_presets
Supabase table. Falls back to config/vertical_defaults.yaml when the DB is
unavailable or a preset is missing from the table.

This module is read-only. It never writes to the DB.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

YAML_PATH = Path(__file__).parent.parent.parent / "config" / "vertical_defaults.yaml"

_VALID_VERTICALS = frozenset(
    ["plumbing", "hvac", "cleaning", "power_washing", "landscaping", "electrical"]
)


async def get_vertical_preset(vertical: str) -> Optional[dict]:
    """Load preset from DB; fall back to YAML on miss or DB error.

    Args:
        vertical: One of the 6 supported vertical slugs.

    Returns:
        Dict with keys: vertical, display_name, default_services, default_faqs,
        default_hours, avg_ticket_amount, avg_hours_saved_per_lead.
        None if the vertical is not recognised.
    """
    if vertical not in _VALID_VERTICALS:
        logger.warning("get_vertical_preset: unknown vertical %r", vertical)
        return None

    try:
        supabase = get_service_supabase()
        result = (
            supabase.table("vertical_presets")
            .select("*")
            .eq("vertical", vertical)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        logger.info(
            "get_vertical_preset: %r not found in DB, using YAML fallback", vertical
        )
    except Exception:
        logger.exception(
            "get_vertical_preset: DB query failed for %r, falling back to YAML",
            vertical,
        )

    return _load_yaml_preset(vertical)


async def list_verticals() -> list[dict]:
    """Return all verticals with display names.

    Tries DB first; falls back to YAML on error. Each entry contains at minimum
    'vertical' and 'display_name' keys.

    Returns:
        List of dicts, one per supported vertical.
    """
    try:
        supabase = get_service_supabase()
        result = (
            supabase.table("vertical_presets")
            .select(
                "vertical, display_name, avg_ticket_amount, avg_hours_saved_per_lead"
            )
            .order("vertical")
            .execute()
        )
        if result.data:
            return result.data
        logger.info("list_verticals: DB returned empty, using YAML fallback")
    except Exception:
        logger.exception("list_verticals: DB query failed, falling back to YAML")

    return _list_yaml_verticals()


def _load_yaml_preset(vertical: str) -> Optional[dict]:
    """YAML fallback — used when DB is unavailable or preset is missing.

    Args:
        vertical: Vertical slug to load.

    Returns:
        Dict matching the DB row shape, or None if not found in YAML.
    """
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not data or vertical not in data:
            return None
        entry = data[vertical]
        return {
            "vertical": vertical,
            "display_name": entry.get("display_name", vertical),
            "default_services": entry.get("default_services", []),
            "default_faqs": entry.get("default_faqs", []),
            "default_hours": entry.get("default_hours", {}),
            "avg_ticket_amount": entry.get("avg_ticket_amount"),
            "avg_hours_saved_per_lead": entry.get("avg_hours_saved_per_lead"),
        }
    except Exception:
        logger.exception(
            "_load_yaml_preset: failed to load YAML for vertical %r", vertical
        )
        return None


def _list_yaml_verticals() -> list[dict]:
    """List all verticals from YAML with display names and ticket amounts."""
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not data:
            return []
        return [
            {
                "vertical": slug,
                "display_name": entry.get("display_name", slug),
                "avg_ticket_amount": entry.get("avg_ticket_amount"),
                "avg_hours_saved_per_lead": entry.get("avg_hours_saved_per_lead"),
            }
            for slug, entry in data.items()
        ]
    except Exception:
        logger.exception("_list_yaml_verticals: failed to load YAML")
        return []
