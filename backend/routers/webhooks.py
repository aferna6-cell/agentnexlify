"""Incoming webhooks — Twilio SMS, etc."""

import logging

from fastapi import APIRouter, Request, Form

from backend.models.database import get_supabase
from backend.services.claude_agent import run_agent
from backend.services.conversation import get_or_create_conversation
from backend.services.sms import send_sms
from backend.models.schemas import ClientRow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/twilio/sms")
async def twilio_sms_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
):
    """Handle incoming SMS via Twilio webhook.

    Maps the receiving phone number to a client, processes the message
    through the AI agent, and sends the reply back via SMS.
    """
    db = get_supabase()

    # Find the client by their Twilio phone number
    result = (
        db.table("clients")
        .select("*")
        .eq("notification_phone", To)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("SMS received on unmapped number: %s", To)
        return {"status": "ignored", "reason": "No client mapped to this number"}

    client = ClientRow(**result.data[0])

    # Use the sender's phone number as the session_id
    session_id = From.replace("+", "").strip()
    conversation = get_or_create_conversation(client.id, session_id, channel="sms")
    conversation_id = conversation["id"]

    reply = await run_agent(client, conversation_id, Body)

    # Send reply via SMS
    await send_sms(From, reply)

    # Return TwiML empty response (we already sent via API)
    return '<Response></Response>'
