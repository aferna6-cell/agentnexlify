"""Shared plumbing for best-effort notification modules.

``lead_alerts``, ``booking_alerts``, and ``appointment_customer_notify`` grew
as three copies of the same skeleton: a per-worker idempotency set, a tenants
config read that degrades to {}, per-channel send wrappers that swallow every
failure, and an email/SMS dispatch branch with skip logging. This module is
that skeleton, written once.

Design contract (inherited by every caller):
  - Best-effort and non-blocking - nothing here ever raises into a request
    cycle or background task.
  - Demo-safe - the ``send_email`` / ``send_sms`` wrappers already no-op for
    demo tenants; ``tenant_id`` is always passed through.
  - Patch-friendly - the channel senders are imported lazily inside the
    helpers, so tests keep patching ``backend.services.email_sender.send_email``
    and ``backend.services.twilio_service.send_sms`` at the source.

WARNING: imported by modules that FastAPI routers import - do NOT add
``from __future__ import annotations`` here.
"""

import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class IdempotencyGuard:
    """Per-worker at-most-once guard keyed by an arbitrary tuple.

    Production runs 4 Uvicorn workers, so this dedupes within a worker; the
    realistic double-send risk (multiple capture paths handling one request)
    is in-process, which this covers. Intentionally a soft cap, not a
    cross-process lock: at worst another worker sends one duplicate, which is
    far better than blocking the request on a distributed lock.
    """

    def __init__(self, max_tracked: int = 10_000):
        self._seen: set = set()
        self._max_tracked = max_tracked

    def seen(self, *key_parts: str) -> bool:
        """True when this key was already recorded this process.

        Records the key on first call so concurrent duplicate paths
        short-circuit. Any empty key part means "not deduped" - a real
        notification is never silently swallowed for lack of an id.
        """
        if not all(key_parts):
            return False
        key = tuple(key_parts)
        if key in self._seen:
            return True
        if len(self._seen) >= self._max_tracked:
            self._seen.clear()
        self._seen.add(key)
        return False

    def reset(self) -> None:
        """Test helper - drop all tracked keys."""
        self._seen.clear()


def fetch_owner_alert_config(get_db: Callable, tenant_id: str, log_prefix: str) -> dict:
    """Owner notification config off the tenants table; {} on any failure.

    ``get_db`` is passed by the caller (not imported here) so each module's
    ``get_service_supabase`` stays patchable in its own namespace.
    """
    try:
        result = (
            get_db()
            .table("tenants")
            .select(
                "business_name, owner_email, notification_phone, "
                "sms_notifications_enabled"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "%s: tenant config lookup failed for %s", log_prefix, tenant_id,
            exc_info=True,
        )
        return {}
    rows = result.data or []
    return rows[0] if rows else {}


async def safe_send_email(
    *, tenant_id: str, to: str, subject: str, body_html: str, log_prefix: str
) -> None:
    """Send an email, swallowing every failure. Demo-safe via tenant_id."""
    from backend.services.email_sender import send_email

    try:
        await send_email(to=to, subject=subject, body_html=body_html, tenant_id=tenant_id)
    except Exception:
        logger.error(
            "%s: email send FAILED tenant=%s", log_prefix, tenant_id, exc_info=True
        )


async def safe_send_sms(*, tenant_id: str, to: str, body: str, log_prefix: str) -> None:
    """Send an SMS, swallowing every failure. Demo-safe via tenant_id."""
    from backend.services.twilio_service import send_sms

    try:
        await send_sms(to=to, body=body, tenant_id=tenant_id)
    except Exception:
        logger.error(
            "%s: SMS send FAILED tenant=%s", log_prefix, tenant_id, exc_info=True
        )


async def dispatch_owner_alert(
    *,
    tenant_id: str,
    config: dict,
    email_fn: Callable[[str, str], Awaitable[None]],
    sms_fn: Callable[[str, str], Awaitable[None]],
    log_prefix: str,
) -> None:
    """Run the standard owner email/SMS channel branch with skip logging.

    ``email_fn(business_name, owner_email)`` fires when the tenant has an
    owner_email; ``sms_fn(business_name, phone)`` fires when SMS alerts are
    enabled AND a notification phone is set. Callers bind everything else
    (lead/booking payloads) into the callables.
    """
    business_name = config.get("business_name") or "your business"
    owner_email = config.get("owner_email")
    phone = config.get("notification_phone")
    sms_enabled = config.get("sms_notifications_enabled")

    if owner_email:
        await email_fn(business_name, owner_email)
    else:
        logger.info(
            "%s: no owner_email for tenant=%s, email skipped", log_prefix, tenant_id
        )

    if sms_enabled and phone:
        await sms_fn(business_name, phone)
    else:
        logger.info(
            "%s: SMS skipped tenant=%s (sms_enabled=%s phone_set=%s)",
            log_prefix, tenant_id, bool(sms_enabled), bool(phone),
        )
