"""Automation management + Twilio missed-call / SMS-reply webhooks.

Production webhook URLs must be HTTPS. Use ngrok for local development:
    ngrok http 8000
Then set Twilio voice webhook (HTTP POST, on "no answer") to:
    https://<ngrok-id>.ngrok-free.app/api/v1/twilio/missed-call
And messaging webhook (HTTP POST) to:
    https://<ngrok-id>.ngrok-free.app/api/v1/twilio/sms-reply
"""


import logging

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import PlainTextResponse

from backend.models.database import get_supabase
from backend.services.activity import log_activity
from backend.services.twilio_service import (
    format_textback_message,
    looks_like_booking_request,
    send_sms,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["automations"])

DEFAULT_TEXTBACK_TEMPLATE = (
    "Hi! Sorry we missed your call at {business_name}. "
    "How can we help? Reply here and we'll get back to you right away!"
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _lookup_tenant_by_twilio_number(phone: str) -> dict | None:
    """Find a tenant whose widget_configs row carries this Twilio number.

    We store the tenant's Twilio number in widget_configs.allowed_domains
    as a pragmatic short-term solution, but the cleaner path is a dedicated
    `twilio_phone` column on tenants.  For now we look up tenants.phone.
    """
    db = get_supabase()
    result = (
        db.table("tenants")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _get_automation(tenant_id: str, automation_type: str) -> dict | None:
    """Fetch a single automation by tenant + type."""
    db = get_supabase()
    result = (
        db.table("automations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("type", automation_type)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ------------------------------------------------------------------
# Twilio Webhooks
# ------------------------------------------------------------------

@router.post("/twilio/missed-call", response_class=PlainTextResponse)
async def twilio_missed_call(
    CallSid: str = Form(...),
    To: str = Form(...),
    From: str = Form(...),
    CallStatus: str = Form("no-answer"),
):
    """Twilio calls this when a call is not answered.

    1. Look up tenant by the To phone number.
    2. Check if missed_call_textback automation is enabled.
    3. Send SMS to the caller with the configured template.
    4. Create a lead record.
    5. Increment automation runs_total.
    6. Return empty TwiML.
    """
    db = get_supabase()

    # 1. Tenant lookup
    tenant = _lookup_tenant_by_twilio_number(To)
    if not tenant:
        logger.warning("Missed call on unmapped number %s (CallSid=%s)", To, CallSid)
        return "<Response></Response>"

    tenant_id = tenant["id"]

    # 2. Check automation
    automation = _get_automation(tenant_id, "missed_call_textback")
    if not automation or not automation.get("is_enabled"):
        logger.info("missed_call_textback disabled for tenant %s", tenant_id)
        return "<Response></Response>"

    # 3. Send SMS
    config = automation.get("config") or {}
    template = config.get("message_template", DEFAULT_TEXTBACK_TEMPLATE)
    body = format_textback_message(template, tenant.get("business_name", "us"))

    await send_sms(to=From, body=body)

    # 4. Create lead (live schema: client_id, status, no source/notes columns)
    lead_result = db.table("leads").insert({
        "client_id": tenant_id,
        "phone": From,
        "status": "new",
        "conversation_summary": f"Missed call text-back sent (CallSid: {CallSid})",
    }).execute()

    if lead_result.data:
        log_activity(
            tenant_id=tenant_id,
            activity_type="lead_created",
            description=f"New lead from missed call: {From}",
            lead_id=lead_result.data[0]["id"],
            metadata={"source": "missed_call", "call_sid": CallSid},
        )
        log_activity(
            tenant_id=tenant_id,
            activity_type="automation_triggered",
            description="Missed call text-back sent",
            lead_id=lead_result.data[0]["id"],
            metadata={"automation": "missed_call_textback"},
        )

    # 5. Increment runs_total
    db.table("automations").update({
        "runs_total": automation["runs_total"] + 1,
    }).eq("id", automation["id"]).execute()

    logger.info("Missed-call text-back sent to %s for tenant %s", From, tenant_id)

    # 6. TwiML
    return "<Response></Response>"


@router.post("/twilio/sms-reply", response_class=PlainTextResponse)
async def twilio_sms_reply(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(""),
):
    """Twilio calls this when a customer replies to an automated SMS.

    1. Look up tenant by To number.
    2. Find the lead by caller phone.
    3. If message contains booking keywords, send booking link.
    4. Forward the reply to the business owner.
    """
    db = get_supabase()

    # 1. Tenant lookup
    tenant = _lookup_tenant_by_twilio_number(To)
    if not tenant:
        logger.warning("SMS reply on unmapped number %s", To)
        return "<Response></Response>"

    tenant_id = tenant["id"]

    # 2. Find lead
    lead_result = (
        db.table("leads")
        .select("*")
        .eq("client_id", tenant_id)
        .eq("phone", From)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    lead = lead_result.data[0] if lead_result.data else None

    if lead:
        # 3. Update lead conversation_summary with the reply
        existing_notes = lead.get("conversation_summary") or ""
        updated_notes = f"{existing_notes}\nCustomer reply: {Body}".strip()
        db.table("leads").update({"conversation_summary": updated_notes}).eq("id", lead["id"]).execute()

        log_activity(
            tenant_id=tenant_id,
            activity_type="message",
            description=f"SMS reply from {From}",
            lead_id=lead["id"],
            metadata={"source": "sms", "preview": Body[:100]},
        )

    # 4. Booking keyword detection
    if looks_like_booking_request(Body):
        automation = _get_automation(tenant_id, "missed_call_textback")
        config = (automation or {}).get("config") or {}
        booking_link = config.get("booking_link", "")

        if booking_link:
            await send_sms(
                to=From,
                body=f"Great! You can book an appointment here: {booking_link}",
            )

    # 5. Forward to business owner
    owner_phone = tenant.get("phone")
    if owner_phone and owner_phone != To:
        await send_sms(
            to=owner_phone,
            body=f"New reply from {From}: {Body}",
        )

    return "<Response></Response>"


# ------------------------------------------------------------------
# Automation CRUD
# ------------------------------------------------------------------

@router.get("/automations/{tenant_id}")
async def list_automations(tenant_id: str):
    """List all automations for a tenant."""
    db = get_supabase()
    result = (
        db.table("automations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return {"automations": result.data or []}


@router.post("/automations/{tenant_id}/{automation_id}/toggle")
async def toggle_automation(tenant_id: str, automation_id: str):
    """Enable or disable an automation."""
    db = get_supabase()
    result = (
        db.table("automations")
        .select("id, is_enabled")
        .eq("id", automation_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Automation not found")

    current = result.data[0]
    new_state = not current["is_enabled"]

    db.table("automations").update({
        "is_enabled": new_state,
    }).eq("id", automation_id).execute()

    return {"id": automation_id, "is_enabled": new_state}


@router.put("/automations/{tenant_id}/{automation_id}/config")
async def update_automation_config(tenant_id: str, automation_id: str, config: dict):
    """Update an automation's config JSON."""
    db = get_supabase()

    # Verify ownership
    result = (
        db.table("automations")
        .select("id")
        .eq("id", automation_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Automation not found")

    db.table("automations").update({
        "config": config,
    }).eq("id", automation_id).execute()

    return {"id": automation_id, "config": config}
