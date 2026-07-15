"""Instant owner alerts when a new lead is captured.

The moment the widget captures a lead, the business owner gets notified
instantly via BOTH channels they have configured:

  - Email (Resend) when ``tenants.owner_email`` is set.
  - SMS (Twilio) when ``tenants.notification_phone`` is set AND
    ``tenants.sms_notifications_enabled`` is true.

This is the #1 ROI story for an AI front desk: an SMB never misses a
fresh lead.

Design contract:

  - Best-effort and non-blocking. A notification failure NEVER blocks
    lead capture or the widget response. Every channel runs in its own
    try/except; this module's public entry point never raises.
  - Idempotent. The same lead is alerted at most once per worker process.
    The widget has two capture paths (manual ``POST /lead`` and the
    conversation-scan ``_capture_leads_from_session``) plus a per-message
    enrichment retry, so without a guard a single lead could fire the
    owner alert two or three times.
  - Demo-safe. The Twilio and Resend wrappers already no-op for demo
    tenants (``tenants.is_demo = true``); we pass ``tenant_id`` to
    ``send_sms`` so the SMS path gets the same suppression the email
    path already has.

Multi-tenant invariant: the leads table uses ``client_id`` (NOT
tenant_id), but the per-tenant config we read here lives on the
``tenants`` table keyed by ``id``. See docs/dev-knowledge/schema-log.md.

WARNING: this module is imported by FastAPI routers. Do NOT add
``from __future__ import annotations`` here.
"""

import asyncio
import html as html_mod
import logging

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Per-worker idempotency guard. Keyed by (tenant_id, lead_id). Production
# runs 4 Uvicorn workers, so this dedupes within a worker; the realistic
# double-send risk (two capture paths + an enrichment retry handling the
# same request) is in-process, which this covers. It is intentionally a
# soft cap, not a hard cross-process lock: at worst a second worker could
# send one duplicate, which is far better than blocking lead capture on a
# distributed lock.
_alerted: set = set()
# Bound the set so a long-lived worker cannot grow it without limit.
_MAX_TRACKED = 10_000


def _already_alerted(tenant_id: str, lead_id: str) -> bool:
    """Return True if this (tenant, lead) was already alerted this process.

    Marks the pair as alerted on first call so concurrent/duplicate capture
    paths short-circuit. Missing identifiers are treated as not-alerted so
    we never silently swallow a real alert.
    """
    if not tenant_id or not lead_id:
        return False
    key = (tenant_id, lead_id)
    if key in _alerted:
        return True
    if len(_alerted) >= _MAX_TRACKED:
        _alerted.clear()
    _alerted.add(key)
    return False


def reset_idempotency_cache() -> None:
    """Test helper — drop all tracked (tenant, lead) pairs."""
    _alerted.clear()


def _fetch_tenant_alert_config(tenant_id: str) -> dict:
    """Read the owner notification config off the tenants table.

    Returns an empty dict on any failure so callers degrade to "no
    channels configured" rather than raising into the request cycle.
    """
    try:
        result = (
            get_service_supabase()
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
            "lead_alert: tenant config lookup failed for %s", tenant_id, exc_info=True
        )
        return {}
    rows = result.data or []
    return rows[0] if rows else {}


def _build_email_html(
    business_name: str,
    lead_name: str,
    lead_info: dict,
    source_label: str = "your chat widget",
) -> str:
    """Build the owner-alert email body. All interpolated values escaped."""
    safe_business = html_mod.escape(business_name)
    safe_name = html_mod.escape(lead_name)
    safe_email = html_mod.escape(lead_info.get("email") or "not provided")
    safe_phone = html_mod.escape(lead_info.get("phone") or "not provided")
    safe_source = html_mod.escape(source_label or "your chat widget")
    return (
        f"<h2>New lead for {safe_business}</h2>"
        f"<p>A new lead was just captured from {safe_source}:</p>"
        f"<table style='border-collapse:collapse;margin:16px 0;'>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Name</td>"
        f"<td style='padding:4px 0;'>{safe_name}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Email</td>"
        f"<td style='padding:4px 0;'>{safe_email}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Phone</td>"
        f"<td style='padding:4px 0;'>{safe_phone}</td></tr>"
        f"</table>"
        f"<p>Log in to your dashboard to view and follow up with this lead.</p>"
        f"<p>The AgentNexLiFy Team</p>"
    )


def _build_sms_body(business_name: str, lead_name: str, lead_info: dict) -> str:
    """Build the owner-alert SMS body (plain text, no escaping needed)."""
    contact = lead_info.get("email") or lead_info.get("phone") or "no contact info"
    return f"New lead for {business_name}: {lead_name} ({contact})"


