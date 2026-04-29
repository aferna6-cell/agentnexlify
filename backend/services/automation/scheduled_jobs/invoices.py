"""Scheduled jobs — invoice payment reminders."""
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email
from backend.services.twilio_service import send_sms
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.automation.scheduled_jobs._common import logger


async def send_invoice_payment_reminders() -> int:
    """Send reminders for overdue or soon-due unpaid invoices.

    Logic:
    - Invoices with status='sent' and due_date <= today -> mark as 'overdue' and send reminder
    - Invoices with status='sent' and due_date = tomorrow -> send a friendly "due tomorrow" nudge
    - Uses activity_log to dedup (one reminder per invoice per day)

    Returns count of reminders sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    activity_date_tag = f"invoice_reminder_{today}"
    sent = 0

    # Fetch sent invoices that are due today or earlier (overdue) or due tomorrow
    try:
        invoices = (
            db.table("invoices")
            .select(
                "id, tenant_id, lead_id, invoice_number, total, due_date, status, stripe_payment_link"
            )
            .eq("status", "sent")
            .lte("due_date", tomorrow)
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_invoice_payment_reminders: failed to query invoices")
        return 0

    for inv in invoices.data or []:
        inv_id = inv["id"]
        tenant_id = inv.get("tenant_id")
        lead_id = inv.get("lead_id")
        due_date = inv.get("due_date", "")

        if not tenant_id or not lead_id:
            continue

        # Check dedup — one reminder per invoice per day
        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .eq("activity_type", activity_date_tag)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning(
                "send_invoice_payment_reminders: dedup check failed for invoice %s",
                inv_id,
            )
            continue

        # Mark overdue if due_date <= today
        is_overdue = due_date <= today
        if is_overdue:
            try:
                db.table("invoices").update({"status": "overdue"}).eq(
                    "id", inv_id
                ).execute()
            except Exception:
                logger.warning("Failed to mark invoice %s as overdue", inv_id)

        # Get lead contact info
        try:
            lead_result = (
                db.table("leads")
                .select("name, email, phone")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "send_invoice_payment_reminders: failed to look up lead %s", lead_id
            )
            continue

        if not lead_result.data:
            continue
        lead = lead_result.data[0]

        # Get business info
        try:
            tenant_result = (
                db.table("tenants")
                .select("business_name, owner_email")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "send_invoice_payment_reminders: failed to look up tenant %s", tenant_id
            )
            continue

        if not tenant_result.data:
            continue
        tenant_info = tenant_result.data[0]

        biz_name = tenant_info.get("business_name") or "Your Service Provider"
        cust_name = lead.get("name") or "Customer"
        inv_num = inv.get("invoice_number") or "N/A"
        total = inv.get("total", 0)
        pay_link = inv.get("stripe_payment_link") or ""

        if is_overdue:
            subject = f"Payment overdue — Invoice {inv_num} from {biz_name}"
            body_text = (
                f"Hi {cust_name}, this is a reminder that Invoice {inv_num} "
                f"for ${total:.2f} was due on {due_date} and is now overdue."
            )
        else:
            subject = f"Payment reminder — Invoice {inv_num} due tomorrow"
            body_text = (
                f"Hi {cust_name}, just a friendly reminder that Invoice {inv_num} "
                f"for ${total:.2f} from {biz_name} is due tomorrow ({due_date})."
            )

        pay_section = f" Pay now: {pay_link}" if pay_link else ""

        # Send email
        email = lead.get("email")
        if email:
            html_body = (
                f"<div style='font-family:sans-serif;max-width:600px;'>"
                f"<h2 style='color:#1e293b;'>{subject}</h2>"
                f"<p style='color:#374151;font-size:16px;'>{body_text}</p>"
            )
            if pay_link:
                html_body += (
                    f"<p style='margin-top:24px;'>"
                    f"<a href='{pay_link}' style='background:#3b82f6;color:white;padding:12px 24px;"
                    f"border-radius:8px;text-decoration:none;font-weight:bold;'>Pay Now</a></p>"
                )
            html_body += (
                f"<p style='color:#6b7280;margin-top:24px;'>— {biz_name}</p></div>"
            )

            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    body_html=html_body,
                    tenant_id=tenant_id,
                )
                if result.get("success"):
                    sent += 1
                    logger.info(
                        "Sent invoice reminder email for %s to %s", inv_num, email
                    )
            except Exception:
                logger.exception(
                    "Failed to send invoice reminder email for %s", inv_num
                )

        # Send SMS
        phone = lead.get("phone")
        if phone:
            sms_body = f"{body_text}{pay_section}"
            try:
                sms_ok = await send_sms(to=phone, body=sms_body)
                if sms_ok:
                    sent += 1
                    logger.info(
                        "Sent invoice reminder SMS for %s to %s", inv_num, phone
                    )
            except Exception:
                logger.exception("Failed to send invoice reminder SMS for %s", inv_num)

        # Track in activity_log for dedup
        try:
            from backend.services.activity import log_activity

            log_activity(
                tenant_id=tenant_id,
                lead_id=lead_id,
                activity_type=activity_date_tag,
                description=f"{'Overdue' if is_overdue else 'Due tomorrow'} reminder sent for Invoice {inv_num} (${total:.2f})",
                metadata={"invoice_id": inv_id, "is_overdue": is_overdue},
            )
        except Exception:
            logger.warning("Failed to log activity for invoice reminder %s", inv_id)

    return sent
