"""Widget lead notifications: SMS + email to tenant owner on new-lead capture.

Extracted from widget_lead_helpers.py (god class split 2026-05-24).
Re-exported via widget_lead_helpers so existing test patches at
`backend.routers.widget_lead_helpers._send_new_lead_sms_notification` continue
to resolve correctly.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not add
`from __future__ import annotations` here.
"""

import logging

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)


async def _send_new_lead_sms_notification(
    tenant_id: str, lead_name: str, lead_info: dict[str, str]
) -> None:
    """Send SMS notification to tenant owner when a new lead is captured."""
    logger.info("SMS_FUNCTION: entered function tenant=%s lead=%s", tenant_id, lead_name)
    logger.info(
        "sms_notification: starting for tenant=%s lead=%s info_keys=%s",
        tenant_id, lead_name, list(lead_info.keys()),
    )
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("notification_phone, sms_notifications_enabled, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("sms_notification: no tenant found for id=%s", tenant_id)
        return
    tenant = result.data[0]
    sms_enabled = tenant.get("sms_notifications_enabled")
    phone = tenant.get("notification_phone")
    logger.info(
        "sms_notification: tenant=%s sms_enabled=%s phone=%s",
        tenant_id, sms_enabled, phone,
    )
    if not sms_enabled or not phone:
        logger.info("sms_notification: skipping — sms_enabled=%s phone=%s", sms_enabled, phone)
        return

    contact = lead_info.get("email") or lead_info.get("phone") or "no contact info"
    body = f"New lead for {tenant.get('business_name', 'your business')}: {lead_name} ({contact})"
    logger.info("sms_notification: sending to=%s body_len=%d", phone, len(body))

    try:
        from backend.services.twilio_service import send_sms
        await send_sms(to=phone, body=body)
        logger.info("sms_notification: sent successfully for tenant=%s", tenant_id)
    except Exception:
        logger.error("sms_notification: FAILED to send for tenant=%s", tenant_id, exc_info=True)


async def _send_new_lead_email_notification(
    tenant_id: str, lead_name: str, lead_info: dict[str, str]
) -> None:
    """Send email notification to tenant owner when a new lead is captured."""
    import html as html_mod

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("owner_email, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return
    tenant = result.data[0]
    owner_email = tenant.get("owner_email")
    if not owner_email:
        return

    raw_business_name = tenant.get("business_name") or "your business"
    business_name = html_mod.escape(raw_business_name)
    safe_name = html_mod.escape(lead_name)
    safe_email = html_mod.escape(lead_info.get("email") or "not provided")
    safe_phone = html_mod.escape(lead_info.get("phone") or "not provided")

    body_html = (
        f"<h2>New lead for {business_name}</h2>"
        f"<p>A new lead was just captured from your chat widget:</p>"
        f"<table style='border-collapse:collapse;margin:16px 0;'>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Name</td>"
        f"<td style='padding:4px 0;'>{safe_name}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Email</td>"
        f"<td style='padding:4px 0;'>{safe_email}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;font-weight:bold;'>Phone</td>"
        f"<td style='padding:4px 0;'>{safe_phone}</td></tr>"
        f"</table>"
        f"<p>Log in to your dashboard to view and follow up with this lead.</p>"
        f"<p>— The AgentNexLiFy Team</p>"
    )

    try:
        await send_email(
            to=owner_email,
            subject=f"New lead for {raw_business_name}: {lead_name}",
            body_html=body_html,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "email_notification: FAILED for tenant=%s lead=%s",
            tenant_id, lead_name, exc_info=True,
        )