async def _send_email_alert(
    tenant_id: str,
    business_name: str,
    owner_email: str,
    lead_name: str,
    lead_info: dict,
    source_label: str = "your chat widget",
) -> None:
    """Send the owner email alert. Swallows every failure."""
    from backend.services.email_sender import send_email

    try:
        await send_email(
            to=owner_email,
            subject=f"New lead for {business_name}: {lead_name}",
            body_html=_build_email_html(business_name, lead_name, lead_info, source_label),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "lead_alert: email send FAILED tenant=%s lead=%s",
            tenant_id, lead_name, exc_info=True,
        )


async def _send_sms_alert(
    tenant_id: str, business_name: str, phone: str, lead_name: str, lead_info: dict
) -> None:
    """Send the owner SMS alert. Passes tenant_id so the demo no-op fires.
    Swallows every failure."""
    from backend.services.twilio_service import send_sms

    try:
        await send_sms(
            to=phone,
            body=_build_sms_body(business_name, lead_name, lead_info),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "lead_alert: SMS send FAILED tenant=%s lead=%s",
            tenant_id, lead_name, exc_info=True,
        )


async def send_new_lead_alert(
    tenant_id: str,
    lead_name: str,
    lead_info: dict,
    lead_id: str = "",
    source_label: str = "your chat widget",
) -> None:
    """Fire instant owner alerts (email + SMS) for a newly captured lead.

    Best-effort, non-blocking, idempotent, demo-safe. NEVER raises:
    callers fire this from FastAPI background tasks where a raised
    exception would propagate into the response cycle.

    Args:
        tenant_id: the tenant the lead belongs to (tenants.id).
        lead_name: display name for the lead ("New visitor" when unknown).
        lead_info: dict with optional "email" / "phone" keys.
        lead_id: the captured lead's id, used for idempotency. When empty
            (legacy callers), the alert still fires but is not deduped.
        source_label: where the lead came from, shown in the email body
            (e.g. "your chat widget", "your website contact form",
            "Facebook Messenger"). Defaults to the widget wording so
            existing callers are unchanged.
    """
    try:
        if _already_alerted(tenant_id, lead_id):
            logger.info(
                "lead_alert: already alerted tenant=%s lead_id=%s, skipping",
                tenant_id, lead_id,
            )
            return

        config = _fetch_tenant_alert_config(tenant_id)
        if not config:
            logger.warning("lead_alert: no tenant config for %s, skipping", tenant_id)
            return

        business_name = config.get("business_name") or "your business"
        owner_email = config.get("owner_email")
        phone = config.get("notification_phone")
        sms_enabled = config.get("sms_notifications_enabled")

        if owner_email:
            await _send_email_alert(
                tenant_id, business_name, owner_email, lead_name, lead_info, source_label
            )
        else:
            logger.info("lead_alert: no owner_email for tenant=%s, email skipped", tenant_id)

        if sms_enabled and phone:
            await _send_sms_alert(
                tenant_id, business_name, phone, lead_name, lead_info
            )
        else:
            logger.info(
                "lead_alert: SMS skipped tenant=%s (sms_enabled=%s phone_set=%s)",
                tenant_id, bool(sms_enabled), bool(phone),
            )
    except Exception:
        # Final backstop: this function is called from background tasks and
        # must never propagate. The channel helpers already swallow their
        # own errors; this guards the config/idempotency path too.
        logger.error(
            "lead_alert: send_new_lead_alert FAILED tenant=%s lead=%s",
            tenant_id, lead_name, exc_info=True,
        )


def fire_new_lead_alert_background(
    tenant_id: str,
    lead_name: str,
    lead_info: dict,
    lead_id: str = "",
    source_label: str = "your chat widget",
) -> None:
    """Schedule ``send_new_lead_alert`` from a sync context without blocking.

    Mirror of ``webhook_dispatcher.fire_event_background``: fire the async
    owner alert onto the running event loop and return immediately. Callers
    are sync code paths (form submit, Messenger ingest) that must not await
    email/SMS sends inside the request/response cycle.

    Best-effort: when there is no running loop (e.g. a pure-sync worker with
    no event loop, or a unit test calling without one), the alert is skipped
    rather than raised. NEVER raises.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug(
            "lead_alert: no running event loop, skipping alert for tenant=%s lead=%s",
            tenant_id, lead_id,
        )
        return
    try:
        loop.create_task(
            send_new_lead_alert(
                tenant_id, lead_name, lead_info, lead_id=lead_id, source_label=source_label
            )
        )
    except Exception:
        logger.error(
            "lead_alert: failed to schedule background alert tenant=%s lead=%s",
            tenant_id, lead_id, exc_info=True,
        )
