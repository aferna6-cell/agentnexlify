"""Web Push notification when an Agent OS deliverable awaits approval.

Free browser-push leg alongside the email + SMS legs in os_approval_notify.
Degrades to a clean no-op in two independent ways:
  - pywebpush not installed → module-level import guard, logged once
  - VAPID keys unset (pending manual Railway env step) → push_configured()
    returns False and send is skipped

Best-effort by design: a push failure must never break the chat turn.
Never log full endpoint URLs — they are capability URLs (truncate).
"""

import asyncio
import json
import logging
from urllib.parse import urlparse

from backend.config import settings

logger = logging.getLogger(__name__)

# SSRF guard: pywebpush POSTs to the stored endpoint URL server-side, so an
# attacker-controlled endpoint would let a tenant aim requests at internal
# services. Browsers only ever hand out endpoints on the major push services
# — restrict to exactly those (suffix match with a leading dot, plus exact).
ALLOWED_PUSH_HOSTS = (
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    ".notify.windows.com",
    "web.push.apple.com",
    ".push.apple.com",
)


def endpoint_host_allowed(endpoint: str) -> bool:
    """True when the endpoint is https on a known browser push service."""
    try:
        parsed = urlparse(endpoint)
        if parsed.scheme != "https":
            return False
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            return False
        for allowed in ALLOWED_PUSH_HOSTS:
            if allowed.startswith("."):
                if host.endswith(allowed) or host == allowed[1:]:
                    return True
            elif host == allowed:
                return True
        return False
    except Exception:
        return False

try:
    from pywebpush import webpush, WebPushException

    _PYWEBPUSH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via tests by patching
    webpush = None
    WebPushException = Exception
    _PYWEBPUSH_AVAILABLE = False
    logger.info("os_push_notify: pywebpush not installed — web push disabled")


def _truncate_endpoint(endpoint: str) -> str:
    """Endpoints are capability URLs — log only a recognizable prefix."""
    return str(endpoint)[:48] + "..."


def push_configured() -> bool:
    """True when pywebpush is importable AND all VAPID settings are set."""
    return bool(
        _PYWEBPUSH_AVAILABLE
        and settings.vapid_public_key
        and settings.vapid_private_key
        and settings.vapid_subject
    )


def _send_one(subscription: dict, payload: str) -> None:
    """Blocking pywebpush call — run via asyncio.to_thread.

    Re-checks the host allowlist at send time: rows written before the
    validator existed (or via any other path) must not become SSRF vectors.
    """
    if not endpoint_host_allowed(subscription["endpoint"]):
        raise ValueError("push endpoint host not in allowlist")
    webpush(
        subscription_info={
            "endpoint": subscription["endpoint"],
            "keys": subscription["keys"],
        },
        data=payload,
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject},
    )


async def send_pending_approval_push(db, tenant_id: str, *, title: str | None) -> int:
    """Push 'draft awaits approval' to every browser subscribed for the tenant.

    Returns the number of pushes delivered. No-ops (returns 0) when push is
    not configured. Expired subscriptions (404/410 from the push service)
    are deleted so they don't accumulate.
    """
    return await send_owner_push(
        db,
        tenant_id,
        title="Approval needed",
        body=(
            f"{title} is waiting for your approval."
            if title
            else "A draft from your AI staff is waiting for your approval."
        ),
        url_path="/dashboard/agent-os",
    )


async def send_owner_push(
    db, tenant_id: str, *, title: str, body: str, url_path: str
) -> int:
    """Push a notification to every browser subscribed for the tenant.

    Generic fan-out behind send_pending_approval_push, also used for
    escalation alerts. ``url_path`` is joined onto ``settings.frontend_url``
    and opened by the service worker's notificationclick handler.
    Same semantics: returns pushes delivered, 0 when unconfigured, prunes
    404/410-expired subscriptions.
    """
    if not push_configured():
        return 0

    try:
        result = (
            db.table("push_subscriptions")
            .select("endpoint, keys")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        subscriptions = result.data or []
        if not subscriptions:
            return 0

        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "url": f"{settings.frontend_url}{url_path}",
            }
        )

        sent = 0
        for sub in subscriptions:
            try:
                await asyncio.to_thread(_send_one, sub, payload)
                sent += 1
            except WebPushException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):
                    # Subscription expired or revoked — prune it.
                    try:
                        db.table("push_subscriptions").delete().eq(
                            "endpoint", sub["endpoint"]
                        ).execute()
                    except Exception:
                        logger.warning(
                            "os_push_notify: failed pruning expired sub %s",
                            _truncate_endpoint(sub["endpoint"]),
                            exc_info=True,
                        )
                else:
                    logger.warning(
                        "os_push_notify: push failed for tenant %s (endpoint %s, status %s)",
                        tenant_id,
                        _truncate_endpoint(sub["endpoint"]),
                        status,
                    )
            except Exception:
                logger.warning(
                    "os_push_notify: push failed for tenant %s (endpoint %s)",
                    tenant_id,
                    _truncate_endpoint(sub["endpoint"]),
                    exc_info=True,
                )

        if sent:
            logger.info(
                "os_push_notify: pushed to %s/%s subscriptions for tenant %s",
                sent,
                len(subscriptions),
                tenant_id,
            )
        return sent
    except Exception:
        logger.warning(
            "os_push_notify: failed for tenant %s — turn unaffected",
            tenant_id,
            exc_info=True,
        )
        return 0
