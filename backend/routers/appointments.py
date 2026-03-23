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
    RecurrenceRequest,
)
from backend.services.automation_engine import trigger_sequence
from backend.services.booking import (
    cancel_appointment,
    create_appointment,
    create_recurring_series,
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
    config = get_business_hours(tenant_id)
    tz = config["timezone"] if config else "America/New_York"
    return AppointmentListResponse(appointments=appointments, timezone=tz)


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


@router.post("/{tenant_id}/{appointment_id}/check-in")
async def check_in_appointment(
    tenant_id: str,
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Mark a customer as checked in for their appointment.

    Sets status to 'checked_in' and records check-in time in notes.
    Only works for 'confirmed' appointments. Prevents no-show auto-detection
    since the customer has arrived.
    """
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Fetch the appointment
    result = db.table("appointments").select("*").eq("id", appointment_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment = result.data[0]
    current_status = appointment.get("status")

    if current_status not in ("confirmed", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot check in an appointment with status '{current_status}'. Must be 'confirmed' or 'pending'.",
        )

    from datetime import datetime, timezone
    check_in_time = datetime.now(timezone.utc).isoformat()

    # Update status and record check-in time
    existing_notes = appointment.get("notes") or ""
    check_in_note = f"[Checked in at {check_in_time}]"
    updated_notes = f"{existing_notes}\n{check_in_note}".strip()

    update_data = {
        "status": "checked_in",
        "notes": updated_notes,
        "updated_at": check_in_time,
    }

    db.table("appointments").update(update_data).eq("id", appointment_id).execute()

    # Log activity
    try:
        customer_name = appointment.get("customer_name") or "Customer"
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "lead_id": appointment.get("lead_id"),
            "activity_type": "appointment_check_in",
            "description": f"{customer_name} checked in for appointment",
        }).execute()
    except Exception:
        logger.warning("Failed to log check-in activity for appointment %s", appointment_id, exc_info=True)

    # Fire webhook
    fire_event_background(tenant_id, "appointment.checked_in", {
        "appointment_id": appointment_id,
        "customer_name": appointment.get("customer_name") or "",
        "check_in_time": check_in_time,
    })

    return {
        "id": appointment_id,
        "status": "checked_in",
        "check_in_time": check_in_time,
        "message": f"{appointment.get('customer_name') or 'Customer'} has been checked in.",
    }


@router.post("/{tenant_id}/{appointment_id}/reschedule")
async def reschedule_appointment(
    tenant_id: str,
    appointment_id: str,
    req: AppointmentUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Reschedule an appointment to a new time.

    Preserves the lead link, sends notification emails/SMS to the customer,
    logs the change in activity_log, and fires a webhook event.
    """
    _verify_tenant(claims, tenant_id)

    if not req.start_time or not req.end_time:
        raise HTTPException(status_code=400, detail="start_time and end_time are required for rescheduling")

    db = get_supabase()

    # Fetch existing appointment
    result = db.table("appointments").select("*").eq("id", appointment_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment = result.data[0]
    old_start = appointment.get("start_time", "")
    old_end = appointment.get("end_time", "")
    customer_name = appointment.get("customer_name") or "Customer"
    customer_email = appointment.get("customer_email")
    customer_phone = appointment.get("customer_phone")

    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc).isoformat()

    # Update the appointment
    update_data = {
        "start_time": req.start_time,
        "end_time": req.end_time,
        "status": "confirmed",  # Reset to confirmed on reschedule
        "updated_at": now,
    }
    if req.notes:
        existing_notes = appointment.get("notes") or ""
        update_data["notes"] = f"{existing_notes}\n[Rescheduled at {now}]".strip()

    db.table("appointments").update(update_data).eq("id", appointment_id).execute()

    # Log activity
    try:
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "lead_id": appointment.get("lead_id"),
            "activity_type": "appointment_rescheduled",
            "description": f"Appointment for {customer_name} rescheduled from {old_start} to {req.start_time}",
        }).execute()
    except Exception:
        logger.warning("Failed to log reschedule activity for appointment %s", appointment_id, exc_info=True)

    # Send notification email to customer
    if customer_email:
        try:
            tenant_result = db.table("tenants").select("business_name").eq("id", tenant_id).execute()
            biz_name = "the business"
            if tenant_result.data:
                biz_name = tenant_result.data[0].get("business_name") or "the business"

            from backend.services.email_sender import send_email
            new_dt = datetime.fromisoformat(req.start_time)
            formatted_time = new_dt.strftime("%A, %B %d at %I:%M %p")

            send_email(
                to=customer_email,
                subject=f"Your appointment with {biz_name} has been rescheduled",
                html=f"""
                <h2>Appointment Rescheduled</h2>
                <p>Hi {customer_name},</p>
                <p>Your appointment with <strong>{biz_name}</strong> has been rescheduled to:</p>
                <p style="font-size:18px;font-weight:bold;color:#2563eb;margin:16px 0;">{formatted_time}</p>
                <p>If this time doesn't work for you, please contact us to find a better time.</p>
                <p style="color:#666;margin-top:24px;">— {biz_name}</p>
                """,
            )
        except Exception:
            logger.warning("Failed to send reschedule email for appointment %s", appointment_id, exc_info=True)

    # Send SMS notification
    if customer_phone:
        try:
            from backend.services.sms_sender import send_sms
            tenant_result = db.table("tenants").select("business_name").eq("id", tenant_id).execute()
            biz_name = "us"
            if tenant_result.data:
                biz_name = tenant_result.data[0].get("business_name") or "us"

            new_dt = datetime.fromisoformat(req.start_time)
            formatted_time = new_dt.strftime("%a %b %d at %I:%M %p")
            send_sms(customer_phone, f"Hi {customer_name}, your appointment with {biz_name} has been rescheduled to {formatted_time}. Reply if you need to change.")
        except Exception:
            logger.warning("Failed to send reschedule SMS for appointment %s", appointment_id, exc_info=True)

    # Fire webhook
    fire_event_background(tenant_id, "appointment.rescheduled", {
        "appointment_id": appointment_id,
        "customer_name": customer_name,
        "old_start_time": old_start,
        "new_start_time": req.start_time,
        "new_end_time": req.end_time,
    })

    return {
        "id": appointment_id,
        "status": "confirmed",
        "start_time": req.start_time,
        "end_time": req.end_time,
        "message": f"Appointment for {customer_name} has been rescheduled.",
    }


