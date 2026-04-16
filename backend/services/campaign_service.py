"""Campaign delivery service — background send logic shared between the
marketing_campaigns router and the automation engine.

Extracted from the router to fix the service→router import violation in
automation_engine.py.
"""

import asyncio
import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import build_unsubscribe_url, send_email
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


async def _send_campaign_background(
    campaign_id: str,
    tenant_id: str,
    leads: list[dict],
    campaign: dict,
) -> None:
    """Background task: send a campaign to all matched leads and update DB with results.

    Runs after the HTTP handler has already returned. On any unhandled error the
    campaign status is set to 'failed' so the dashboard never shows a stuck 'sending'
    state.
    """
    try:
        db = get_service_supabase()
        total_sent = 0
        total_failed = 0
        campaign_type = campaign["type"]
        campaign_send_records = []

        for i, lead in enumerate(leads):
            lead_id = lead["id"]
            send_status = "failed"
            recipient = ""

            # Yield control every 10 sends to prevent event loop starvation
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(0)

            try:
                if campaign_type == "email":
                    recipient = lead.get("email", "")
                    if not recipient:
                        continue

                    unsub_url = build_unsubscribe_url(lead_id, tenant_id)
                    result = await send_email(
                        to=recipient,
                        subject=campaign.get("subject", ""),
                        body_html=campaign["body"],
                        tenant_id=tenant_id,
                        unsubscribe_url=unsub_url,
                        lead_id=lead_id,
                    )
                    if result.get("success"):
                        send_status = "sent"
                        total_sent += 1
                    else:
                        total_failed += 1
                        logger.warning(
                            "Campaign email failed for lead %s: %s",
                            lead_id,
                            result.get("detail"),
                        )

                elif campaign_type == "sms":
                    recipient = lead.get("phone", "")
                    if not recipient:
                        continue

                    success = await send_sms(to=recipient, body=campaign["body"])
                    if success:
                        send_status = "sent"
                        total_sent += 1
                    else:
                        total_failed += 1
                        logger.warning("Campaign SMS failed for lead %s", lead_id)

            except Exception:
                total_failed += 1
                logger.exception("Failed to send campaign to lead %s", lead_id)

            # Collect the send record for batch insert
            campaign_send_records.append(
                {
                    "campaign_id": campaign_id,
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "channel": campaign_type,
                    "recipient": recipient,
                    "status": send_status,
                }
            )

        # Batch-insert all campaign_sends at once (avoids N+1 queries)
        if campaign_send_records:
            try:
                db.table("campaign_sends").insert(campaign_send_records).execute()
            except Exception:
                logger.exception(
                    "Failed to batch-insert campaign sends for campaign %s", campaign_id
                )

        # Update campaign with final results
        final_status = "sent" if total_sent > 0 else "failed"
        try:
            db.table("marketing_campaigns").update(
                {
                    "status": final_status,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "total_recipients": len(leads),
                    "total_sent": total_sent,
                }
            ).eq("id", campaign_id).execute()
            logger.info(
                "Campaign %s completed: status=%s sent=%d failed=%d",
                campaign_id,
                final_status,
                total_sent,
                total_failed,
            )
        except Exception:
            logger.exception(
                "Failed to update final status for campaign %s (sent=%d, failed=%d)",
                campaign_id,
                total_sent,
                total_failed,
            )

    except Exception:
        logger.exception(
            "Unhandled error in background send for campaign %s — marking as failed",
            campaign_id,
        )
        try:
            db_bg = get_service_supabase()
            db_bg.table("marketing_campaigns").update(
                {
                    "status": "failed",
                }
            ).eq("id", campaign_id).execute()
        except Exception:
            logger.exception(
                "Failed to mark campaign %s as failed after background error",
                campaign_id,
            )
