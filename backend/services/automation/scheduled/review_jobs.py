"""Review scheduled jobs — review requests, follow-ups, new review alerts."""

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.automation.trigger import BATCH_LIMIT

logger = logging.getLogger(__name__)


async def send_pending_review_requests() -> int:
    """Check for completed appointments that need review requests sent.

    Queries appointments with status='completed' where review_request_sent_at
    is null and the tenant has review requests enabled. Respects the configured
    delay (hours since completion). Sends via email, SMS, or both.

    Returns count of review requests sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    try:
        appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, updated_at, lead_id"
            )
            .eq("status", "completed")
            .is_("review_request_sent_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_pending_review_requests: failed to query appointments")
        return 0

    tenant_cache: dict[str, dict] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select(
                        "business_name, google_review_link, google_place_id, review_request_config, plan"
                    )
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.exception(
                    "send_pending_review_requests: failed to load tenant %s", tenant_id
                )
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        config = tenant.get("review_request_config") or {}
        if not config.get("enabled"):
            continue

        place_id = tenant.get("google_place_id")
        if place_id:
            review_link = (
                f"https://search.google.com/local/writereview?placeid={place_id}"
            )
        else:
            review_link = tenant.get("google_review_link") or ""

        if not review_link:
            continue

        delay_hours = config.get("delay_hours", 2)
        try:
            completed_at = datetime.fromisoformat(
                appt["updated_at"].replace("Z", "+00:00")
            )
        except Exception:
            logger.warning("Failed to parse appointment timestamp", exc_info=True)
            continue

        if (now - completed_at).total_seconds() < delay_hours * 3600:
            continue

        business_name = html.escape(tenant.get("business_name") or "Our Team")
        customer_name = html.escape(appt.get("customer_name") or "there")
        method = config.get("method", "email")

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
                logger.debug(
                    "Failed to check unsubscribe status for lead %s, proceeding (fail-open)",
                    lead_id,
                    exc_info=True,
                )

        if method in ("email", "both") and appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            safe_review_link = html.escape(review_link, quote=True)
            subject = f"How was your experience with {business_name}?"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>Thank you for your recent visit with <strong>{business_name}</strong>! "
                f"We hope everything went well.</p>"
                f"<p>We'd really appreciate it if you could take a moment to share your experience:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{safe_review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;font-weight:600;">Leave a Review</a></p>'
                f"<p>Your feedback helps us improve and helps others find us. Thank you!</p>"
                f"<p>Best,<br>The {business_name} Team</p>"
            )
            try:
                result = await send_email(
                    to=appt["customer_email"],
                    subject=subject,
                    body_html=body,
                    tenant_id=tenant_id,
                    unsubscribe_url=unsub_url,
                )
                if result.get("success"):
                    sent += 1
                    logger.info(
                        "Sent review request email for appointment %s", appt["id"]
                    )
            except Exception:
                logger.exception(
                    "Failed to send review request email for appointment %s", appt["id"]
                )

        if method in ("sms", "both") and appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, thanks for visiting {business_name}! "
                f"We'd love your feedback. Leave a review here: {review_link}"
            )
            try:
                plan = tenant.get("plan") or "free"
                if check_sms_rate_limit(tenant_id, plan):
                    sms_ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if sms_ok:
                        increment_sms_count(tenant_id)
                        sent += 1
                        logger.info(
                            "Sent review request SMS for appointment %s", appt["id"]
                        )
            except Exception:
                logger.exception(
                    "Failed to send review request SMS for appointment %s", appt["id"]
                )

        try:
            db.table("appointments").update(
                {"review_request_sent_at": now.isoformat()}
            ).eq("id", appt["id"]).execute()
        except Exception:
            logger.exception(
                "Failed to mark review request sent for appointment %s", appt["id"]
            )

    sent += await _send_review_followups(db, now, tenant_cache)

    return sent


async def _send_review_followups(
    db: Any,
    now: datetime,
    tenant_cache: dict[str, dict],
) -> int:
    """Send one follow-up review reminder for requests sent 48+ hours ago with no prior followup.

    Deduplication: checks activity_log for activity_type='review_followup_{appointment_id}'.
    Returns count of follow-ups sent.
    """
    sent = 0
    followup_cutoff = now - timedelta(hours=48)

    try:
        followup_appts = (
            db.table("appointments")
            .select(
                "id, tenant_id, customer_name, customer_email, customer_phone, lead_id, review_request_sent_at"
            )
            .eq("status", "completed")
            .filter("review_request_sent_at", "not.is", "null")
            .lte("review_request_sent_at", followup_cutoff.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("_send_review_followups: failed to query appointments")
        return 0

    for appt in followup_appts.data or []:
        appt_id = appt["id"]
        tenant_id = appt["tenant_id"]
        followup_activity_type = f"review_followup_{appt_id}"

        try:
            dedup_result = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", followup_activity_type)
                .limit(1)
                .execute()
            )
            if dedup_result.data:
                continue
        except Exception:
            logger.warning(
                "_send_review_followups: dedup check failed for appointment %s",
                appt_id,
                exc_info=True,
            )
            continue

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select(
                        "business_name, google_review_link, google_place_id, review_request_config, plan"
                    )
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                logger.exception(
                    "_send_review_followups: failed to load tenant %s", tenant_id
                )
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant:
            continue

        config = tenant.get("review_request_config") or {}
        if not config.get("enabled"):
            continue

        place_id = tenant.get("google_place_id")
        if place_id:
            review_link = (
                f"https://search.google.com/local/writereview?placeid={place_id}"
            )
        else:
            review_link = tenant.get("google_review_link") or ""

        if not review_link:
            continue

        business_name = html.escape(tenant.get("business_name") or "Our Team")
        customer_name = html.escape(appt.get("customer_name") or "there")
        method = config.get("method", "email")

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
                logger.debug(
                    "Failed to check unsubscribe status for lead %s, proceeding (fail-open)",
                    lead_id,
                    exc_info=True,
                )

        followup_sent = False

        if method in ("email", "both") and appt.get("customer_email"):
            unsub_url = build_unsubscribe_url(lead_id, tenant_id) if lead_id else ""
            safe_review_link = html.escape(review_link, quote=True)
            subject = f"Still happy to help — leave us a review, {customer_name}!"
            body = (
                f"<h2>Hi {customer_name},</h2>"
                f"<p>We wanted to follow up on our earlier message. We'd love to hear "
                f"about your experience with <strong>{business_name}</strong>.</p>"
                f"<p>If you have a moment, we'd really appreciate a quick review:</p>"
                f'<p style="text-align:center;margin:20px 0;">'
                f'<a href="{safe_review_link}" style="background:#4f46e5;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;font-weight:600;">Leave a Review</a></p>'
                f"<p>It only takes a minute and means a lot to us. Thank you!</p>"
                f"<p>Best,<br>The {business_name} Team</p>"
            )
            try:
                result = await send_email(
                    to=appt["customer_email"],
                    subject=subject,
                    body_html=body,
                    tenant_id=tenant_id,
                    unsubscribe_url=unsub_url,
                )
                if result.get("success"):
                    sent += 1
                    followup_sent = True
                    logger.info(
                        "Sent review follow-up email for appointment %s", appt_id
                    )
            except Exception:
                logger.exception(
                    "Failed to send review follow-up email for appointment %s", appt_id
                )

        if method in ("sms", "both") and appt.get("customer_phone"):
            sms_body = (
                f"Hi {customer_name}, just a friendly reminder from {business_name} — "
                f"we'd love your review! {review_link}"
            )
            try:
                plan = tenant.get("plan") or "free"
                if check_sms_rate_limit(tenant_id, plan):
                    sms_ok = await send_sms(to=appt["customer_phone"], body=sms_body)
                    if sms_ok:
                        increment_sms_count(tenant_id)
                        sent += 1
                        followup_sent = True
                        logger.info(
                            "Sent review follow-up SMS for appointment %s", appt_id
                        )
            except Exception:
                logger.exception(
                    "Failed to send review follow-up SMS for appointment %s", appt_id
                )

        if followup_sent:
            try:
                activity_row: dict[str, Any] = {
                    "tenant_id": tenant_id,
                    "activity_type": followup_activity_type,
                    "description": f"Review follow-up sent for appointment {appt_id}",
                    "metadata": {"appointment_id": appt_id},
                }
                if lead_id:
                    activity_row["lead_id"] = lead_id
                db.table("activity_log").insert(activity_row).execute()
            except Exception:
                logger.warning(
                    "_send_review_followups: failed to log followup activity for appointment %s",
                    appt_id,
                    exc_info=True,
                )

    return sent


async def check_new_reviews() -> int:
    """Check for new reviews created in the last 60 seconds and notify tenant owners.

    For each new review, if the tenant has a notification_phone, sends an SMS alert
    and logs an activity_log entry with activity_type='new_review_alert'.

    Returns count of alerts sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(seconds=60)).isoformat()
    sent = 0

    try:
        recent_reviews = (
            db.table("reviews")
            .select("id, tenant_id, rating, author_name, platform, review_text")
            .gte("created_at", cutoff)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("check_new_reviews: failed to query recent reviews")
        return 0

    for review in recent_reviews.data or []:
        tenant_id = review.get("tenant_id")
        if not tenant_id:
            continue

        try:
            tenant_result = (
                db.table("tenants")
                .select("notification_phone, business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "check_new_reviews: failed to look up tenant %s", tenant_id
            )
            continue

        if not tenant_result.data:
            continue

        tenant = tenant_result.data[0]
        notification_phone = tenant.get("notification_phone")

        rating = review.get("rating", "?")
        author_name = review.get("author_name", "Someone")
        platform = review.get("platform", "unknown")
        review_text = review.get("review_text") or ""
        truncated_text = (
            review_text[:80] + "..." if len(review_text) > 80 else review_text
        )

        from backend.services.activity import log_activity

        log_activity(
            tenant_id=tenant_id,
            activity_type="new_review_alert",
            description=(f"New {rating}-star review from {author_name} on {platform}"),
            metadata={
                "review_id": review.get("id"),
                "rating": rating,
                "author_name": author_name,
                "platform": platform,
            },
        )

        if notification_phone:
            sms_body = (
                f"New {rating}-star review from {author_name} on {platform}: "
                f"'{truncated_text}'. Reply in your dashboard."
            )
            try:
                sms_ok = await send_sms(to=notification_phone, body=sms_body)
                if sms_ok:
                    sent += 1
                    logger.info(
                        "Sent new review alert SMS to %s for tenant %s (review %s)",
                        notification_phone,
                        tenant_id,
                        review.get("id"),
                    )
            except Exception:
                logger.exception(
                    "check_new_reviews: failed to send SMS to %s for tenant %s",
                    notification_phone,
                    tenant_id,
                )

    return sent
