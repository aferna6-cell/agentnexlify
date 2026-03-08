"""SMS endpoints — send SMS from CRM."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.sms_rate_limiter import check_sms_rate_limit, increment_sms_count
from backend.services.twilio_service import send_sms

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
    plan = claims.get("plan", "free")

    if not check_sms_rate_limit(tenant_id, plan):
        raise HTTPException(status_code=429, detail="Daily SMS limit reached")

    db = get_supabase()

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
