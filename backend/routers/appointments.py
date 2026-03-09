"""Appointment booking endpoints — availability config, slot queries, booking."""


import asyncio
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.models.schemas import (
    AppointmentListResponse,
    AppointmentUpdateRequest,
    AvailabilityConfigRequest,
    AvailabilityConfigResponse,
    AvailableSlotsResponse,
    BookAppointmentRequest,
    BookAppointmentResponse,
)
from backend.services.automation_engine import trigger_sequence
from backend.services.booking import (
    cancel_appointment,
    create_appointment,
    generate_available_slots,
    get_business_hours,
    list_appointments,
    update_appointment,
    upsert_business_hours,
)

from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

_JWT_ALGORITHM = "HS256"


# ── Auth helpers ──────────────────────────────────────────────

def _get_current_tenant(authorization: str = Header(...)) -> dict:
    """Extract tenant claims from Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    from jose import JWTError, jwt
    from backend.config import settings
    try:
        return jwt.decode(
            authorization.removeprefix("Bearer ").strip(),
            settings.api_secret_key,
            algorithms=[_JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _get_widget_config(api_key: str) -> dict:
    db = get_supabase()
    result = db.table("widget_configs").select("*").eq("api_key", api_key).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return result.data[0]


# ── Availability endpoints (JWT-protected) ────────────────────


@router.get("/availability/{tenant_id}", response_model=AvailabilityConfigResponse)
async def get_availability(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Get business hours configuration."""
    _verify_tenant(claims, tenant_id)
    config = get_business_hours(tenant_id)
    if not config:
        # Return defaults
        return AvailabilityConfigResponse(
            timezone="America/New_York",
            hours={
                "monday":    {"enabled": True, "start": "09:00", "end": "17:00"},
                "tuesday":   {"enabled": True, "start": "09:00", "end": "17:00"},
                "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "thursday":  {"enabled": True, "start": "09:00", "end": "17:00"},
                "friday":    {"enabled": True, "start": "09:00", "end": "17:00"},
                "saturday":  {"enabled": False, "start": "09:00", "end": "17:00"},
                "sunday":    {"enabled": False, "start": "09:00", "end": "17:00"},
            },
            slot_duration_minutes=30,
            buffer_minutes=0,
            max_advance_days=30,
        )
    return AvailabilityConfigResponse(
        timezone=config["timezone"],
        hours=config["hours"],
        slot_duration_minutes=config["slot_duration_minutes"],
        buffer_minutes=config["buffer_minutes"],
        max_advance_days=config["max_advance_days"],
    )


@router.put("/availability/{tenant_id}", response_model=AvailabilityConfigResponse)
async def set_availability(
    tenant_id: str,
    req: AvailabilityConfigRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Create or update business hours configuration."""
    _verify_tenant(claims, tenant_id)

    data = req.model_dump(exclude_none=True)
    # Convert DayHours models to dicts
    if "hours" in data and data["hours"]:
        data["hours"] = {k: (v if isinstance(v, dict) else v.model_dump()) for k, v in req.hours.items()}

    config = upsert_business_hours(tenant_id, data)
    return AvailabilityConfigResponse(
        timezone=config["timezone"],
        hours=config["hours"],
        slot_duration_minutes=config["slot_duration_minutes"],
        buffer_minutes=config["buffer_minutes"],
        max_advance_days=config["max_advance_days"],
    )


# ── Public endpoints (API key auth) ──────────────────────────


@router.get("/slots/{tenant_id}", response_model=AvailableSlotsResponse)
@limiter.limit("60/minute")
async def get_slots(
    request: Request,
    tenant_id: str,
    target_date: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    api_key: str = Query(..., description="Widget API key"),
):
    """Get available appointment slots for a date. Public endpoint (API key auth)."""
    widget = _get_widget_config(api_key)
    if widget["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="API key mismatch")

    try:
        parsed_date = date_type.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    config = get_business_hours(tenant_id)
    tz = config["timezone"] if config else "America/New_York"

    slots = generate_available_slots(tenant_id, parsed_date)

    return AvailableSlotsResponse(
        date=target_date,
        timezone=tz,
        slots=slots,
    )


@router.post("/{tenant_id}", response_model=BookAppointmentResponse)
@limiter.limit("10/minute")
async def book_appointment(request: Request, tenant_id: str, req: BookAppointmentRequest):
    """Book an appointment. Public endpoint (API key auth via body)."""
    widget = _get_widget_config(req.api_key)
    if widget["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="API key mismatch")

    try:
        appointment = create_appointment(
            tenant_id=tenant_id,
            customer_name=req.customer_name,
            customer_email=req.customer_email,
            customer_phone=req.customer_phone,
            start_time=req.start_utc,
            end_time=req.end_utc,
            notes=req.notes,
        )
    except Exception as exc:
        err_msg = str(exc)
        if "exclusion" in err_msg.lower() or "conflicting" in err_msg.lower():
            raise HTTPException(status_code=409, detail="This time slot is no longer available")
        logger.exception("Failed to create appointment for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create appointment")

    fire_event_background(tenant_id, "appointment.booked", {
        "appointment_id": appointment["id"],
        "customer_name": appointment["customer_name"],
        "customer_email": appointment["customer_email"],
        "start_time": appointment["start_time"],
        "end_time": appointment["end_time"],
    })

    return BookAppointmentResponse(
        id=appointment["id"],
        start_time=appointment["start_time"],
        end_time=appointment["end_time"],
        status=appointment["status"],
        customer_name=appointment["customer_name"],
        customer_email=appointment["customer_email"],
    )


# ── Dashboard endpoints (JWT-protected) ───────────────────────


@router.get("/{tenant_id}", response_model=AppointmentListResponse)
async def get_appointments(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    status: str | None = Query(None),
):
    """List appointments with optional filters."""
    _verify_tenant(claims, tenant_id)
    appointments = list_appointments(tenant_id, start_date, end_date, status)
    return AppointmentListResponse(appointments=appointments)


@router.patch("/{tenant_id}/{appointment_id}")
async def patch_appointment(
    tenant_id: str,
    appointment_id: str,
    req: AppointmentUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update appointment status, notes, or reschedule."""
    _verify_tenant(claims, tenant_id)
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = update_appointment(tenant_id, appointment_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Fire automation trigger when appointment is completed
    if data.get("status") == "completed" and updated.get("lead_id"):
        asyncio.create_task(
            trigger_sequence(
                tenant_id, updated["lead_id"], "appointment_completed",
                {"appointment_id": appointment_id},
            )
        )

    return updated


@router.delete("/{tenant_id}/{appointment_id}")
async def delete_appointment(
    tenant_id: str,
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Cancel an appointment (soft delete)."""
    _verify_tenant(claims, tenant_id)
    result = cancel_appointment(tenant_id, appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    fire_event_background(tenant_id, "appointment.cancelled", {
        "appointment_id": appointment_id,
    })

    return {"status": "cancelled", "id": appointment_id}
