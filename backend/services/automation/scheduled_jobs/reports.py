"""Scheduled jobs — reporting automations."""
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.automation.scheduled_jobs._common import logger


async def send_monthly_reports() -> int:
    """Send monthly performance reports to tenants with autopilot_enabled.

    Queries tenants where autopilot_enabled is true and last_monthly_report_at
    is NULL or more than 28 days ago. For each, builds a summary of the past
    month's conversations, leads, appointments, and reviews, then emails it to
    the owner. Updates last_monthly_report_at on the tenant after sending.

    Returns count of reports sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=28)).isoformat()
    month_start = (now - timedelta(days=30)).isoformat()
    sent = 0

    # Fetch tenants eligible for a monthly report:
    # autopilot_enabled = true AND (last_monthly_report_at IS NULL OR < 28 days ago)
    try:
        # First: tenants with autopilot_enabled and last_monthly_report_at IS NULL
        null_result = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .eq("autopilot_enabled", True)
            .is_("last_monthly_report_at", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
        # Second: tenants with autopilot_enabled and last_monthly_report_at < cutoff
        old_result = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .eq("autopilot_enabled", True)
            .lte("last_monthly_report_at", cutoff)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_monthly_reports: failed to query eligible tenants")
        return 0

    # Combine and deduplicate by tenant ID
    seen_ids: set[str] = set()
    eligible_tenants: list[dict] = []
    for tenant in (null_result.data or []) + (old_result.data or []):
        if tenant["id"] not in seen_ids:
            seen_ids.add(tenant["id"])
            eligible_tenants.append(tenant)

    for tenant in eligible_tenants:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        owner_name = tenant.get("owner_name") or "there"
        business_name = tenant.get("business_name") or "Your Business"

        # Gather metrics for the past 30 days
        conversations_count = 0
        leads_count = 0
        appointments_count = 0
        reviews_count = 0

        try:
            conv_result = (
                db.table("chat_messages")
                .select("session_id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .execute()
            )
            # Unique sessions = unique conversations
            if conv_result.data:
                unique_sessions = {m["session_id"] for m in conv_result.data}
                conversations_count = len(unique_sessions)
        except Exception:
            logger.warning(
                "send_monthly_reports: failed to count conversations for tenant %s",
                tid,
                exc_info=True,
            )

        try:
            # leads table uses client_id, not tenant_id
            leads_result = (
                db.table("leads")
                .select("id", count="exact")
                .eq("client_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            leads_count = leads_result.count or 0
        except Exception:
            logger.warning(
                "send_monthly_reports: failed to count leads for tenant %s",
                tid,
                exc_info=True,
            )

        try:
            appt_result = (
                db.table("appointments")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            appointments_count = appt_result.count or 0
        except Exception:
            logger.warning(
                "send_monthly_reports: failed to count appointments for tenant %s",
                tid,
                exc_info=True,
            )

        try:
            rev_result = (
                db.table("reviews")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", month_start)
                .limit(1)
                .execute()
            )
            reviews_count = rev_result.count or 0
        except Exception:
            logger.warning(
                "send_monthly_reports: failed to count reviews for tenant %s",
                tid,
                exc_info=True,
            )

        # Build report email
        subject = f"Monthly Performance Report for {business_name}"
        body_html = (
            f"<h2>Hi {owner_name},</h2>"
            f"<p>Here's your monthly performance summary for <strong>{business_name}</strong>:</p>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;'>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Conversations</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{conversations_count}</td>"
            f"</tr>"
            f"<tr>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Leads Captured</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{leads_count}</td>"
            f"</tr>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Appointments Booked</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{appointments_count}</td>"
            f"</tr>"
            f"<tr>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;font-weight:600;'>Reviews Received</td>"
            f"<td style='padding:12px 16px;border:1px solid #e5e7eb;text-align:right;font-size:1.2em;'>{reviews_count}</td>"
            f"</tr>"
            f"</table>"
            f"<p>Keep up the great work! Visit your <a href='https://app.agentnexlify.com'>dashboard</a> "
            f"to see detailed analytics and manage your business.</p>"
            f"<p>Best,<br>The AgentNexLiFy Team</p>"
        )

        try:
            result = await send_email(
                to=email,
                subject=subject,
                body_html=body_html,
                tenant_id=tid,
            )
            if result.get("success"):
                sent += 1
                logger.info(
                    "Sent monthly report to %s (tenant %s): convos=%d leads=%d appts=%d reviews=%d",
                    email,
                    tid,
                    conversations_count,
                    leads_count,
                    appointments_count,
                    reviews_count,
                )

                # Update last_monthly_report_at on the tenant
                try:
                    db.table("tenants").update(
                        {
                            "last_monthly_report_at": now.isoformat(),
                        }
                    ).eq("id", tid).execute()
                except Exception:
                    logger.exception(
                        "send_monthly_reports: failed to update last_monthly_report_at for tenant %s",
                        tid,
                    )
            else:
                logger.warning(
                    "send_monthly_reports: email send returned failure for tenant %s",
                    tid,
                )
        except Exception:
            logger.exception(
                "send_monthly_reports: failed to send report email to %s (tenant %s)",
                email,
                tid,
            )

    return sent


async def send_portal_links() -> int:
    """Send portal links to customers after job completion.

    When an appointment is marked 'completed' and the lead has a portal token,
    auto-send an email with the portal link. Tracks delivery via activity_log.
    """
    db = get_service_supabase()
    sent = 0

    try:
        # Find completed appointments without portal link sent
        appts = (
            db.table("appointments")
            .select("id, tenant_id, lead_id, customer_name, customer_email")
            .eq("status", "completed")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_portal_links: failed to query completed appointments")
        return 0

    for appt in appts.data or []:
        lead_id = appt.get("lead_id")
        customer_email = appt.get("customer_email")
        if not lead_id or not customer_email:
            continue

        tenant_id = appt["tenant_id"]
        activity_key = f"portal_link_sent_{appt['id']}"

        # Check if already sent
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", "portal_link_sent")
                .eq("description", activity_key)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning("Dedup check failed in review request trigger", exc_info=True)
            continue

        # Check if portal token exists
        try:
            tok_result = (
                db.table("portal_tokens")
                .select("token")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning("Failed to insert review request record", exc_info=True)
            continue

        if not tok_result.data:
            continue

        token = tok_result.data[0]["token"]
        portal_url = f"https://app.agentnexlify.com/client/{token}"

        # Get business name
        try:
            t_result = (
                db.table("tenants")
                .select("business_name")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            biz_name = (
                t_result.data[0]["business_name"] if t_result.data else "Our Team"
            )
        except Exception:
            biz_name = "Our Team"

        customer_name = appt.get("customer_name") or "there"

        subject = f"Your service details from {biz_name}"
        body = (
            f"<h2>Hi {customer_name},</h2>"
            f"<p>Thank you for choosing <strong>{biz_name}</strong>!</p>"
            f"<p>You can view your service details, documents, and book again anytime:</p>"
            f"<p style='text-align:center;margin:20px 0;'>"
            f"<a href='{portal_url}' style='background:#3b82f6;color:#fff;padding:12px 24px;"
            f"border-radius:6px;text-decoration:none;font-weight:600;'>View Your Portal</a></p>"
            f"<p>Best,<br>The {biz_name} Team</p>"
        )

        try:
            result = await send_email(
                to=customer_email, subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
                # Track delivery
                from backend.services.activity import log_activity

                log_activity(
                    tenant_id=tenant_id,
                    activity_type="portal_link_sent",
                    description=activity_key,
                )
                logger.info(
                    "Sent portal link to %s for appointment %s",
                    customer_email,
                    appt["id"],
                )
        except Exception:
            logger.exception(
                "Failed to send portal link for appointment %s", appt["id"]
            )

    return sent
