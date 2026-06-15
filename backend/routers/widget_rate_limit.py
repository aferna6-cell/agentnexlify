"""Dynamic per-tenant rate-limit resolver for the widget chat endpoint.

Extracted from widget_chat.py — single concern: plan-tier → rate-limit string.
"""

import logging

from backend.middleware.rate_limit import get_tier_limit

logger = logging.getLogger(__name__)


def _chat_rate_limit(key: str) -> str:
    """Dynamic per-tenant rate limit based on plan tier.

    slowapi calls this with the result of key_function (the api_key string)
    when the limit provider's signature includes a `key` parameter
    (slowapi/wrappers.py:86-92). Looks up tenant plan via api_key, falls
    back to free-tier (30/minute) if the plan cannot be resolved.
    """
    try:
        from backend.routers.widget_chat_helpers import _get_widget_config, _get_tenant

        widget = _get_widget_config(key)
        tenant = _get_tenant(widget["tenant_id"])
        plan = tenant.get("plan", "free") or "free"
    except Exception as exc:
        logger.warning(
            "_chat_rate_limit fallback to free tier for key=%s: %s", key, exc
        )
        plan = "free"
    return get_tier_limit(plan)
