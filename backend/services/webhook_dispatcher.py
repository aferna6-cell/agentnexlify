"""Webhook dispatcher — delivers event payloads to registered webhook URLs."""

import asyncio

from backend.services.task_utils import safe_create_task
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.models.database import get_service_supabase
from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = {
    "lead.created",
    "lead.updated",
    "lead.status_changed",
    "appointment.booked",
    "appointment.cancelled",
    "conversation.started",
    "conversation.message",
    "automation.email_sent",
    "automation.sms_sent",
    "order.created",
    "call.completed",
    "invoice.created",
    "invoice.paid",
    "form.submitted",
    "review.received",
}

_TIMEOUT = 10.0
_MAX_RETRIES = 3
_RETRY_DELAYS = [5, 15, 60]  # Exponential backoff: 5s, 15s, 60s
_MAX_FAILURES = 10
_DAILY_LIMIT = 1000

# In-memory daily delivery tracking per tenant (reset at midnight UTC)
_daily_deliveries: dict[str, int] = {}
_last_reset_date: str = ""


def _check_daily_limit(tenant_id: str) -> bool:
    global _last_reset_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != _last_reset_date:
        _daily_deliveries.clear()
        _last_reset_date = today
    return _daily_deliveries.get(tenant_id, 0) < _DAILY_LIMIT


def _increment_daily(tenant_id: str) -> None:
    _daily_deliveries[tenant_id] = _daily_deliveries.get(tenant_id, 0) + 1


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def fire_event(
    tenant_id: str,
    event: str,
    data: dict[str, Any],
) -> None:
    """Fire a webhook event for a tenant. Finds matching webhooks and delivers."""
    if event not in SUPPORTED_EVENTS:
        logger.warning("Unknown webhook event: %s", event)
        return

    # Live-demo sandbox: never POST demo data to visitor-configured URLs.
    from backend.services.demo_guard import is_demo_tenant

    if is_demo_tenant(tenant_id):
        logger.info("demo tenant %s: webhook event %s suppressed (demo no-op)", tenant_id, event)
        return

    if not _check_daily_limit(tenant_id):
        logger.warning("Webhook daily limit reached for tenant %s", tenant_id)
        return

    db = get_service_supabase()
    try:
        result = (
            db.table("webhooks")
            .select("id, url, events, secret")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to query webhooks for tenant %s", tenant_id)
        return

    webhooks = [w for w in (result.data or []) if event in (w.get("events") or [])]
    if not webhooks:
        return

    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    for webhook in webhooks:
        if not _check_daily_limit(tenant_id):
            break
        safe_create_task(_deliver(tenant_id, webhook, payload), name="webhook_deliver")


async def _deliver(
    tenant_id: str,
    webhook: dict,
    payload: dict,
    attempt: int = 0,
) -> None:
    """POST payload to a single webhook URL. Log result. Retry up to 3 times with exponential backoff."""
    webhook_id = webhook["id"]
    url = webhook["url"]
    payload_bytes = json.dumps(payload, default=str).encode()

    headers = {"Content-Type": "application/json"}
    if webhook.get("secret"):
        headers["X-Webhook-Signature"] = _sign_payload(payload_bytes, webhook["secret"])

    db = get_service_supabase()
    success = False
    status_code = None
    response_body = ""

    if not is_safe_url(url):
        logger.warning(
            "webhook_dispatcher: blocked unsafe URL for tenant=%s webhook=%s",
            tenant_id, webhook_id,
        )
        try:
            db.table("webhook_logs").insert({
                "webhook_id": webhook_id,
                "event": payload.get("event", ""),
                "payload": payload,
                "response_status": None,
                "response_body": "Refused: URL resolves to a private, loopback, or reserved IP",
                "success": False,
            }).execute()
        except Exception:
            logger.exception("Failed to log blocked webhook delivery for %s", webhook_id)
        return

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, content=payload_bytes, headers=headers)
            status_code = resp.status_code
            response_body = resp.text[:2000]
            success = 200 <= resp.status_code < 300
    except httpx.TimeoutException:
        response_body = "Timeout after 10 seconds"
    except Exception as e:
        response_body = str(e)[:2000]

    _increment_daily(tenant_id)

    # Log delivery
    try:
        db.table("webhook_logs").insert({
            "webhook_id": webhook_id,
            "event": payload.get("event", ""),
            "payload": payload,
            "response_status": status_code,
            "response_body": response_body,
            "success": success,
        }).execute()
    except Exception:
        logger.exception("Failed to log webhook delivery for %s", webhook_id)

    if success:
        # Reset failure count and update last_triggered_at
        try:
            db.table("webhooks").update({
                "failure_count": 0,
                "last_triggered_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", webhook_id).execute()
        except Exception:
            logger.warning("Failed to reset failure count for webhook %s", webhook_id, exc_info=True)
    else:
        # Increment failure count
        try:
            current = (
                db.table("webhooks")
                .select("failure_count")
                .eq("id", webhook_id)
                .limit(1)
                .execute()
            )
            count = (current.data[0]["failure_count"] or 0) + 1 if current.data else 1
            updates: dict[str, Any] = {"failure_count": count}
            if count >= _MAX_FAILURES:
                updates["is_active"] = False
                logger.warning(
                    "Webhook %s auto-disabled after %d consecutive failures",
                    webhook_id, count,
                )
            db.table("webhooks").update(updates).eq("id", webhook_id).execute()
        except Exception:
            logger.exception("Failed to update failure count for webhook %s", webhook_id)

        # Retry with exponential backoff
        if attempt < _MAX_RETRIES:
            delay = _RETRY_DELAYS[attempt] if attempt < len(_RETRY_DELAYS) else _RETRY_DELAYS[-1]
            logger.info(
                "Webhook %s delivery failed (attempt %d/%d), retrying in %ds",
                webhook_id, attempt + 1, _MAX_RETRIES, delay,
            )
            await asyncio.sleep(delay)
            await _deliver(tenant_id, webhook, payload, attempt=attempt + 1)


def fire_event_background(tenant_id: str, event: str, data: dict[str, Any]) -> None:
    """Fire webhook event from a sync context by scheduling on the running event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(fire_event(tenant_id, event, data))
    except RuntimeError:
        logger.debug("No running event loop, skipping webhook fire for %s", event)
