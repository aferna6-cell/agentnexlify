"""Widget chat cache + DB config fetchers + origin check.

Extracted from widget_chat_helpers.py (god class split 2026-05-24).
Re-exported via widget_chat_helpers so existing imports continue to resolve.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not add
a future-annotations import here.
"""

import logging
import time as _time
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache TTL constants
# ---------------------------------------------------------------------------

_WIDGET_CACHE_TTL = 300  # 5 minutes for config data
_CHAT_CACHE_TTL = 300    # 5 minutes for FAQ/hours/corrections


# ---------------------------------------------------------------------------
# In-memory TTL cache — reduces DB load on hot widget endpoints
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}


def _get_cached(key: str, ttl: int = _WIDGET_CACHE_TTL) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        if _time.time() - ts < ttl:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    if len(_cache) > 1000:
        cutoff = _time.time() - _WIDGET_CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (_time.time(), data)


def _invalidate_cache(prefix: str) -> None:
    """Remove all cache entries matching a prefix."""
    to_del = [k for k in _cache if k.startswith(prefix)]
    for k in to_del:
        del _cache[k]


# ---------------------------------------------------------------------------
# DB helpers — widget config + tenant
# ---------------------------------------------------------------------------


def _get_widget_config(api_key: str) -> dict[str, Any]:
    cached = _get_cached(f"wc:{api_key}")
    if cached is not None:
        return cached
    try:
        db = get_service_supabase()
        result = db.table("widget_configs").select("*").eq("api_key", api_key).limit(1).execute()
    except Exception:
        logger.warning("Database unreachable in _get_widget_config", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    _set_cache(f"wc:{api_key}", result.data[0])
    return result.data[0]


def _get_tenant(tenant_id: str) -> dict[str, Any]:
    cached = _get_cached(f"t:{tenant_id}")
    if cached is not None:
        return cached
    try:
        db = get_service_supabase()
        result = db.table("tenants").select(
            "id, business_name, business_type, city, plan, plan_status, "
            "free_trial_started_at, conversations_used_this_month, "
            "sms_notifications_enabled, notification_phone, owner_email, "
            "ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit"
        ).eq("id", tenant_id).limit(1).execute()
    except Exception:
        logger.warning("Database unreachable in _get_tenant", exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    _set_cache(f"t:{tenant_id}", result.data[0])
    return result.data[0]


# ---------------------------------------------------------------------------
# Origin check
# ---------------------------------------------------------------------------

def _normalize_origin_host(value: str) -> str:
    value = (value or "").strip().lower().rstrip("/")
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"//{value}")
    return (parsed.netloc or parsed.path).strip().lower().rstrip("/")


def _check_origin(
    request: Request,
    allowed_domains: list[str] | None,
    *,
    require_origin: bool = False,
) -> None:
    if not allowed_domains:
        return
    origin = request.headers.get("origin", "")
    if not origin:
        if require_origin:
            raise HTTPException(status_code=403, detail="Origin required")
        return
    origin_host = _normalize_origin_host(origin)
    for domain in allowed_domains:
        domain_clean = _normalize_origin_host(domain)
        if origin_host == domain_clean:
            return
    raise HTTPException(status_code=403, detail="Origin not allowed")
