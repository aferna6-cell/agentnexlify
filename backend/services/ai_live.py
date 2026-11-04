"""Live Anthropic status.

``ai_live`` is true only after GET /v1/models succeeds. That list call spends
no completion tokens. It is cached for a few minutes. /health and /readyz never
start a completion. Reason codes are for admin callers and never include keys.
"""

import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request

from backend.config import settings

logger = logging.getLogger(__name__)

# A few minutes. /health and /readyz must not call the model more often.
AI_LIVE_TTL_S = 180.0
_MODELS_URL = "https://api.anthropic.com/v1/models?limit=1"

_lock = threading.Lock()
_cache: dict | None = None
_cache_at = 0.0

_REASON_RE = re.compile(r"^[a-z0-9_]{1,40}$")
# Split so the source does not contain a contiguous provider-key prefix.
_ANTHROPIC_KEY_PREFIX = "sk-" + "ant-"
_SECRET_RE = re.compile(
    re.escape(_ANTHROPIC_KEY_PREFIX)
    + r"[A-Za-z0-9_\-]+|(?:x-api-key|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def normalize_api_key(raw: str | None) -> str:
    """Trim whitespace and one pair of wrapping quotes. Never log the result."""
    key = (raw or "").strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        key = key[1:-1].strip()
    return key


def sanitize_provider_reason(status: int | None, detail: str = "") -> str:
    """Map a provider failure to a stable code. The raw detail is not returned."""
    text = _SECRET_RE.sub("", detail or "").lower()
    if status == 401 or "invalid x-api-key" in text or "authentication_error" in text:
        return "invalid_api_key"
    if status == 403 or "permission_error" in text:
        return "permission_denied"
    if status == 404 or "not_found_error" in text or ("model" in text and "not found" in text):
        return "invalid_model"
    if status == 429 or "rate_limit" in text:
        return "rate_limited"
    if status in (408, 504) or "timeout" in text or "timed out" in text:
        return "timeout"
    if status in (529, 503) or "overloaded" in text:
        return "overloaded"
    if status is None and not text.strip():
        return "provider_unreachable"
    return "provider_error"


def sanitize_exception(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = getattr(exc, "status", None)
    if not isinstance(status, int):
        status = None
    detail = f"{type(exc).__name__} {exc}"
    return sanitize_provider_reason(status, detail[:500])


def _safe_reason(reason: str, *, ok: bool) -> str:
    if ok:
        return "ok"
    if _REASON_RE.fullmatch(reason or ""):
        return reason
    return "provider_error"


def probe_models_list(api_key: str, *, opener=None, timeout: float = 4.0) -> tuple[bool, str]:
    """GET /v1/models. A non-empty key is not success until Anthropic accepts it."""
    key = normalize_api_key(api_key)
    if not key:
        return False, "no_api_key"
    open_url = opener or urllib.request.urlopen
    req = urllib.request.Request(
        _MODELS_URL,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="GET",
    )
    try:
        with open_url(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", None) or getattr(resp, "code", 200))
            if 200 <= status < 300:
                return True, "ok"
            return False, sanitize_provider_reason(status, "")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body = ""
        reason = sanitize_provider_reason(getattr(exc, "code", None), body)
        logger.warning("ai_live models probe failed reason=%s status=%s", reason, getattr(exc, "code", None))
        return False, reason
    except Exception as exc:
        logger.warning(
            "ai_live models probe failed reason=provider_unreachable error_type=%s",
            type(exc).__name__,
        )
        return False, "provider_unreachable"


def _read_json(opener, url: str, headers: dict | None, timeout: float) -> tuple[int, dict | None]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")[:2000]
            status = int(getattr(resp, "status", None) or getattr(resp, "code", 200))
    except urllib.error.HTTPError as exc:
        return int(getattr(exc, "code", 0) or 0), None
    except Exception:
        return 0, None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return status, None
    return status, payload if isinstance(payload, dict) else None


def fetch_agent_service_status(
    base_url: str,
    *,
    opener=None,
    token: str = "",
    timeout: float = 3.0,
) -> tuple[bool, str]:
    """Boolean from public /health. Reason from token-gated /ai-live when we can."""
    open_url = opener or urllib.request.urlopen
    root = base_url.rstrip("/")
    _status, health = _read_json(open_url, root + "/health", None, timeout)
    if not health or "ai_live" not in health:
        logger.warning("ai_live agent-service health missing ai_live")
        return False, "agent_service_status_unknown"
    ok = bool(health.get("ai_live"))
    if not token:
        return ok, "ok" if ok else "reason_unavailable"
    headers = {"X-Agent-Token": token}
    code, detail = _read_json(open_url, root + "/ai-live", headers, timeout)
    if code == 200 and isinstance(detail, dict) and "ai_live_reason" in detail:
        reason = _safe_reason(str(detail.get("ai_live_reason") or ""), ok=bool(detail.get("ai_live")))
        return bool(detail.get("ai_live")), reason
    return ok, "ok" if ok else "reason_unavailable"


def read_ai_live_cache() -> dict:
    """Copy the last probe. Never starts I/O and never waits on a refresh."""
    with _lock:
        if _cache is None:
            return {"ai_live": False, "ai_live_reason": "probe_pending"}
        return dict(_cache)


def refresh_ai_live_cache(*, force: bool = False, _deps: dict | None = None) -> dict:
    """Probe off the request path. The lock is not held during network I/O.

    /health and /readyz must call read_ai_live_cache instead. A hung probe
    must not delay them or fail Railway's healthcheck.
    """
    global _cache, _cache_at
    now = time.monotonic()
    with _lock:
        if not force and _cache is not None and now - _cache_at < AI_LIVE_TTL_S:
            return dict(_cache)

    if os.environ.get("TESTING") == "1" and _deps is None:
        measured = {"ai_live": False, "ai_live_reason": "probe_skipped"}
    else:
        measured = _measure(_deps)
    ok = bool(measured.get("ai_live"))
    result = {
        "ai_live": ok,
        "ai_live_reason": _safe_reason(str(measured.get("ai_live_reason") or ""), ok=ok),
    }
    if not result["ai_live"]:
        logger.warning("ai_live not ok reason=%s", result["ai_live_reason"])
    with _lock:
        _cache = result
        _cache_at = time.monotonic()
        return dict(result)


def current_ai_live(*, force: bool = False, _deps: dict | None = None) -> dict:
    """Synchronous refresh used by the background worker and unit tests.

    Request handlers must not call this. Use read_ai_live_cache.
    """
    return refresh_ai_live_cache(force=force, _deps=_deps)


def _measure(deps: dict | None) -> dict:
    deps = deps or {}
    service_url = deps.get("service_url", os.environ.get("AGENT_SERVICE_URL", "").strip())
    if service_url:
        fetch_service = deps.get("fetch_service", fetch_agent_service_status)
        token = deps.get("token", os.environ.get("AGENT_SERVICE_TOKEN", ""))
        ok, reason = fetch_service(service_url, token=token)
        return {"ai_live": ok, "ai_live_reason": reason}
    probe = deps.get("probe", probe_models_list)
    api_key = normalize_api_key(deps.get("api_key", settings.anthropic_api_key))
    ok, reason = probe(api_key)
    return {"ai_live": ok, "ai_live_reason": reason}


def reset_ai_live_cache() -> None:
    global _cache, _cache_at
    with _lock:
        _cache = None
        _cache_at = 0.0
