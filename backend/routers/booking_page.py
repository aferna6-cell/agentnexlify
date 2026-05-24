"""Public booking page — shareable URL where customers can book appointments
without going through the chat widget.

Public endpoints (NO auth required):
  GET  /api/v1/book/{business_slug}                          — HTML booking page
  POST /api/v1/book/{business_slug}/submit                   — create appointment + lead
  GET  /api/v1/book/reschedule/{appointment_id}              — reschedule HTML page
  POST /api/v1/book/reschedule/{appointment_id}/submit       — reschedule appointment
  POST /api/v1/book/reschedule/{appointment_id}/cancel       — cancel appointment

All non-HTTP logic lives in `backend.services.booking_page_service` and
HTML templates live in `backend.services.booking_page_html`.
"""

import html
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Request

_ = (Any, cast)  # keep ruff from stripping typing imports used in type-narrow casts below
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.booking import generate_available_slots, link_appointment_to_lead
from backend.services.booking_page_html import (
    build_booking_page_html,
    build_reschedule_page_html,
)
from backend.services.booking_page_service import (
    BookingTenantLookupFailed,
    BookingTenantNotFound,
    fetch_active_service_types,
    fetch_widget_color,
    format_service_note,
    lookup_tenant_by_slug,
    slot_available,
    verify_reschedule_token,
)
from backend.services.email_sender import send_email
from backend.services.tenant_scope import tenant_table
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/book", tags=["booking-page"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BookingSubmitRequest(BaseModel):
    name: str
    email: str
    phone: str
    date: str        # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    service_type_id: str | None = None


class _RescheduleBody(BaseModel):
    token: str
    new_start: str
    new_end: str


