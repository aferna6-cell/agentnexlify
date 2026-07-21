"""Booking ↔ Google Calendar write-back, failure handling, and slot fallback (#119).

Companion module to ``booking.py`` (which is already ~22.5K — user-rules Rule 9
+ Rule 12: a new concern goes in a new module, not into the god-class). These
functions are the GCal-integration core the booking flow calls into:

- ``create_gcal_event`` — write the appointment to Google Calendar and stamp the
  returned ``gcal_event_id`` back on the row.
- ``handle_gcal_failure`` — mark the appointment ``pending_sync`` and enqueue a
  ``pending_automations`` retry so a transient GCal outage never loses the sync.
- ``rule_based_slots`` — the GCal-OAuth-expiry fallback: deterministic 60-minute
  windows in business hours (09:00–17:00), no Calendar API spend.
- ``next_available_alternates`` — the three alternates returned on a booking race
  (409 slot-taken), per spec §8.

Every DB touch is fail-open (matching ``retry_worker.py`` #118 and the rest of
the automation layer): a missing not-yet-migrated table (``pending_automations``
is migration 180) or a transient error is logged and swallowed, never raised
into the booking request. Dependencies (db, the GCal create fn, ``now``) are
injectable so the logic is unit-testable without booting the app.

Appointments are ``tenant_id``-scoped (verified against ``booking.py`` +
``schema-discipline.md`` — the ``client_id`` note in the issue text is wrong;
code wins).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)

# Fallback business-hours window (tenant-local, applied when GCal free/busy is
# unavailable). Kept simple + deterministic on purpose — this path exists to
# never block a booking, not to be a full scheduler.
_DAY_START_HOUR = 9
_DAY_END_HOUR = 17  # last slot starts at 16:00, ends 17:00
_SLOT_MINUTES = 60

# pending_automations retry cadence for an appointment sync (seconds).
_SYNC_BACKOFF_SECONDS = (30, 120, 600)


def _get_db(db):
    if db is not None:
        return db
    from backend.models.database import get_service_supabase

    return get_service_supabase()


def create_gcal_event(
    tenant_id: str,
    appointment: dict,
    *,
    db=None,
    create_event: Callable[..., Any] | None = None,
) -> str | None:
    """Create a Google Calendar event for ``appointment`` and write the id back.

    Returns the ``gcal_event_id`` on success, ``None`` when GCal declines (auth
    expired / API error — ``create_calendar_event`` already returns None there)
    or on any error. Never raises: a booking is never blocked by a calendar
    hiccup — the caller routes a None to ``handle_gcal_failure``.
    """
    if create_event is None:
        from backend.services.google_calendar import create_calendar_event

        create_event = create_calendar_event

    start = appointment.get("start_utc") or appointment.get("start")
    end = appointment.get("end_utc") or appointment.get("end")
    if not start or not end:
        logger.warning("create_gcal_event: appointment missing start/end")
        return None

    summary = appointment.get("service") or appointment.get("title") or "Appointment"
    attendee = appointment.get("customer_email") or appointment.get("contact_email")
    description = appointment.get("notes") or appointment.get("description")

    try:
        event_id = create_event(
            tenant_id, summary, start, end,
            attendee_email=attendee, description=description,
        )
    except Exception:
        logger.warning("create_gcal_event: GCal create raised; treating as failure")
        return None

    if not event_id:
        return None

    appt_id = appointment.get("id")
    if appt_id:
        try:
            db = _get_db(db)
            db.table("appointments").update({"gcal_event_id": event_id}).eq(
                "id", appt_id
            ).execute()
        except Exception:
            # gcal_event_id column not applied yet, or transient — the event
            # exists in GCal regardless; write-back is best-effort.
            logger.warning(
                "create_gcal_event: gcal_event_id write-back failed (event still created)"
            )

    return event_id


def handle_gcal_failure(
    tenant_id: str,
    appointment_id: str,
    *,
    db=None,
    now: datetime | None = None,
) -> None:
    """Mark the appointment ``pending_sync`` and enqueue a retry.

    Called when ``create_gcal_event`` returned None. The customer is never
    blocked: the appointment stays booked locally, flips to ``pending_sync``,
    and the retry worker (#118) re-attempts the calendar write later. Fail-open
    — ``pending_automations`` may not be migrated yet (migration 180).
    """
    now = now or datetime.now(timezone.utc)
    db = _get_db(db)

    try:
        db.table("appointments").update({"status": "pending_sync"}).eq(
            "id", appointment_id
        ).execute()
    except Exception:
        logger.warning("handle_gcal_failure: could not set pending_sync status")

    scheduled_for = (now + timedelta(seconds=_SYNC_BACKOFF_SECONDS[0])).isoformat()
    try:
        db.table("pending_automations").insert(
            {
                "tenant_id": tenant_id,
                "automation_type": "appointment_sync",
                "payload": {"appointment_id": appointment_id},
                "status": "pending",
                "attempts": 0,
                "scheduled_for": scheduled_for,
            }
        ).execute()
    except Exception:
        # Table not applied yet (migration 180) or transient — the appointment
        # is already flagged pending_sync, so it is not lost.
        logger.warning(
            "handle_gcal_failure: pending_automations enqueue failed (table may be unapplied)"
        )


def _slot(start_dt: datetime) -> dict:
    end_dt = start_dt + timedelta(minutes=_SLOT_MINUTES)
    return {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "display": start_dt.strftime("%a %b %-d, %-I:%M %p"),
    }


def rule_based_slots(
    *,
    now: datetime,
    booked_starts: Iterable[str] = (),
    count: int = 5,
) -> list[dict]:
    """Deterministic next ``count`` free 60-minute windows — no Calendar API.

    The GCal-OAuth-expiry fallback (spec §8): when free/busy can't be read, offer
    rule-based slots in the 09:00–17:00 window so booking never stalls. Skips
    past times and any start already in ``booked_starts``. Slots are generated in
    ``now``'s timezone.
    """
    booked = set(booked_starts)
    out: list[dict] = []
    # Start from the next whole hour at or after now, clamped into the window.
    cursor = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    # Bound the search so a pathological input can't loop forever (~60 days).
    horizon = now + timedelta(days=60)
    while len(out) < count and cursor <= horizon:
        if _DAY_START_HOUR <= cursor.hour <= (_DAY_END_HOUR - 1) and cursor > now:
            slot = _slot(cursor)
            if slot["start"] not in booked:
                out.append(slot)
            cursor += timedelta(hours=1)
        else:
            # Jump to the next day's opening hour.
            nxt = (cursor + timedelta(days=1)).replace(hour=_DAY_START_HOUR)
            cursor = nxt if nxt > cursor else cursor + timedelta(hours=1)
    return out


def next_available_alternates(
    available: list[dict],
    *,
    taken_start: str,
    count: int = 3,
) -> list[dict]:
    """Return up to ``count`` alternates from ``available``, excluding the taken
    slot — the ``{error: slot_taken, alternatives: [...]}`` payload on a 409."""
    return [s for s in available if s.get("start") != taken_start][:count]
