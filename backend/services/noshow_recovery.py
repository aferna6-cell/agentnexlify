"""No-show recovery sequences — automated outreach when appointments are missed.

Flow:
  1. Detect appointments with status='no_show' that haven't been followed up
  2. Send empathetic SMS + email to customer offering easy rebooking
  3. If no response after 24h, send one follow-up with optional incentive
  4. Track all outreach in activity_log to prevent duplicates

Runs on the 5-min automation tier.
"""

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.config import settings
from backend.models.database import get_supabase
from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50
# Wait at least 1 hour after no-show before reaching out
INITIAL_DELAY_HOURS = 1
# Follow-up after 24 hours if no rebooking
FOLLOWUP_DELAY_HOURS = 24


async def process_noshow_recovery() -> int:
    """Find no-show appointments and send recovery outreach.

    Returns count of recovery messages sent.
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    # Get no-show appointments that haven't had recovery outreach
    try:
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, "
                "start_time, updated_at, lead_id"
            )
            .eq("status", "no_show")
            .is_("noshow_recovery_sent_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("noshow_recovery: failed to query no-show appointments")
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]
        appt_id = appt["id"]

        # Parse no-show timestamp (updated_at = when status changed)
        try:
            noshow_at = datetime.fromisoformat(
                appt["updated_at"].replace("Z", "+00:00")
            )
        except Exception:
            continue

        # Wait the initial delay before sending
        if (now - noshow_at).total_seconds() < INITIAL_DELAY_HOURS * 3600:
            continue

        # Load tenant config (cached)
        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, plan, google_review_link, owner_email")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.warning("noshow_recovery: failed to load tenant %s", tenant_id, exc_info=True)
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        plan = tenant.get("plan") or "free"
        # Only available on paid plans
        if plan == "free":
            continue

        business_name = tenant.get("business_name") or "Our Team"
        customer_name = appt.get("customer_name") or "there"
        safe_biz = html.escape(business_name)
        safe_name = html.escape(customer_name)

        # CAN-SPAM: check unsubscribe status
        lead_id = appt.get("lead_id")
        if lead_id:
            try:
                lr = (
                    db.table("leads")
                    .select("unsubscribed")
                    .eq("id", lead_id)
                    .limit(1)
                    .execute()
                )
                if lr.data and lr.data[0].get("unsubscribed"):
                    continue
            except Exception:
                logger.debug("noshow_recovery: unsubscribe check failed for lead %s", lead_id, exc_info=True)

        # Build rebooking URL
        base_url = settings.api_url.rstrip("/")
        # Use business slug for booking page link
        rebook_url = f"{base_url}/api/v1/book/reschedule/{appt_id}?token=noshow"
        try:
            from backend.routers.booking_page import build_reschedule_url
            rebook_url = build_reschedule_url(appt_id)
        except Exception:
            logger.debug("noshow_recovery: could not build signed reschedule URL", exc_info=True)

        messages_sent = 0

        # Send SMS
        if appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, we missed you at your appointment with {business_name}. "
                f"We hope everything is okay! "
                f"Would you like to reschedule? It's easy: {rebook_url}"
            )
            try:
                if check_sms_rate_limit(tenant_id, plan):
                    ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if ok:
                        increment_sms_count(tenant_id)
                        messages_sent += 1
            except Exception:
                logger.warning("noshow_recovery: SMS failed for appointment %s", appt_id, exc_info=True)

        # Send email
        if appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            subject = f"We missed you, {safe_name}!"
            body_html = (
                f"<h2>Hi {safe_name},</h2>"
                f"<p>We noticed you weren't able to make your appointment with "
                f"<strong>{safe_biz}</strong>. We hope everything is okay!</p>"
                f"<p>Life happens — no worries at all. If you'd like to reschedule, "
                f"it only takes a moment:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{html.escape(rebook_url, quote=True)}" '
                f'style="background:#4f46e5;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;font-weight:600;">'
                f'Reschedule Now</a></p>'
                f"<p>We look forward to seeing you soon!</p>"
                f"<p>Best,<br>The {safe_biz} Team</p>"
            )
            try:
                result = await send_email(
                    to=appt["customer_email"],
                    subject=subject,
                    body_html=body_html,
                    tenant_id=tenant_id,
                    unsubscribe_url=unsub_url,
                )
                if result.get("success"):
                    messages_sent += 1
            except Exception:
                logger.warning("noshow_recovery: email failed for appointment %s", appt_id, exc_info=True)

        if messages_sent > 0:
            sent += messages_sent
            # Mark appointment so we don't send again
            try:
                db.table("appointments").update({
                    "noshow_recovery_sent_at": now.isoformat(),
                }).eq("id", appt_id).execute()
            except Exception:
                logger.warning("noshow_recovery: failed to mark appointment %s", appt_id, exc_info=True)

            # Log activity
            try:
                db.table("activity_log").insert({
                    "tenant_id": tenant_id,
                    "action": "noshow_recovery_sent",
                    "description": f"No-show recovery sent to {customer_name} for appointment {appt_id}",
                    "metadata": {"appointment_id": appt_id, "lead_id": lead_id},
                }).execute()
            except Exception:
                logger.debug("noshow_recovery: activity log failed", exc_info=True)

            fire_event_background(tenant_id, "appointment.noshow_recovery", {
                "appointment_id": appt_id,
                "customer_name": customer_name,
                "messages_sent": messages_sent,
            })

    # --- Follow-up for no-shows that haven't rebooked ---
    sent += await _send_noshow_followups(db, now, tenant_cache)

    return sent


async def _send_noshow_followups(
    db: Any,
    now: datetime,
    tenant_cache: dict[str, dict | None],
) -> int:
    """Send follow-up to no-shows who haven't rebooked after 24h."""
    sent = 0
    cutoff = (now - timedelta(hours=FOLLOWUP_DELAY_HOURS)).isoformat()

    try:
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, "
                "lead_id, noshow_recovery_sent_at"
            )
            .eq("status", "no_show")
            .not_.is_("noshow_recovery_sent_at", "null")
            .is_("noshow_followup_sent_at", "null")
            .lte("noshow_recovery_sent_at", cutoff)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("noshow_followups: failed to query")
        return 0

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]
        appt_id = appt["id"]

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        plan = tenant.get("plan") or "free"
        if plan == "free":
            continue

        business_name = tenant.get("business_name") or "Our Team"
        customer_name = appt.get("customer_name") or "there"

        # Check if customer already rebooked (new appointment exists)
        try:
            if appt.get("customer_email"):
                rebooked = (
                    tenant_table(db, "appointments", tenant_id)
                    .select("id")
                    .eq("customer_email", appt["customer_email"])
                    .eq("status", "confirmed")
                    .gt("start_time", now.isoformat())
                    .limit(1)
                    .execute()
                )
                if rebooked.data:
                    # Already rebooked — mark followup as done, skip sending
                    db.table("appointments").update({
                        "noshow_followup_sent_at": now.isoformat(),
                    }).eq("id", appt_id).execute()
                    continue
        except Exception:
            logger.debug("noshow_followup: rebook check failed", exc_info=True)

        messages_sent = 0

        # Follow-up SMS
        if appt.get("customer_phone"):
            sms = (
                f"Hi {customer_name}, just checking in from {business_name}. "
                f"We'd love to get you rescheduled whenever works for you. "
                f"Reply to this text or visit our booking page anytime!"
            )
            try:
                if check_sms_rate_limit(tenant_id, plan):
                    ok = await send_sms(to=appt["customer_phone"], body=sms)
                    if ok:
                        increment_sms_count(tenant_id)
                        messages_sent += 1
            except Exception:
                logger.debug("noshow_followup: SMS failed", exc_info=True)

        # Follow-up email
        if appt.get("customer_email"):
            safe_biz = html.escape(business_name)
            safe_name = html.escape(customer_name)
            lead_id = appt.get("lead_id")
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            try:
                await send_email(
                    to=appt["customer_email"],
                    subject=f"Still thinking of you, {safe_name}",
                    body_html=(
                        f"<h2>Hi {safe_name},</h2>"
                        f"<p>We just wanted to follow up and let you know that "
                        f"<strong>{safe_biz}</strong> would love to see you whenever "
                        f"you're ready.</p>"
                        f"<p>No pressure — just reply to this email or give us a call "
                        f"to reschedule at your convenience.</p>"
                        f"<p>Warm regards,<br>The {safe_biz} Team</p>"
                    ),
                    tenant_id=tenant_id,
                    unsubscribe_url=unsub_url,
                )
                messages_sent += 1
            except Exception:
                logger.debug("noshow_followup: email failed", exc_info=True)

        if messages_sent > 0:
            sent += messages_sent
            try:
                db.table("appointments").update({
                    "noshow_followup_sent_at": now.isoformat(),
                }).eq("id", appt_id).execute()
            except Exception:
                logger.debug("noshow_followup: mark failed", exc_info=True)

    return sent
