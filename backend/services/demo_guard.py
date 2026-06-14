"""Demo-tenant outbound guard for the public live-demo sandbox.

Demo tenants (``tenants.is_demo = true``) are fully clickable — visitors can
approve drafts, trigger sends, edit anything — but nothing may actually leave
the system or cost money. The two outbound chokepoints (``email_sender.
send_email`` and ``os_action_dispatch.queue_action_for_run``) call
``is_demo_tenant`` and no-op with a success-shaped result so the UI flows
look real.

Lookups are cached per-worker for 5 minutes (same TTL convention as the
widget config cache); a DB error fails OPEN as "not demo" — a blip must
never silence real tenants' outbound mail.
"""

import logging
import time

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_TTL_SECONDS = 300
_cache: dict[str, tuple[bool, float]] = {}


def is_demo_tenant(tenant_id: str | None) -> bool:
    """True when this tenant is the live-demo sandbox. Cached 5 min."""
    if not tenant_id:
        return False
    hit = _cache.get(tenant_id)
    now = time.monotonic()
    if hit and now - hit[1] < _TTL_SECONDS:
        return hit[0]
    try:
        result = (
            get_service_supabase()
            .table("tenants")
            .select("is_demo")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        # Strict identity check: only an explicit JSON true marks a demo
        # tenant. This also keeps mocked DB clients (MagicMock results in
        # tests) from reading as truthy and silencing real outbound sends.
        rows = result.data
        value = (
            isinstance(rows, list)
            and len(rows) > 0
            and rows[0].get("is_demo") is True
        )
    except Exception:
        logger.warning("demo_guard lookup failed for %s — treating as not demo", tenant_id, exc_info=True)
        return False
    _cache[tenant_id] = (value, now)
    return value


def clear_cache() -> None:
    """Test helper — drop all cached lookups."""
    _cache.clear()
