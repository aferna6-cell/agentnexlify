"""Vertical preset loader for new-tenant activation.

Loads config/vertical_presets.yaml and returns structured preset dicts.
Falls back to the ``generic`` preset for unknown verticals.
Returns the ``generic`` preset (not raises) when the YAML file is missing.

Public API:
    load_vertical_preset(vertical: str) -> dict
    list_verticals() -> list[str]
"""

import logging
import pathlib
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = pathlib.Path(__file__).parent.parent.parent / "config" / "vertical_presets.yaml"

# Module-level cache so the file is only parsed once per process.
_cache: dict[str, Any] | None = None


def _load_yaml() -> dict[str, Any]:
    """Load and cache the presets YAML.  Returns empty dict on missing file."""
    global _cache
    if _cache is not None:
        return _cache

    if not _CONFIG_PATH.exists():
        logger.warning(
            "vertical_presets.yaml not found at %s; using empty preset map",
            _CONFIG_PATH,
        )
        _cache = {}
        return _cache

    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        logger.exception("Failed to parse %s; using empty preset map", _CONFIG_PATH)
        data = {}

    if not isinstance(data, dict):
        logger.error(
            "vertical_presets.yaml root is not a mapping (got %s); using empty preset map",
            type(data).__name__,
        )
        data = {}

    _cache = data
    return _cache


def _normalize(vertical: str) -> str:
    """Lowercase and underscore-normalize a vertical name."""
    return vertical.strip().lower().replace("-", "_").replace(" ", "_")


def load_vertical_preset(vertical: str) -> dict:
    """Return the preset dict for *vertical*.

    Falls back to the ``generic`` preset when the requested vertical is not
    found.  Returns the ``generic`` preset (not raises) when the YAML file
    is missing entirely.

    Args:
        vertical: The business vertical key, e.g. ``"salon_spa"``,
            ``"plumber_hvac"``, ``"dental"``.  Case-insensitive; hyphens and
            spaces are normalised to underscores.

    Returns:
        A dict with keys ``greeting``, ``services``, ``business_hours``,
        and ``faqs``.  The ``faqs`` value is a list of dicts with
        ``question`` and ``answer`` keys.
    """
    data = _load_yaml()
    key = _normalize(vertical)
    preset = data.get(key)
    if preset is None:
        logger.info(
            "load_vertical_preset: no preset for %r, falling back to generic", vertical
        )
        preset = data.get("generic", {})
    return preset


def list_verticals() -> list[str]:
    """Return the sorted list of available vertical keys (excluding ``generic``).

    The ``generic`` fallback is intentionally excluded because it is not a
    real vertical -- it applies to any tenant that does not match a named key.
    """
    data = _load_yaml()
    return sorted(k for k in data if k != "generic")
