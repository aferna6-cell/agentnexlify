"""Appointment booking endpoints — availability config, slot queries, booking."""

import logging
from datetime import date as date_type

from backend.services.task_utils import safe_create_task

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body

from backend.limiter import limiter
from backend.models.database import get_service_supabase
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

from backend.dependencies import _get_current_tenant
from backend.services.webhook_dispatcher import fire_event_background
from backend.services.review_requester import create_review_request_draft

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


async def _draft_review_request(
    tenant_id: str, appointment_id: str, appointment: dict
) -> None:
    """Background coroutine: fetch tenant context, then file review-request draft.

    Fault-tolerant — errors are logged but never propagate.
    """
    try:
        db = get_service_supabase()
        tenant_row = (
            db.table("tenants")
            .select("business_name, google_review_link")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        tenant = tenant_row.data[0] if tenant_row.data else {}
        business_name = tenant.get("business_name") or ""
        google_review_link = tenant.get("google_review_link") or None

        await create_review_request_draft(
            db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
            lead_id=appointment.get("lead_id"),
            customer_name=appointment.get("customer_name") or "",
            customer_phone=appointment.get("customer_phone") or "",
            business_name=business_name,
            google_review_link=google_review_link,
        )
    except Exception:
        logger.warning(
            "_draft_review_request: unexpected error tenant=%s appointment=%s",
            tenant_id,
            appointment_id,
            exc_info=True,
        )


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _get_widget_config(api_key: str) -> dict:
    db = get_service_supabase()
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


@router.post("/slots/{tenant_id}", response_model=AvailableSlotsResponse)
@limiter.limit("60/minute")
async def get_slots_post(
    request: Request,
    tenant_id: str,
    target_date: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    api_key: str = Body(..., embed=True),
):
    """Get available appointment slots for a date. POST version to avoid API key in URL."""
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
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
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


from pydantic import BaseModel as _BaseModel


class _DashboardBookBody(_BaseModel):
    customer_name: str
    customer_email: str | None = None
    customer_phone: str | None = None
    start_time: str
    end_time: str
    notes: str | None = None
    status: str = "confirmed"


@router.post("/{tenant_id}/dashboard-book")
async def dashboard_book_appointment(
    tenant_id: str,
    req: _DashboardBookBody,
    claims: dict = Depends(_get_current_tenant),
):
    """Book an appointment from the dashboard (JWT-protected)."""
    _verify_tenant(claims, tenant_id)
    try:
        appointment = create_appointment(
            tenant_id=tenant_id,
            customer_name=req.customer_name,
            customer_email=req.customer_email,
            start_time=req.start_time,
            end_time=req.end_time,
            customer_phone=req.customer_phone,
            notes=req.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        err_msg = str(exc)
        if "exclusion" in err_msg.lower() or "conflicting" in err_msg.lower():
            raise HTTPException(status_code=409, detail="This time slot is no longer available")
        logger.exception("Failed to create appointment for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create appointment")

    fire_event_background(tenant_id, "appointment.booked", {
        "appointment_id": appointment["id"],
        "customer_name": appointment["customer_name"],
        "customer_email": appointment.get("customer_email"),
        "start_time": appointment["start_time"],
        "end_time": appointment["end_time"],
    })

    return appointment


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
        safe_create_task(
            trigger_sequence(
                tenant_id, updated["lead_id"], "appointment_completed",
                {"appointment_id": appointment_id},
            ),
            name="trigger_appointment_completed",
        )

    # File review-request draft whenever appointment is marked completed
    if data.get("status") == "completed":
        safe_create_task(
            _draft_review_request(tenant_id, appointment_id, updated),
            name="review_request_draft",
        )

    return updated


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
    db = get_service_supabase()
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
    db = get_service_supabase()
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
    db = get_service_supabase()
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
    db = get_service_supabase()
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
    db = get_service_supabase()
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
    db = get_service_supabase()
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


@router.get("/no-show-stats/{tenant_id}")
async def get_no_show_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get no-show statistics: total no-shows, no-show rate, and repeat offenders."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()

    # Get all completed + no_show appointments for rate calculation
    all_appts = (
        db.table("appointments")
        .select("id, status, customer_email, customer_name, lead_id")
        .eq("tenant_id", tenant_id)
        .in_("status", ["completed", "no_show"])
        .execute()
    )
    appts = all_appts.data or []

    total = len(appts)
    no_shows = [a for a in appts if a["status"] == "no_show"]
    no_show_count = len(no_shows)
    no_show_rate = round((no_show_count / total * 100) if total > 0 else 0, 1)

    # Find repeat offenders (2+ no-shows by email)
    email_counts = {}
    for a in no_shows:
        email = a.get("customer_email") or a.get("customer_name") or "unknown"
        email_counts[email] = email_counts.get(email, 0) + 1

    repeat_offenders = [
        {"customer": email, "no_show_count": count}
        for email, count in sorted(email_counts.items(), key=lambda x: -x[1])
        if count >= 2
    ][:10]  # Top 10

    return {
        "total_appointments": total,
        "no_show_count": no_show_count,
        "no_show_rate": no_show_rate,
        "repeat_offenders": repeat_offenders,
    }


@router.get("/{tenant_id}/ical")
async def ical_feed(
    tenant_id: str,
    key: str = Query(..., description="Widget API key for authentication"),
):
    """Public iCal/webcal feed of upcoming appointments. Authenticated via API key.

    Businesses can subscribe to this URL in Google Calendar or Apple Calendar
    for a live view of their appointments.
    """
    from datetime import datetime, timedelta, timezone
    from fastapi.responses import Response as FastAPIResponse

    db = get_service_supabase()

    # Validate API key
    wc = (
        db.table("widget_configs")
        .select("tenant_id")
        .eq("api_key", key)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not wc.data:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Fetch tenant name
    tenant = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
    biz_name = (tenant.data[0].get("business_name") or "AgentNexLiFy") if tenant.data else "AgentNexLiFy"

    # Fetch upcoming + recent appointments (last 30 days + next 90 days)
    cutoff_past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    cutoff_future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()

    # SECURITY: this feed is authenticated only by the widget API key, which is
    # PUBLIC (embedded in every tenant page's source). It therefore MUST NOT
    # return customer PII (name/email/phone/notes) — anyone who reads a tenant's
    # page could otherwise export their whole customer contact list. The feed
    # exposes only appointment time-blocks + status ("busy" calendar view).
    # Follow-up for full-detail sync: a private, revocable per-tenant feed token
    # distinct from the public embed key.
    appts = (
        db.table("appointments")
        .select("id, start_time, end_time, status")
        .eq("tenant_id", tenant_id)
        .neq("status", "cancelled")
        .gte("start_time", cutoff_past)
        .lte("start_time", cutoff_future)
        .order("start_time")
        .limit(500)
        .execute()
    )

    # Build iCal
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//AgentNexLiFy//{biz_name}//EN",
        f"X-WR-CALNAME:{biz_name} Appointments",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for appt in (appts.data or []):
        uid = appt["id"]
        # No customer PII — public-key feed. Generic busy-block only.
        summary = "Appointment"
        description = f"Status: {appt['status']}" if appt.get("status") else ""

        # Format timestamps for iCal (YYYYMMDDTHHMMSSZ)
        def _to_ical_dt(dt_str):
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                return dt.strftime("%Y%m%dT%H%M%SZ")
            except Exception:
                return dt_str.replace("-", "").replace(":", "").replace(" ", "T")[:15] + "Z"

        dtstart = _to_ical_dt(appt["start_time"])
        dtend = _to_ical_dt(appt["end_time"])

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}@agentnexlify.com",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"STATUS:{'CANCELLED' if appt.get('status') == 'no_show' else 'CONFIRMED'}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ical_content = "\r\n".join(lines)

    return FastAPIResponse(
        content=ical_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={biz_name.replace(' ', '_')}_appointments.ics"},
    )
