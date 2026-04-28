"""Scheduled jobs — onboarding automations."""
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import render_template, send_email
from backend.services.automation.templates import _ONBOARDING_STEPS
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.automation.scheduled_jobs._common import logger


async def send_onboarding_emails() -> int:
    """Send onboarding drip emails to tenants based on their signup date.

    Checks tenants created within specific time windows (Day 1, 3, 7, 14).
    Uses activity_log to track which emails have been sent (avoids duplicates).
    Returns count of emails sent.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    sent = 0

    for step in _ONBOARDING_STEPS:
        window_start = now - timedelta(hours=step["max_hours"])
        window_end = now - timedelta(hours=step["min_hours"])
        activity_type = f"onboarding_email_day_{step['day']}"

        try:
            tenants = (
                db.table("tenants")
                .select("id, owner_name, owner_email, business_name")
                .gte("created_at", window_start.isoformat())
                .lte("created_at", window_end.isoformat())
                .limit(BATCH_LIMIT)
                .execute()
            )
        except Exception:
            logger.exception(
                "send_onboarding_emails: failed to query tenants for day %d",
                step["day"],
            )
            continue

        for tenant in tenants.data or []:
            tid = tenant["id"]
            email = tenant.get("owner_email")
            if not email:
                continue

            # Check if already sent
            try:
                existing = (
                    db.table("activity_log")
                    .select("id", count="exact")
                    .eq("tenant_id", tid)
                    .eq("activity_type", activity_type)
                    .limit(1)
                    .execute()
                )
                if existing.count and existing.count > 0:
                    continue
            except Exception:
                logger.warning(
                    "send_onboarding_emails: couldn't check activity_log for %s, skipping",
                    tid,
                )
                continue

            owner_name = tenant.get("owner_name") or "there"
            biz_name = tenant.get("business_name") or "your business"
            context = {"owner_name": owner_name, "business_name": biz_name}

            subject = render_template(step["subject"], context)
            body = render_template(step["body"], context)

            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    body_html=body,
                    tenant_id=tid,
                )
                if result.get("success"):
                    sent += 1
                    logger.info(
                        "Sent onboarding day %d email to %s (tenant %s)",
                        step["day"],
                        email,
                        tid,
                    )
                    # Track in activity_log
                    db.table("activity_log").insert(
                        {
                            "tenant_id": tid,
                            "activity_type": activity_type,
                            "description": f"Onboarding email Day {step['day']} sent to {email}",
                        }
                    ).execute()
            except Exception:
                logger.exception(
                    "Failed to send onboarding day %d email to %s", step["day"], email
                )

    return sent