class _CancelBody(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Internal HTTP helpers
# ---------------------------------------------------------------------------


def _resolve_tenant(slug: str) -> dict:
    """Look up tenant by slug; wrap service exceptions as HTTP errors."""
    db = get_service_supabase()
    try:
        return lookup_tenant_by_slug(db, slug)
    except BookingTenantNotFound:
        raise HTTPException(status_code=404, detail="Booking page not found")
    except BookingTenantLookupFailed:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


# ---------------------------------------------------------------------------
# GET /api/v1/book/{business_slug}
# ---------------------------------------------------------------------------


@router.get("/{business_slug}", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def booking_page(request: Request, business_slug: str):
    """Return a server-rendered HTML booking page for a business."""
    tenant = _resolve_tenant(business_slug)
    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "Business"

    db = get_service_supabase()
    primary_color = fetch_widget_color(db, tenant_id)
    service_types = fetch_active_service_types(db, tenant_id)

    today = date.today()
    slots_by_date: dict[str, list[dict]] = {}
    for i in range(7):
        target = today + timedelta(days=i)
        try:
            day_slots = generate_available_slots(tenant_id, target)
        except Exception:
            logger.warning(
                "Could not generate slots for tenant %s on %s",
                tenant_id,
                target.isoformat(),
                exc_info=True,
            )
            day_slots = []

        if day_slots:
            slots_by_date[target.isoformat()] = day_slots

    page_html = build_booking_page_html(
        business_name=business_name,
        primary_color=primary_color,
        slug=html.escape(business_slug),
        slots_by_date=slots_by_date,
        service_types=service_types,
    )
    return HTMLResponse(content=page_html, status_code=200)


# ---------------------------------------------------------------------------
# POST /api/v1/book/{business_slug}/submit
# ---------------------------------------------------------------------------


@router.post("/{business_slug}/submit")
@limiter.limit("5/minute")
async def booking_submit(
    request: Request,
    business_slug: str,
    body: BookingSubmitRequest,
):
    """Accept a booking submission and create an appointment + lead record."""
    tenant = _resolve_tenant(business_slug)
    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "Business"

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not body.date or not body.start_time or not body.end_time:
        raise HTTPException(status_code=400, detail="Date and time slot are required")

    # Build ISO timestamps for the slot (naive local time — same convention as create_appointment).
    start_iso = f"{body.date}T{body.start_time}:00"
    end_iso = f"{body.date}T{body.end_time}:00"

    db = get_service_supabase()

    if not slot_available(db, tenant_id, start_iso, end_iso):
        raise HTTPException(
            status_code=409,
            detail="That time slot is no longer available. Please choose another.",
        )

    service_note = format_service_note(db, tenant_id, body.service_type_id)

    try:
        appt_result = tenant_table(db, "appointments", tenant_id).insert({
            "tenant_id": tenant_id,
            "customer_name": body.name.strip(),
            "customer_email": body.email.strip(),
            "customer_phone": body.phone.strip() if body.phone else None,
            "start_time": start_iso,
            "end_time": end_iso,
            "status": "confirmed",
            "notes": service_note,
        }).execute()
    except Exception as exc:
        error_msg = str(exc).lower()
        if "exclude" in error_msg or "overlap" in error_msg or "conflicting" in error_msg:
            raise HTTPException(
                status_code=409,
                detail="That time slot was just booked by someone else. Please choose another.",
            )
        logger.exception(
            "Failed to create appointment for tenant %s slug %s", tenant_id, business_slug
        )
        raise HTTPException(status_code=500, detail="Could not create appointment. Please try again.")

    if not appt_result.data:
        logger.error("Appointment insert returned no data for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Could not create appointment. Please try again.")

    appointment = appt_result.data[0]
    appointment_id = appointment["id"]

    # Create or find lead (uses client_id, not tenant_id — critical rule).
    lead_id: str | None = None
    try:
        lead_id = link_appointment_to_lead(tenant_id, {
            "customer_name": body.name.strip(),
            "customer_email": body.email.strip(),
            "customer_phone": body.phone.strip() if body.phone else None,
        })
        if lead_id:
            tenant_table(db, "appointments", tenant_id).update({"lead_id": lead_id}).eq("id", appointment_id).execute()
    except Exception:
        logger.warning(
            "Could not link appointment %s to lead for tenant %s",
            appointment_id,
            tenant_id,
            exc_info=True,
        )

    # Send confirmation email to customer (best-effort).
    try:
        confirmation_html = (
            f"<h2>Appointment Confirmed</h2>"
            f"<p>Hi {html.escape(body.name.strip())},</p>"
            f"<p>Your appointment with <strong>{html.escape(business_name)}</strong> has been confirmed.</p>"
            f"<ul>"
            f"<li><strong>Date:</strong> {html.escape(body.date)}</li>"
            f"<li><strong>Time:</strong> {html.escape(body.start_time)} – {html.escape(body.end_time)}</li>"
            f"</ul>"
            f"<p>If you need to cancel or reschedule, please contact us directly.</p>"
        )
        await send_email(
            to=body.email.strip(),
            subject=f"Appointment Confirmed — {business_name}",
            body_html=confirmation_html,
            tenant_id=tenant_id,
            lead_id=lead_id or "",
        )
    except Exception:
        logger.warning(
            "Could not send confirmation email for appointment %s", appointment_id, exc_info=True
        )

    # Fire webhook event (best-effort, non-blocking).
    try:
        fire_event_background(
            tenant_id=tenant_id,
            event="appointment.booked",
            data={
                "appointment_id": appointment_id,
                "customer_name": body.name.strip(),
                "customer_email": body.email.strip(),
                "customer_phone": body.phone.strip() if body.phone else None,
                "start_time": start_iso,
                "end_time": end_iso,
                "lead_id": lead_id,
                "source": "public_booking_page",
            },
        )
    except Exception:
        logger.warning(
            "Could not fire appointment.booked webhook for tenant %s", tenant_id, exc_info=True
        )

    return JSONResponse(
        content={"success": True, "message": "Appointment booked! You'll receive a confirmation email shortly."},
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Public reschedule
# ---------------------------------------------------------------------------


@router.get("/reschedule/{appointment_id}", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def reschedule_page(request: Request, appointment_id: str, token: str = Query(...)):
    """Public reschedule page. Customer picks a new time slot."""
    if not verify_reschedule_token(appointment_id, token):
        return HTMLResponse("<h2>Invalid or expired reschedule link.</h2>", status_code=403)

    db = get_service_supabase()
    appt = db.table("appointments").select("*").eq("id", appointment_id).limit(1).execute()
    appt_rows = appt.data or []
    if not appt_rows:
        return HTMLResponse("<h2>Appointment not found.</h2>", status_code=404)

    appointment = cast(dict, appt_rows[0])
    tenant_id = appointment["tenant_id"]

    appt_status = appointment.get("status")
    if appt_status in ("cancelled", "no_show", "completed"):
        return HTMLResponse(f"<h2>This appointment has already been {appt_status}.</h2>", status_code=400)

    tenant_resp = tenant_table(db, "tenants", tenant_id).select("business_name, business_phone").limit(1).execute()
    tenant_rows = tenant_resp.data or []
    biz_name: str = "Our Business"
    if tenant_rows:
        first = cast(dict, tenant_rows[0])
        biz_name = first.get("business_name") or "Our Business"

    today = date.today()
    slots_by_day: dict[str, list[dict]] = {}
    for offset in range(1, 15):
        d = today + timedelta(days=offset)
        slots = generate_available_slots(tenant_id, d)
        if slots:
            slots_by_day[d.isoformat()] = [
                {"start": s["start_utc"], "end": s["end_utc"], "label": s["display"]}
                for s in slots
            ]

    current_dt = appointment.get("start_time", "")
    try:
        dt = datetime.fromisoformat(appointment["start_time"].replace("Z", "+00:00"))
        current_dt = dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        logger.debug("Could not format appointment start_time for display", exc_info=True)

    page_html = build_reschedule_page_html(
        appointment_id=appointment_id,
        token=token,
        biz_name=biz_name,
        current_dt_label=current_dt,
        slots_by_day=slots_by_day,
    )
    return HTMLResponse(page_html)


@router.post("/reschedule/{appointment_id}/submit")
@limiter.limit("10/minute")
async def reschedule_submit(request: Request, appointment_id: str, body: _RescheduleBody):
    """Submit a reschedule for an appointment."""
    if not verify_reschedule_token(appointment_id, body.token):
        raise HTTPException(status_code=403, detail="Invalid or expired reschedule link")

    db = get_service_supabase()
    appt = db.table("appointments").select("*").eq("id", appointment_id).limit(1).execute()
    appt_rows = appt.data or []
    if not appt_rows:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment = cast(dict, appt_rows[0])
    appt_status = appointment.get("status")
    if appt_status in ("cancelled", "no_show", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot reschedule — appointment is {appt_status}")

    tenant_id = appointment["tenant_id"]

    existing = (
        tenant_table(db, "appointments", tenant_id)
        .select("id")
        .neq("id", appointment_id)
        .neq("status", "cancelled")
        .lt("start_time", body.new_end)
        .gt("end_time", body.new_start)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="That time slot is no longer available")

    try:
        result = (
            tenant_table(db, "appointments", tenant_id)
            .update({
                "start_time": body.new_start,
                "end_time": body.new_end,
                "notes": f"{appointment.get('notes', '') or ''}\n[Rescheduled by customer]".strip(),
            })
            .eq("id", appointment_id)
            .execute()
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        if "exclude" in error_msg or "overlap" in error_msg:
            raise HTTPException(status_code=409, detail="That time slot was just booked")
        logger.exception("Failed to reschedule appointment %s", appointment_id)
        raise HTTPException(status_code=500, detail="Failed to reschedule")

    try:
        from backend.services.booking import _send_appointment_confirmation
        from backend.services.task_utils import safe_create_task
        if result.data:
            safe_create_task(
                _send_appointment_confirmation(tenant_id, result.data[0]),
                name=f"reschedule_confirmation_{appointment_id}",
            )
    except Exception:
        logger.warning("Failed to send reschedule confirmation for %s", appointment_id, exc_info=True)

    try:
        from backend.services.activity import log_activity
        log_activity(
            tenant_id=tenant_id,
            activity_type="appointment_rescheduled",
            description=f"Customer rescheduled appointment to {body.new_start}",
            lead_id=appointment.get("lead_id"),
        )
    except Exception:
        logger.warning("Failed to log reschedule activity", exc_info=True)

    return {"success": True, "message": "Appointment rescheduled successfully"}


@router.post("/reschedule/{appointment_id}/cancel")
@limiter.limit("10/minute")
async def reschedule_cancel(request: Request, appointment_id: str, body: _CancelBody):
    """Cancel an appointment via the reschedule link."""
    if not verify_reschedule_token(appointment_id, body.token):
        raise HTTPException(status_code=403, detail="Invalid or expired link")

    db = get_service_supabase()
    appt = db.table("appointments").select("id, tenant_id, lead_id, status").eq("id", appointment_id).limit(1).execute()
    appt_rows = appt.data or []
    if not appt_rows:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment = cast(dict, appt_rows[0])
    tenant_id = appointment["tenant_id"]
    if appointment.get("status") == "cancelled":
        return {"success": True, "message": "Already cancelled"}

    tenant_table(db, "appointments", tenant_id).update({"status": "cancelled"}).eq("id", appointment_id).execute()

    try:
        from backend.services.activity import log_activity
        log_activity(
            tenant_id=tenant_id,
            activity_type="appointment_cancelled",
            description="Customer cancelled appointment via reschedule link",
            lead_id=appointment.get("lead_id"),
        )
    except Exception:
        logger.warning("Failed to log cancel activity", exc_info=True)

    fire_event_background(tenant_id, "appointment.cancelled", {"appointment_id": appointment_id})

    return {"success": True, "message": "Appointment cancelled"}


# `timezone` retained for forward compat (reschedule TTL check shares it indirectly).
_ = timezone
