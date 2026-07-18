"""DB-backed operational flags with env fallback (migration 175).

Several launch-gating flags could only be flipped from the Railway
dashboard: ``REFERRAL_REWARD_ENABLED`` sat unset for 27 days (GH #413)
because activation required an env-var change no automation could make,
and the PR #471 retrieval flags (``widget_kb_rerank_enabled`` /
``widget_kb_hybrid_enabled``) shipped as config.py env settings with the
same problem. This module gives every such flag a ``platform_settings``
row override:

    flag_value("widget_kb_rerank_enabled")  ->  "1" | None

Resolution order at the call site stays explicit: DB row wins when
present, otherwise the caller uses its existing env/config fallback.
Reads are cached for 60s per process (the table is tiny and flags are
not latency-sensitive), and every failure path returns None so a broken
DB can never take down a request path that only wanted a flag.

Under TESTING the DB is never touched - unit tests exercise config/env
behavior exactly as before unless they patch this module explicitly.
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, str | None]] = {}


def _testing() -> bool:
    return os.environ.get("TESTING", "").strip() == "1"


def clear_cache() -> None:
    _cache.clear()


def flag_value(key: str) -> str | None:
    """Return the platform_settings override for *key*, or None.

    None means "no override - use your env/config fallback". Cached 60s.
    """
    if _testing():
        return None

    cached = _cache.get(key)
    now = time.time()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    value: str | None = None
    try:
        from backend.models.database import get_service_supabase

        result = (
            get_service_supabase()
            .table("platform_settings")
            .select("value")
            .eq("key", key)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows:
            value = rows[0].get("value")
    except Exception:
        logger.warning("platform_flags: lookup failed for %s - using env fallback", key)
        value = None

    _cache[key] = (now, value)
    return value


def flag_enabled(key: str, env_default: bool = False) -> bool:
    """Truthy check: DB override wins, else *env_default*.

    Truthy values: 1/true/yes/on (case-insensitive).
    """
    raw = flag_value(key)
    if raw is None:
        return env_default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def flag_int(key: str, env_default: int) -> int:
    """Integer flag: DB override wins when parseable, else *env_default*."""
    raw = flag_value(key)
    if raw is None:
        return env_default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return env_default