@router.post("/{tenant_id}/{appointment_id}/recur")
async def set_recurrence(
    tenant_id: str,
    appointment_id: str,
    req: RecurrenceRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Set up recurring schedule for an appointment. Generates future instances."""
    _verify_tenant(claims, tenant_id)
    created = create_recurring_series(tenant_id, appointment_id, req.rule, req.end_date)
    return {
        "parent_id": appointment_id,
        "rule": req.rule,
        "end_date": req.end_date,
        "instances_created": len(created),
    }


@router.delete("/{tenant_id}/{appointment_id}")
async def delete_appointment(
    tenant_id: str,
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Cancel an appointment (soft delete)."""
    _verify_tenant(claims, tenant_id)

    # Fetch appointment details before cancelling (for webhook payload)
    db = get_supabase()
    appt_result = (
        db.table("appointments")
        .select("customer_name, customer_email, start_time, end_time")
        .eq("id", appointment_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    appt_data = appt_result.data[0] if appt_result.data else {}

    result = cancel_appointment(tenant_id, appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    fire_event_background(tenant_id, "appointment.cancelled", {
        "appointment_id": appointment_id,
        "customer_name": appt_data.get("customer_name"),
        "customer_email": appt_data.get("customer_email"),
        "start_time": appt_data.get("start_time"),
        "end_time": appt_data.get("end_time"),
    })

    # Notify waitlisted customers about the opened slot
    if appt_data.get("start_time"):
        try:
            from backend.routers.waitlist import notify_waitlist_for_cancellation
            cancelled_date = appt_data["start_time"][:10] if "T" in appt_data["start_time"] else appt_data["start_time"]
            asyncio.create_task(asyncio.to_thread(
                notify_waitlist_for_cancellation,
                tenant_id,
                cancelled_date,
                appt_data.get("start_time", ""),
                appt_data.get("end_time", ""),
            ))
        except Exception:
            logger.warning("Failed to trigger waitlist notifications for cancelled appointment %s", appointment_id, exc_info=True)

    return {"status": "cancelled", "id": appointment_id}


# ---------------------------------------------------------------------------
# Service Types — define services with custom durations for booking
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class ServiceTypeCreate(BaseModel):
    name: str = Field(..., max_length=200)
    duration_minutes: int = Field(30, ge=15, le=480)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, ge=0)


class ServiceTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    duration_minutes: int | None = Field(None, ge=15, le=480)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, ge=0)
    is_active: bool | None = None


@router.get("/{tenant_id}/service-types")
async def list_service_types(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List service types for appointment booking."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_supabase()
    result = (
        db.table("service_types")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    return result.data or []


@router.post("/{tenant_id}/service-types")
async def create_service_type(
    tenant_id: str,
    req: ServiceTypeCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new service type."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": req.name,
        "duration_minutes": req.duration_minutes,
    }
    if req.description:
        data["description"] = req.description
    if req.price is not None:
        data["price"] = float(req.price)
    result = db.table("service_types").insert(data).execute()
    return result.data[0] if result.data else {}


@router.put("/{tenant_id}/service-types/{service_id}")
async def update_service_type(
    tenant_id: str,
    service_id: str,
    req: ServiceTypeUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a service type."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updates = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_supabase()
    result = db.table("service_types").update(updates).eq("id", service_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Service type not found")
    return result.data[0]


@router.delete("/{tenant_id}/service-types/{service_id}")
async def delete_service_type(
    tenant_id: str,
    service_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Soft-delete a service type."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_supabase()
    result = (
        db.table("service_types")
        .update({"is_active": False})
        .eq("id", service_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Service type not found")
    return {"deleted": True}


@router.get("/public/{tenant_id}/service-types")
@limiter.limit("60/minute")
async def public_service_types(request: Request, tenant_id: str, api_key: str = Query(...)):
    """Public endpoint: list active service types for widget booking."""
    db = get_supabase()
    # Verify API key
    wc = db.table("widget_configs").select("tenant_id").eq("api_key", api_key).eq("tenant_id", tenant_id).limit(1).execute()
    if not wc.data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    result = (
        db.table("service_types")
        .select("id, name, duration_minutes, description, price")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    return result.data or []
