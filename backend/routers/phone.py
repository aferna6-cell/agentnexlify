"""Business Phone Number Provisioning — search, buy, and release Twilio phone numbers.

POST /api/v1/phone/{tenant_id}/provision — Buy and configure a local number
GET  /api/v1/phone/{tenant_id}/available — Search available numbers
DELETE /api/v1/phone/{tenant_id}/release — Release a provisioned number
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/phone", tags=["phone"])

# Twilio API base
_TWILIO_BASE = "https://api.twilio.com/2010-04-01/Accounts"

# Backend base URL for webhook configuration
_BACKEND_BASE = "https://agentnexlify-production.up.railway.app"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AvailableNumber(BaseModel):
    phone_number: str
    friendly_name: str
    locality: str | None = None
    region: str | None = None
    capabilities: dict[str, bool] = Field(default_factory=dict)


class AvailableNumbersResponse(BaseModel):
    numbers: list[AvailableNumber]
    count: int


class ProvisionRequest(BaseModel):
    area_code: str | None = Field(None, max_length=10)
    city: str | None = Field(None, max_length=100)


class ProvisionResponse(BaseModel):
    phone_number: str
    friendly_name: str
    sid: str
    voice_webhook: str
    sms_webhook: str
    message: str


class ReleaseResponse(BaseModel):
    released: bool
    phone_number: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _twilio_auth() -> tuple[str, str]:
    """Return Twilio basic auth tuple."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise HTTPException(
            status_code=503,
            detail="Twilio is not configured. Contact support.",
        )
    return (settings.twilio_account_sid, settings.twilio_auth_token)


