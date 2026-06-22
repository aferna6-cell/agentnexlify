"""Per-tenant rate limiting for /api/v1/widget/chat.

Keys by client_id extracted from the request body (api_key lookup deferred to
the route handler — here we use api_key as the limiter key since client_id is
not yet resolved at this layer).

Per-tier RPM defaults (overridable via env vars RATE_LIMIT_<TIER>_RPM):
    free:         30 rpm
    growth:       120 rpm
    autopilot:    240 rpm
    professional: 480 rpm
    enterprise:   1200 rpm

The limiter instance is imported from backend.limiter (already wired to the
FastAPI app in main.py). This module adds the tier-aware key extractor and
helper used by the widget_chat route decorator.
"""

import logging
import os

from starlette.requests import Request

logger = logging.getLogger(__name__)

# Per-tier RPM defaults, overridable via environment variables.
# Current paid plans (chatbot, agent_os — see backend/services/plan_catalog.py)
# MUST have entries here. Without them get_tier_limit() falls back to the free
# 30 rpm cap, silently throttling paying tenants on /api/v1/widget/chat
# (a $99.99 agent_os tenant would be capped like free). Keep in sync with
# plan_catalog.CURRENT_PAID_PLANS; test_rate_limit_current_plans guards it.
_TIER_DEFAULTS: dict[str, int] = {
    "free": 30,
    # Current sellable plans (repriced 2026-06-15)
    "chatbot": 120,      # AI Front Desk — widget/chat entry tier
    "agent_os": 480,     # AI Workforce — full platform
    # Legacy / grandfathered
    "growth": 120,
    "autopilot": 240,
    "professional": 480,
    "enterprise": 1200,
}


def _env_rpm(tier: str, default: int) -> int:
    """Read RATE_LIMIT_<TIER>_RPM from environment, fallback to default."""
    env_key = f"RATE_LIMIT_{tier.upper()}_RPM"
    raw = os.environ.get(env_key, "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return default


def get_tier_limit(plan: str) -> str:
    """Return a slowapi limit string like '120/minute' for the given plan.

    Falls back to free-tier if plan is unknown.
    """
    tier = plan.lower() if plan else "free"
    default_rpm = _TIER_DEFAULTS.get(tier, _TIER_DEFAULTS["free"])
    rpm = _env_rpm(tier, default_rpm)
    return f"{rpm}/minute"


def get_client_id_key(request: Request) -> str:
    """Extract the api_key from the JSON body to use as the rate-limit key.

    slowapi calls this synchronously before the route handler runs, so we
    read the body via request.state if it was stashed, or fall back to the
    client IP.  The widget_chat handler reads body via Pydantic — the api_key
    is available in the parsed body after Pydantic validation, but the key
    extractor runs before that.

    Strategy: use the raw JSON api_key field if present (fast path), else
    fall back to client IP (same as default limiter behavior).
    """
    # Try to pull api_key from query params (not typical for POST, but safe)
    api_key = request.query_params.get("api_key", "")
    if api_key:
        return api_key

    # Attempt to read cached body bytes stashed by a middleware or prior read
    body_bytes: bytes = b""
    if hasattr(request.state, "_body"):
        body_bytes = request.state._body
    elif hasattr(request, "_body"):
        body_bytes = request._body  # type: ignore[attr-defined]

    if body_bytes:
        try:
            import json
            data = json.loads(body_bytes)
            key = data.get("api_key", "")
            if key:
                return str(key)
        except Exception:
            pass

    # Fallback: client IP. Prefer request.client.host (set by Railway/Vercel
    # edge after TLS termination) over X-Forwarded-For, since XFF is
    # client-controlled. If we must use XFF, take the RIGHT-most entry — the IP
    # the trusted edge proxy appends — not the left-most, which the client can
    # spoof to rotate rate-limit identities. Matches backend/limiter.py.
    if request.client and request.client.host:
        return request.client.host
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    return "127.0.0.1"
