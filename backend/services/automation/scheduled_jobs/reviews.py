"""Scheduled jobs — review-related automations."""
import html
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.automation.scheduled_jobs._common import logger


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
            .not_.is_("review_request_sent_at", "null")
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

        # Dedup check: skip if a follow-up was already sent for this appointment
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
                continue  # Already sent a follow-up for this appointment
        except Exception:
            logger.warning(
                "_send_review_followups: dedup check failed for appointment %s",
                appt_id,
                exc_info=True,
            )
            continue  # Skip on dedup failure to avoid duplicate sends

        # Load tenant if not already cached
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

        # Build review link (same logic as main loop)
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

        # CAN-SPAM: skip if lead has unsubscribed
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
                logger.debug("Failed to check unsubscribe status for lead %s, proceeding (fail-open)", lead_id, exc_info=True)

        followup_sent = False

        # Send follow-up email
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

        # Send follow-up SMS
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

        # Record the follow-up in activity_log for dedup on future loop iterations
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
        # Get completed appointments that haven't had review requests sent
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

    # Group by tenant to avoid repeated tenant lookups
    tenant_cache: dict[str, dict] = {}

    for appt in appts.data or []:
        tenant_id = appt["tenant_id"]

        # Load tenant config (cached per tenant)
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

        # Build review link: prefer direct Google write-review URL if place_id exists,
        # otherwise fall back to the manually configured google_review_link.
        place_id = tenant.get("google_place_id")
        if place_id:
            review_link = (
                f"https://search.google.com/local/writereview?placeid={place_id}"
            )
        else:
            review_link = tenant.get("google_review_link") or ""

        if not review_link:
            continue

        # Check delay — default changed from 0 to 2 hours so review requests
        # are sent after a short cool-down rather than immediately on completion.
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

        # CAN-SPAM: skip if lead has unsubscribed
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
                logger.debug("Failed to check unsubscribe status for lead %s, proceeding (fail-open)", lead_id, exc_info=True)

        # Send email review request
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

        # Send SMS review request
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

        # Mark as sent regardless of success to avoid retry loops
        try:
            db.table("appointments").update(
                {
                    "review_request_sent_at": now.isoformat(),
                }
            ).eq("id", appt["id"]).execute()
        except Exception:
            logger.exception(
                "Failed to mark review request sent for appointment %s", appt["id"]
            )

    # --- Follow-up reminder loop ---
    # Find appointments where a review request was sent 48+ hours ago but no
    # follow-up has been sent yet. Dedup via activity_log entries.
    sent += await _send_review_followups(db, now, tenant_cache)

    return sent


async def send_csat_surveys() -> int:
    """Send CSAT surveys for recently completed conversations.

    Checks for conversations that ended 1-2 hours ago (to give a cooling period)
    where the lead has an email and no survey has been sent yet.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=2)).isoformat()
    window_end = (now - timedelta(hours=1)).isoformat()
    sent = 0

    try:
        # Find completed appointments in the window
        appts = (
            db.table("appointments")
            .select("id, tenant_id, lead_id, customer_email, customer_name")
            .eq("status", "completed")
            .gte("updated_at", window_start)
            .lte("updated_at", window_end)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_csat_surveys: failed to query appointments")
        return 0

    for appt in appts.data or []:
        email = appt.get("customer_email")
        if not email:
            continue

        tenant_id = appt["tenant_id"]
        activity_key = f"csat_sent_{appt['id']}"

        # Check if already sent
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", "csat_sent")
                .eq("description", activity_key)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning("Dedup check failed in follow-up review trigger", exc_info=True)
            continue

        # Get business name
        try:
            t = (
                db.table("tenants")
                .select("business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            biz_name = t.data[0]["business_name"] if t.data else "us"
        except Exception:
            biz_name = "us"

        customer_name = appt.get("customer_name") or "there"
        survey_token = f"{tenant_id}:appt_{appt['id']}"
        survey_url = f"https://app.agentnexlify.com/survey?token={survey_token}"

        subject = f"How was your experience with {biz_name}?"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>Thank you for choosing <strong>{biz_name}</strong>!</p>"
            f"<p>We'd love to hear about your experience. It takes just 10 seconds:</p>"
            f"<p style='text-align:center;margin:20px 0;font-size:28px;'>"
            f"<a href='{survey_url}&r=1' style='text-decoration:none;margin:0 4px;'>1</a> "
            f"<a href='{survey_url}&r=2' style='text-decoration:none;margin:0 4px;'>2</a> "
            f"<a href='{survey_url}&r=3' style='text-decoration:none;margin:0 4px;'>3</a> "
            f"<a href='{survey_url}&r=4' style='text-decoration:none;margin:0 4px;'>4</a> "
            f"<a href='{survey_url}&r=5' style='text-decoration:none;margin:0 4px;'>5</a>"
            f"</p>"
            f"<p style='text-align:center;color:#888;font-size:12px;'>1 = Poor &nbsp;&nbsp; 5 = Excellent</p>"
            f"<p>Best,<br>The {biz_name} Team</p>"
        )

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tenant_id,
                    activity_type="csat_sent",
                    description=activity_key,
                )
                logger.info(
                    "Sent CSAT survey to %s for appointment %s", email, appt["id"]
                )
        except Exception:
            logger.exception(
                "Failed to send CSAT survey for appointment %s", appt["id"]
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

        # Look up tenant notification phone
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

        # Log activity regardless of whether SMS is sent
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

        # Send SMS if phone is configured
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
