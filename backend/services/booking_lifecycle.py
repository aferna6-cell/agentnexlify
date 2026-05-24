"""Appointment CRUD: create, list, update, cancel, lead-linking."""


import asyncio
import logging

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def create_appointment(
    tenant_id: str,
    customer_name: str,
    customer_email: str,
    start_time: str,
    end_time: str,
    customer_phone: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create a new appointment with double-booking protection.

    Uses a pre-insert overlap check plus DB EXCLUDE constraint as safety net.
    Raises ValueError on conflict so callers can return 409.
    """
    from backend.services import booking as _b

    db = _b.get_service_supabase()

    existing = (
        tenant_table(db, "appointments", tenant_id)
        .select("id")
        .neq("status", "cancelled")
        .lt("start_time", end_time)
        .gt("end_time", start_time)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise ValueError(
            "This time slot is already booked. Please choose a different time."
        )

    payload = {
        "tenant_id": tenant_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "start_time": start_time,
        "end_time": end_time,
        "status": "confirmed",
        "notes": notes,
    }

    try:
        result = tenant_table(db, "appointments", tenant_id).insert(payload).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "exclude" in error_msg or "overlap" in error_msg or "conflicting" in error_msg:
            raise ValueError(
                "This time slot was just booked by someone else. Please choose a different time."
            ) from e
        raise
    appointment = result.data[0]

    try:
        lead_id = _b.link_appointment_to_lead(tenant_id, appointment)
        if lead_id:
            tenant_table(db, "appointments", tenant_id).update(
                {"lead_id": lead_id}
            ).eq("id", appointment["id"]).execute()
            appointment["lead_id"] = lead_id
    except Exception:
        logger.warning(
            "Failed to link appointment %s to lead",
            appointment["id"],
            exc_info=True,
        )

    try:
        from backend.services.google_calendar import create_calendar_event, get_integration

        if get_integration(tenant_id):
            google_event_id = create_calendar_event(
                tenant_id=tenant_id,
                summary=f"Appointment with {customer_name}",
                start_utc=start_time,
                end_utc=end_time,
                attendee_email=customer_email,
                description=f"Customer: {customer_name}\nEmail: {customer_email}"
                + (f"\nPhone: {customer_phone}" if customer_phone else "")
                + (f"\nNotes: {notes}" if notes else ""),
            )
            if google_event_id:
                tenant_table(db, "appointments", tenant_id).update(
                    {"google_event_id": google_event_id}
                ).eq("id", appointment["id"]).execute()
                appointment["google_event_id"] = google_event_id
    except Exception:
        logger.warning(
            "Failed to sync appointment %s to Google Calendar",
            appointment["id"],
            exc_info=True,
        )

    confirmation = None
    try:
        confirmation = _b._send_appointment_confirmation(tenant_id, appointment)
        loop = asyncio.get_running_loop()
        loop.create_task(confirmation)
    except RuntimeError:
        if confirmation is not None and hasattr(confirmation, "close"):
            confirmation.close()
        logger.info(
            "No running event loop; skipping async confirmation for %s",
            appointment["id"],
        )
    except Exception:
        logger.warning(
            "Failed to send appointment confirmation for %s",
            appointment["id"],
            exc_info=True,
        )

    return appointment


def link_appointment_to_lead(tenant_id: str, appointment: dict) -> str | None:
    """Find or create a lead by email and link to the appointment."""
    from backend.services import booking as _b

    email = appointment.get("customer_email")
    if not email:
        return None

    db = _b.get_service_supabase()

    existing = (
        tenant_table(db, "leads", tenant_id)
        .select("id")
        .eq("email", email)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    lead = tenant_table(db, "leads", tenant_id).insert({
        "client_id": tenant_id,
        "name": appointment.get("customer_name"),
        "email": email,
        "phone": appointment.get("customer_phone"),
        "status": "appointment_booked",
        "source": "booking",
        "conversation_summary": "Created from appointment booking",
    }).execute()

    return lead.data[0]["id"] if lead.data else None


def list_appointments(
    tenant_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List appointments with optional filters."""
    from backend.services import booking as _b

    db = _b.get_service_supabase()
    query = (
        tenant_table(db, "appointments", tenant_id)
        .select("*")
        .order("start_time", desc=False)
    )

    if start_date:
        query = query.gte("start_time", start_date)
    if end_date:
        query = query.lte("start_time", end_date)
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


def update_appointment(tenant_id: str, appointment_id: str, data: dict) -> dict:
    """Update appointment fields (status, notes, reschedule)."""
    from backend.services import booking as _b

    db = _b.get_service_supabase()
    result = (
        tenant_table(db, "appointments", tenant_id)
        .update(data)
        .eq("id", appointment_id)
        .execute()
    )
    if not result.data:
        return {}

    appointment = result.data[0]

    google_event_id = appointment.get("google_event_id")
    if google_event_id:
        try:
            from backend.services.google_calendar import update_calendar_event

            gcal_updates = {}
            if "start_time" in data:
                gcal_updates["start_utc"] = data["start_time"]
            if "end_time" in data:
                gcal_updates["end_utc"] = data["end_time"]
            if gcal_updates:
                update_calendar_event(tenant_id, google_event_id, **gcal_updates)
        except Exception:
            logger.warning(
                "Failed to sync appointment update %s to Google Calendar",
                appointment_id,
                exc_info=True,
            )

    return appointment


def cancel_appointment(tenant_id: str, appointment_id: str) -> dict:
    """Soft-delete: set status to cancelled."""
    from backend.services import booking as _b

    db = _b.get_service_supabase()
    existing = (
        tenant_table(db, "appointments", tenant_id)
        .select("google_event_id")
        .eq("id", appointment_id)
        .limit(1)
        .execute()
    )

    result = _b.update_appointment(tenant_id, appointment_id, {"status": "cancelled"})

    if existing.data and existing.data[0].get("google_event_id"):
        try:
            from backend.services.google_calendar import delete_calendar_event

            delete_calendar_event(tenant_id, existing.data[0]["google_event_id"])
        except Exception:
            logger.warning(
                "Failed to delete Google Calendar event for appointment %s",
                appointment_id,
                exc_info=True,
            )

    return result
