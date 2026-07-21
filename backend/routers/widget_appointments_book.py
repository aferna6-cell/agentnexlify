"""Widget appointment booking endpoint with dual auth (#120).

``POST /api/v1/widget/appointments/book`` — a widget books an appointment using
EITHER the legacy ``api_key`` (query/body) OR a short-lived ``Authorization:
Bearer`` token (``widget_booking_auth`` #120 core, merged). Both authenticate
against the tenant's own widget key.

On a booking race (``booking.create_appointment`` raises ``ValueError``) the
endpoint returns 409 with three alternate slots (spec §8) built from
``booking.generate_available_slots`` + ``booking_gcal.next_available_alternates``
(#119 core, merged). GCal write-back already happens inside
``create_appointment``, so this router is thin orchestration over tested pieces
— no edit to the ``booking.py`` god-class.

``appointments`` is ``tenant_id``-scoped (verified against ``booking.py``). No
``from __future__ import annotations`` (CLAUDE.md Rule 5).
"""

import logging
from datetime import date as date_type
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services import booking, booking_gcal, widget_booking_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/widget/appointments", tags=["widget-appointments"])


class WidgetBookRequest(BaseModel):
    tenant_id: str
    start_time: str
    end_time: str
    customer_name: str
    customer_email: str
    customer_phone: str = None
    notes: str = None
    service: str = None
    api_key: str = None


class WidgetBookResponse(BaseModel):
    appointment_id: str
    gcal_event_id: str = None
    confirmation_message: str
    status: str


def _widget_api_key_for(tenant_id: str) -> str:
    """The tenant's widget key (the shared secret for both auth paths), or None."""
    try:
        res = (
            get_service_supabase()
            .table("widget_configs")
            .select("api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0].get("api_key")
    except Exception:
        logger.warning("widget_book: api_key lookup failed for %s", tenant_id)
    return None


def _bearer(authorization: str = None) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _alternates(tenant_id: str, start_time: str) -> list:
    """Three next-available slots for a 409 response."""
    try:
        parsed = date_type.fromisoformat(start_time[:10])
        slots = booking.generate_available_slots(tenant_id, parsed) or []
    except Exception:
        slots = []
    if slots:
        # generate_available_slots returns {start,end,start_utc,end_utc}; normalize
        norm = [
            {"start": s.get("start_utc") or s.get("start"),
             "end": s.get("end_utc") or s.get("end"),
             "display": f'{s.get("start")}–{s.get("end")}'}
            for s in slots
        ]
        return booking_gcal.next_available_alternates(norm, taken_start=start_time, count=3)
    # Fallback: rule-based windows (no calendar dependency)
    return booking_gcal.rule_based_slots(now=datetime.now(timezone.utc), count=3)


@router.post("/book", response_model=WidgetBookResponse)
@limiter.limit("20/minute")
async def book_appointment(
    request: Request,
    payload: WidgetBookRequest,
    api_key: str = Query(None, description="Legacy widget API key"),
    authorization: str = Header(None),
):
    tenant_id = payload.tenant_id
    widget_key = _widget_api_key_for(tenant_id)

    status, detail = widget_booking_auth.authorize_booking(
        widget_api_key=widget_key,
        api_key=api_key or payload.api_key,
        bearer_token=_bearer(authorization),
    )
    if status != 200:
        raise HTTPException(status_code=status, detail=detail)

    try:
        appointment = booking.create_appointment(
            tenant_id=tenant_id,
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            start_time=payload.start_time,
            end_time=payload.end_time,
            customer_phone=payload.customer_phone,
            notes=payload.notes,
        )
    except ValueError:
        # Slot taken — offer alternates (spec §8).
        raise HTTPException(
            status_code=409,
            detail={
                "error": "slot_taken",
                "message": "That time was just booked. Here are the next openings.",
                "alternatives": _alternates(tenant_id, payload.start_time),
            },
        )
    except Exception:
        logger.exception("widget_book: create_appointment failed for %s", tenant_id)
        raise HTTPException(status_code=502, detail="Could not book the appointment right now.")

    return WidgetBookResponse(
        appointment_id=appointment["id"],
        gcal_event_id=appointment.get("google_event_id"),
        confirmation_message=f"Booked — see you {payload.start_time}.",
        status=appointment.get("status", "confirmed"),
    )