def _parse_capabilities(caps: dict[str, Any]) -> dict[str, bool]:
    """Parse Twilio capabilities response into a clean dict."""
    return {
        "voice": caps.get("voice", False),
        "sms": caps.get("SMS", caps.get("sms", False)),
        "mms": caps.get("MMS", caps.get("mms", False)),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/available", response_model=AvailableNumbersResponse)
@limiter.limit("10/minute")
async def search_available_numbers(
    request: Request,
    tenant_id: str,
    area_code: str | None = Query(None, max_length=10),
    city: str | None = Query(None, max_length=100),
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Search available local phone numbers without buying them."""
    _verify_tenant(claims, tenant_id)
    auth = _twilio_auth()

    url = (
        f"{_TWILIO_BASE}/{settings.twilio_account_sid}"
        f"/AvailablePhoneNumbers/US/Local.json"
    )

    params: dict[str, Any] = {"PageSize": 5}
    if area_code:
        params["AreaCode"] = area_code
    if city:
        params["InLocality"] = city

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, auth=auth)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Twilio available numbers search failed: status=%d body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to search available numbers. Please try again.",
        )
    except Exception:
        logger.exception("Twilio available numbers search error")
        raise HTTPException(
            status_code=502,
            detail="Failed to connect to phone number provider.",
        )

    available = data.get("available_phone_numbers", [])
    numbers = []
    for num in available[:5]:
        numbers.append(
            AvailableNumber(
                phone_number=num.get("phone_number", ""),
                friendly_name=num.get("friendly_name", ""),
                locality=num.get("locality"),
                region=num.get("region"),
                capabilities=_parse_capabilities(num.get("capabilities", {})),
            )
        )

    return AvailableNumbersResponse(numbers=numbers, count=len(numbers))


@router.post("/{tenant_id}/provision", response_model=ProvisionResponse)
@limiter.limit("3/minute")
async def provision_number(
    request: Request,
    tenant_id: str,
    req: ProvisionRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Provision a Twilio phone number for the tenant.

    1. Search for available local numbers
    2. Buy the first available number
    3. Configure voice and SMS webhooks
    4. Store on tenant as notification_phone
    """
    _verify_tenant(claims, tenant_id)
    auth = _twilio_auth()
    db = get_supabase()

    # Check if tenant already has a provisioned number
    tenant_result = (
        db.table("tenants")
        .select("id, notification_phone")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant_result.data[0].get("notification_phone"):
        raise HTTPException(
            status_code=409,
            detail="Tenant already has a provisioned number. Release it first.",
        )

    # Step 1: Search for available numbers
    search_url = (
        f"{_TWILIO_BASE}/{settings.twilio_account_sid}"
        f"/AvailablePhoneNumbers/US/Local.json"
    )
    search_params: dict[str, Any] = {"PageSize": 1}
    if req.area_code:
        search_params["AreaCode"] = req.area_code
    if req.city:
        search_params["InLocality"] = req.city

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            search_resp = await client.get(search_url, params=search_params, auth=auth)
            search_resp.raise_for_status()
            search_data = search_resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Twilio number search failed: status=%d body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to search for available numbers.",
        )
    except Exception:
        logger.exception("Twilio number search error")
        raise HTTPException(status_code=502, detail="Failed to connect to Twilio.")

    available = search_data.get("available_phone_numbers", [])
    if not available:
        raise HTTPException(
            status_code=404,
            detail="No available phone numbers found for the specified area. Try a different area code or city.",
        )

    phone_number = available[0]["phone_number"]

    # Step 2: Buy the number
    buy_url = (
        f"{_TWILIO_BASE}/{settings.twilio_account_sid}"
        f"/IncomingPhoneNumbers.json"
    )

    voice_webhook = f"{_BACKEND_BASE}/api/v1/calls/voice/incoming"
    sms_webhook = f"{_BACKEND_BASE}/api/v1/twilio/sms-reply"

    buy_data = {
        "PhoneNumber": phone_number,
        "VoiceUrl": voice_webhook,
        "VoiceMethod": "POST",
        "SmsUrl": sms_webhook,
        "SmsMethod": "POST",
        "FriendlyName": f"AgentNexLiFy - {tenant_id[:8]}",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            buy_resp = await client.post(buy_url, data=buy_data, auth=auth)
            buy_resp.raise_for_status()
            bought = buy_resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Twilio number purchase failed: status=%d body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to purchase the phone number. Please try again.",
        )
    except Exception:
        logger.exception("Twilio number purchase error")
        raise HTTPException(status_code=502, detail="Failed to provision number.")

    purchased_number = bought.get("phone_number", phone_number)
    number_sid = bought.get("sid", "")
    friendly_name = bought.get("friendly_name", purchased_number)

    # Step 3: Store the number on the tenant
    try:
        db.table("tenants").update({
            "notification_phone": purchased_number,
            "sms_notifications_enabled": True,
        }).eq("id", tenant_id).execute()
    except Exception:
        logger.exception(
            "Failed to store provisioned number %s for tenant %s",
            purchased_number,
            tenant_id,
        )
        # The number was already purchased -- log this as critical
        # so it can be manually reconciled
        raise HTTPException(
            status_code=500,
            detail=(
                f"Number {purchased_number} was purchased but failed to save. "
                "Contact support with this number."
            ),
        )

    logger.info(
        "Provisioned phone number %s (SID=%s) for tenant %s",
        purchased_number,
        number_sid,
        tenant_id,
    )

    return ProvisionResponse(
        phone_number=purchased_number,
        friendly_name=friendly_name,
        sid=number_sid,
        voice_webhook=voice_webhook,
        sms_webhook=sms_webhook,
        message=f"Phone number {purchased_number} provisioned and configured.",
    )


@router.delete("/{tenant_id}/release", response_model=ReleaseResponse)
@limiter.limit("3/minute")
async def release_number(
    request: Request,
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Release a provisioned phone number.

    1. Look up the tenant's notification_phone
    2. Find the number SID via Twilio API
    3. Release the number
    4. Clear notification_phone on tenant
    """
    _verify_tenant(claims, tenant_id)
    auth = _twilio_auth()
    db = get_supabase()

    # Get tenant's current number
    tenant_result = (
        db.table("tenants")
        .select("id, notification_phone")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    current_number = tenant_result.data[0].get("notification_phone")
    if not current_number:
        raise HTTPException(
            status_code=404,
            detail="No phone number is provisioned for this tenant.",
        )

    # Find the number SID via Twilio
    list_url = (
        f"{_TWILIO_BASE}/{settings.twilio_account_sid}"
        f"/IncomingPhoneNumbers.json"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            list_resp = await client.get(
                list_url,
                params={"PhoneNumber": current_number},
                auth=auth,
            )
            list_resp.raise_for_status()
            list_data = list_resp.json()
    except Exception:
        logger.exception("Failed to look up Twilio number SID for %s", current_number)
        raise HTTPException(
            status_code=502,
            detail="Failed to look up phone number with provider.",
        )

    numbers = list_data.get("incoming_phone_numbers", [])
    if not numbers:
        # Number not found in Twilio -- still clear it from tenant
        logger.warning(
            "Number %s not found in Twilio for tenant %s -- clearing from DB anyway",
            current_number,
            tenant_id,
        )
        try:
            db.table("tenants").update({
                "notification_phone": None,
            }).eq("id", tenant_id).execute()
        except Exception:
            logger.exception("Failed to clear notification_phone for tenant %s", tenant_id)
        return ReleaseResponse(
            released=True,
            phone_number=current_number,
            message="Number was not found with provider but has been cleared from your account.",
        )

    number_sid = numbers[0]["sid"]

    # Release the number via Twilio
    release_url = (
        f"{_TWILIO_BASE}/{settings.twilio_account_sid}"
        f"/IncomingPhoneNumbers/{number_sid}.json"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            del_resp = await client.delete(release_url, auth=auth)
            del_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Twilio number release failed: status=%d body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to release the phone number. Please try again.",
        )
    except Exception:
        logger.exception("Twilio number release error for %s", current_number)
        raise HTTPException(status_code=502, detail="Failed to release number.")

    # Clear the number from the tenant
    try:
        db.table("tenants").update({
            "notification_phone": None,
        }).eq("id", tenant_id).execute()
    except Exception:
        logger.exception(
            "Number %s released from Twilio but failed to clear from tenant %s",
            current_number,
            tenant_id,
        )

    logger.info(
        "Released phone number %s (SID=%s) for tenant %s",
        current_number,
        number_sid,
        tenant_id,
    )

    return ReleaseResponse(
        released=True,
        phone_number=current_number,
        message=f"Phone number {current_number} has been released.",
    )
