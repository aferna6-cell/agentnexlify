"""SMS endpoints — send SMS from CRM."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sms", tags=["sms"])


class SendSmsRequest(BaseModel):
    lead_id: str
    phone: str
    message: str


class SendSmsResponse(BaseModel):
    success: bool
    detail: str


@router.post("/send", response_model=SendSmsResponse)
async def send_sms_endpoint(
    req: SendSmsRequest,
    claims: dict = Depends(_get_current_tenant),
):
    tenant_id = claims["tenant_id"]

    db = get_supabase()

    # Fetch live plan from DB (not JWT) for accurate rate limiting
    tenant_result = db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    plan = tenant_result.data[0]["plan"] if tenant_result.data else "free"

    if not check_sms_rate_limit(tenant_id, plan):
        raise HTTPException(status_code=429, detail="Daily SMS limit reached")

    # Verify lead belongs to tenant
    lead_result = (
        db.table("leads")
        .select("id")
        .eq("id", req.lead_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    success = await send_sms(to=req.phone, body=req.message)

    if success:
        increment_sms_count(tenant_id)
        log_activity(
            tenant_id=tenant_id,
            activity_type="sms_sent",
            description=f"SMS sent to {req.phone}",
            lead_id=req.lead_id,
            metadata={"phone": req.phone, "message": req.message[:200]},
        )
        return SendSmsResponse(success=True, detail="sent")

    return SendSmsResponse(success=False, detail="Failed to send SMS")


# ---------------------------------------------------------------------------
# Two-way SMS conversation endpoint
# ---------------------------------------------------------------------------

class InitiateSmsRequest(BaseModel):
    phone: str
    message: str


class InitiateSmsResponse(BaseModel):
    success: bool
    session_id: str


def _normalize_phone_for_session(phone: str) -> str:
    """Strip + and spaces from a phone number to form a session_id segment."""
    return re.sub(r"[\s+\-()]", "", phone)


def _get_or_create_sms_conversation(db, tenant_id: str, session_id: str) -> str:
    """Find or create a conversation row for the given SMS session. Returns conversation_id."""
    try:
        result = (
            db.table("conversations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception:
        logger.warning(
            "sms_send: conversations lookup failed for session %s, tenant %s",
            session_id,
            tenant_id,
            exc_info=True,
        )

    try:
        new_conv = (
            db.table("conversations")
            .insert({"tenant_id": tenant_id, "session_id": session_id})
            .execute()
        )
        if new_conv.data:
            return new_conv.data[0]["id"]
    except Exception:
        logger.warning(
            "sms_send: conversations insert failed for session %s, tenant %s",
            session_id,
            tenant_id,
            exc_info=True,
        )

    # Fallback: use session_id as stable identifier
    return session_id


@router.post("/{tenant_id}/send", response_model=InitiateSmsResponse)
async def initiate_sms_conversation(
    tenant_id: str,
    req: InitiateSmsRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Send an outbound SMS from the tenant's provisioned phone number.

    Stores the message in chat_messages, creates/finds the conversation
    record, and fires the conversation.message webhook.
    """
    # Verify the authenticated tenant matches the path parameter
    verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Load tenant — verify they have a provisioned Twilio number
    try:
        tenant_result = (
            db.table("tenants")
            .select("id, notification_phone, plan")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("sms_send: failed to load tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load tenant")

    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]
    from_number = tenant.get("notification_phone")
    if not from_number:
        raise HTTPException(
            status_code=422,
            detail=(
                "No provisioned phone number found. "
                "Go to Phone Settings to provision a number first."
            ),
        )

    # Derive session_id using the same sms_ prefix convention as twilio_webhooks.py
    normalized = _normalize_phone_for_session(req.phone)
    session_id = f"sms_{normalized}"

    # Find or create conversation record (conversations table uses tenant_id)
    conversation_id = _get_or_create_sms_conversation(db, tenant_id, session_id)

    # Store the outbound message in chat_messages (role=assistant: business is speaking)
    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": "assistant",
            "content": req.message,
        }).execute()
    except Exception:
        logger.exception(
            "sms_send: failed to store outbound message for tenant %s session %s",
            tenant_id,
            session_id,
        )
        # Don't abort — still attempt to send the SMS

    # Send the SMS via Twilio from the tenant's provisioned number
    success = await send_sms(to=req.phone, body=req.message, from_number=from_number)

    if not success:
        logger.error(
            "sms_send: Twilio send failed to %s for tenant %s",
            req.phone,
            tenant_id,
        )
        raise HTTPException(status_code=502, detail="Failed to send SMS via Twilio")

    logger.info(
        "sms_send: sent to %s from %s for tenant %s session %s",
        req.phone,
        from_number,
        tenant_id,
        session_id,
    )

    # Log activity
    log_activity(
        tenant_id=tenant_id,
        activity_type="sms_sent",
        description=f"Outbound SMS sent to {req.phone}",
        metadata={"phone": req.phone, "session_id": session_id, "message": req.message[:200]},
    )

    # Fire conversation.message webhook
    try:
        fire_event_background(tenant_id, "conversation.message", {
            "session_id": session_id,
            "conversation_id": conversation_id,
            "assistant_message": req.message[:500],
            "channel": "sms",
        })
    except Exception:
        logger.warning(
            "sms_send: fire_event_background failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    return InitiateSmsResponse(success=True, session_id=session_id)
