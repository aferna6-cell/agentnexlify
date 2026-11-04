"""Live Anthropic status for /readyz.

Reasons are short codes. Provider bodies, request ids, and API keys are never
returned or logged.
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

from backend.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 60.0
_cache: dict | None = None
_cache_at = 0.0

_REASON_RE = re.compile(r"^[a-z0-9_]{1,40}$")
_SECRET_RE = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]+|(?:x-api-key|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+",
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


def probe_anthropic_key(api_key: str, *, opener=None, timeout: float = 4.0) -> tuple[bool, str]:
    """GET /v1/models with the key. 401 is invalid_api_key; the key is not logged."""
    key = normalize_api_key(api_key)
    if not key:
        return False, "no_api_key"
    open_url = opener or urllib.request.urlopen
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=1",
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
        logger.warning("ai_live anthropic probe failed reason=%s status=%s", reason, getattr(exc, "code", None))
        return False, reason
    except Exception as exc:
        logger.warning(
            "ai_live anthropic probe failed reason=provider_unreachable error_type=%s",
            type(exc).__name__,
        )
        return False, "provider_unreachable"


def probe_agent_service(base_url: str, *, opener=None, timeout: float = 3.0) -> tuple[bool | None, str]:
    """Read agent-service /health. None means the process did not report ai_live_ok."""
    url = base_url.rstrip("/") + "/health"
    open_url = opener or urllib.request.urlopen
    req = urllib.request.Request(url, method="GET")
    try:
        with open_url(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")[:2000]
    except Exception as exc:
        logger.warning(
            "ai_live agent-service probe failed reason=agent_service_unreachable error_type=%s",
            type(exc).__name__,
        )
        return False, "agent_service_unreachable"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, "agent_service_status_unknown"
    if not isinstance(payload, dict) or "ai_live_ok" not in payload:
        return None, "agent_service_status_unknown"
    ok = bool(payload.get("ai_live_ok"))
    reason = _safe_reason(str(payload.get("ai_live_reason") or ""), ok=ok)
    if not ok and reason == "ok":
        reason = "provider_error"
    return ok, reason


def latest_model_call_status(db=None) -> tuple[bool | None, str]:
    """Newest non-local os_model_call_log row. None when the log cannot be read."""
    try:
        if db is None:
            from backend.models.database import get_service_supabase

            db = get_service_supabase()
        result = (
            db.table("os_model_call_log")
            .select("ok,error,model")
            .order("created_at", desc=True)
            .limit(8)
            .execute()
        )
    except Exception as exc:
        logger.warning("ai_live model log lookup failed error_type=%s", type(exc).__name__)
        return None, "provider_status_unknown"
    rows = getattr(result, "data", None) or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("model") == "local-composer":
            continue
        if row.get("ok"):
            return True, "ok"
        return False, sanitize_provider_reason(None, str(row.get("error") or ""))
    return None, "no_recent_call"


def current_ai_live(*, force: bool = False, _deps: dict | None = None) -> dict:
    """Workforce AI liveness. Cached. TESTING skips the network unless _deps is passed."""
    global _cache, _cache_at
    now = time.monotonic()
    if not force and _deps is None and _cache is not None and now - _cache_at < _CACHE_TTL_S:
        return dict(_cache)

    if os.environ.get("TESTING") == "1" and _deps is None:
        configured = bool(normalize_api_key(settings.anthropic_api_key))
        result = {
            "ai_live_ok": configured,
            "ai_live_reason": "ok" if configured else "no_api_key",
            "ai_live_scope": "backend",
        }
        _cache = result
        _cache_at = now
        return dict(result)

    deps = _deps or {}
    probe_key = deps.get("probe_key", probe_anthropic_key)
    probe_service = deps.get("probe_service", probe_agent_service)
    model_log = deps.get("model_log", latest_model_call_status)
    api_key = deps.get("api_key", settings.anthropic_api_key)
    service_url = deps.get(
        "service_url", os.environ.get("AGENT_SERVICE_URL", "").strip()
    )

    backend_ok, backend_reason = probe_key(api_key)
    ok, reason, scope = backend_ok, backend_reason, "backend"

    if service_url:
        svc_ok, svc_reason = probe_service(service_url)
        if svc_ok is not None:
            ok, reason, scope = bool(svc_ok), svc_reason, "agent_service"
        else:
            log_ok, log_reason = model_log()
            if log_ok is not None:
                ok, reason, scope = bool(log_ok), log_reason, "model_log"
            elif not backend_ok:
                ok, reason, scope = False, backend_reason, "backend"
            else:
                ok, reason, scope = False, "agent_service_status_unknown", "agent_service"
    else:
        log_ok, log_reason = model_log()
        if log_ok is False:
            ok, reason, scope = False, log_reason, "model_log"

    reason = _safe_reason(reason, ok=ok)
    if not ok:
        logger.warning("ai_live not ok scope=%s reason=%s", scope, reason)
    result = {"ai_live_ok": ok, "ai_live_reason": reason, "ai_live_scope": scope}
    if _deps is None:
        _cache = result
        _cache_at = now
    return dict(result)


def reset_ai_live_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = 0.0
