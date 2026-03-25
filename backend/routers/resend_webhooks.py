"""Resend webhook endpoint for email event handling (bounces, complaints).

Handles email.bounced and email.complained events from Resend to mark
lead emails as invalid and prevent future sends.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class ResendWebhookPayload(BaseModel):
    type: str
    data: dict


@router.post("/resend")
async def resend_webhook(request: Request):
    """Handle Resend webhook events.

    Supported events:
    - email.bounced: marks lead's email as bounced
    - email.complained: marks lead's email as bounced (spam complaint)
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = body.get("type", "")
    event_data = body.get("data", {})

    logger.info("Resend webhook received: type=%s", event_type)

    if event_type in ("email.bounced", "email.complained"):
        await _handle_bounce(event_data, event_type)
    else:
        logger.debug("Unhandled Resend event: %s", event_type)

    return {"status": "ok"}


async def _handle_bounce(event_data: dict, event_type: str) -> None:
    """Mark the lead's email as bounced so future sends are skipped.

    Looks up the lead by email address (from the 'to' field in the event).
    Sets email_bounced=true and email_bounced_at for all matching leads.
    """
    to_addresses = event_data.get("to", [])
    if isinstance(to_addresses, str):
        to_addresses = [to_addresses]

    if not to_addresses:
        logger.warning("Resend bounce event with no 'to' addresses")
        return

    db = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    for email_addr in to_addresses:
        email_addr = email_addr.strip().lower()
        if not email_addr:
            continue

        try:
            # Find all leads with this email and mark as bounced
            result = (
                db.table("leads")
                .update({
                    "email_bounced": True,
                    "email_bounced_at": now_iso,
                })
                .ilike("email", email_addr)
                .execute()
            )

            updated_count = len(result.data) if result.data else 0
            if updated_count > 0:
                logger.info(
                    "Marked %d lead(s) as email_bounced for %s (event: %s)",
                    updated_count, email_addr, event_type,
                )
            else:
                logger.debug(
                    "No leads found with email %s for bounce event", email_addr
                )
        except Exception:
            logger.exception(
                "Failed to mark email as bounced for %s", email_addr
            )
