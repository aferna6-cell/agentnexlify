"""Appointment reminders — schedule + send SMS reminders before booked appointments.

Phase 1 of "AI appointment reminders + smart rebooking": cut no-shows by
texting customers 24h and 2h before their appointment start time.

Two entrypoints:
  - ``schedule_reminders_for_appointment(appointment)`` — called from
    ``backend.services.booking.create_appointment`` right after an
    appointment is booked. Inserts a 24h row + a 2h row.
  - ``send_due_reminders()`` — called from the cron trigger
    (``POST /api/v1/appointments/reminders/run``). Sends every reminder whose
    ``scheduled_for`` has arrived.

SMS always routes through ``backend.services.sms_compliance.is_suppressed``
before send — reminders are transactional (post-booking notification), but a
TCPA opt-out (STOP) suppresses every outbound SMS class, reminders included.
``send_sms`` is also passed ``tenant_id`` so demo tenants get the existing
no-op behavior (see ``twilio_service.send_sms``).

appointments.tenant_id — NOT client_id. Appointments differ from
leads/conversations, which use client_id. See schema-discipline.md.

Idempotency:
  - Scheduling: ``appointment_reminders`` has a UNIQUE (appointment_id,
    reminder_type) constraint (migration 167) + upsert with
    ``ignore_duplicates=True`` — re-scheduling the same appointment is a
    no-op for windows already scheduled.
  - Sending: every reminder row is claimed (status pending -> sending, gated
    on ``.eq("status", "pending")``) immediately before the SMS send, and
    finalized (sending -> sent/failed, gated on ``.eq("status", "sending")``)
    right after. A second worker racing the same row loses the claim and
    no-ops instead of sending a second text — same idiom as
    ``scheduled/billing_jobs.py::process_recurring_invoices``.
  - Every per-reminder failure is caught and logged; one bad reminder never
    aborts the batch.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services import sms_compliance
from backend.services.tenant_scope import tenant_table
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

# Insertion order matters for schedule_reminders_for_appointment's return
# order (24h created before 2h) — Python 3.7+ dicts preserve it.
REMINDER_WINDOWS = {
    "24h": timedelta(hours=24),
    "2h": timedelta(hours=2),
}

_DUE_BATCH_LIMIT = 200


def _parse_dt(value: str | None) -> datetime | None:
    """Parse a Supabase ISO timestamp into an aware UTC datetime. None on failure."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _reminders_enabled(db, tenant_id: str) -> bool:
    """True unless the tenant explicitly disabled reminders. Fails open —
    a lookup error should not silently kill reminders platform-wide."""
    try:
        result = (
            db.table("tenants")
            .select("appointment_reminders_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "_reminders_enabled: lookup failed for tenant %s — defaulting enabled",
            tenant_id,
            exc_info=True,
        )
        return True

    if not result.data:
        return True
    return result.data[0].get("appointment_reminders_enabled") is not False


def schedule_reminders_for_appointment(appointment: dict) -> list[dict]:
    """Insert 24h + 2h reminder rows for a newly booked appointment.

    Best-effort — callers (``booking.create_appointment``) treat failures as
    non-fatal, same as the Google Calendar sync and confirmation send in that
    function.

    Skips a window whose fire time has already passed (appointment booked
    less than 24h/2h out) — sending "reminder" content after the fact is
    misleading, and the booking confirmation SMS already covers that case.
    Skips entirely if the tenant has reminders disabled.
    """
    appointment_id = appointment.get("id")
    tenant_id = appointment.get("tenant_id")
    start_time = appointment.get("start_time")
    if not appointment_id or not tenant_id or not start_time:
        logger.warning(
            "schedule_reminders_for_appointment: missing id/tenant_id/start_time — skipping"
        )
        return []

    start_dt = _parse_dt(start_time)
    if start_dt is None:
        logger.warning(
            "schedule_reminders_for_appointment: unparsable start_time %r for appointment %s",
            start_time,
            appointment_id,
        )
        return []

    db = get_service_supabase()

    if not _reminders_enabled(db, tenant_id):
        logger.info(
            "schedule_reminders_for_appointment: reminders disabled for tenant %s — skipping",
            tenant_id,
        )
        return []

    now = datetime.now(timezone.utc)
    created: list[dict] = []

    for reminder_type, lead_time in REMINDER_WINDOWS.items():
        scheduled_for = start_dt - lead_time
        if scheduled_for <= now:
            logger.info(
                "schedule_reminders_for_appointment: %s window already passed for "
                "appointment %s — skipping",
                reminder_type,
                appointment_id,
            )
            continue

        payload = {
            "tenant_id": tenant_id,
            "appointment_id": appointment_id,
            "reminder_type": reminder_type,
            "scheduled_for": scheduled_for.isoformat(),
            "status": "pending",
        }
        try:
            result = (
                tenant_table(db, "appointment_reminders", tenant_id)
                .upsert(
                    payload,
                    on_conflict="appointment_id,reminder_type",
                    ignore_duplicates=True,
                )
                .execute()
            )
            if result.data:
                created.extend(result.data)
        except Exception:
            logger.warning(
                "schedule_reminders_for_appointment: failed to schedule %s reminder "
                "for appointment %s",
                reminder_type,
                appointment_id,
                exc_info=True,
            )

    return created


def _build_message(reminder_type: str, appointment: dict, business_name: str) -> str:
    customer_name = appointment.get("customer_name") or "there"
    start_dt = _parse_dt(appointment.get("start_time"))
    time_str = (
        start_dt.strftime("%B %d at %I:%M %p")
        if start_dt
        else (appointment.get("start_time") or "")
    )

    if reminder_type == "24h":
        return (
            f"Hi {customer_name}, reminder: your appointment with {business_name} "
            f"is tomorrow ({time_str}). Reply STOP to opt out of texts."
        )
    return (
        f"Hi {customer_name}, your appointment with {business_name} is in about "
        f"2 hours ({time_str}). See you soon! Reply STOP to opt out."
    )


def _claim_pending(db, reminder_id: str) -> bool:
    """Atomically flip pending -> sending. Returns True if this call won the claim."""
    try:
        result = (
            db.table("appointment_reminders")
            .update({"status": "sending"})
            .eq("id", reminder_id)
            .eq("status", "pending")
            .execute()
        )
        return bool(result.data)
    except Exception:
        logger.warning(
            "_claim_pending: claim failed for reminder %s", reminder_id, exc_info=True
        )
        return False


def _finalize_pending(db, reminder_id: str, status: str) -> None:
    """Write a terminal status directly from pending (no SMS was attempted)."""
    try:
        db.table("appointment_reminders").update({"status": status}).eq(
            "id", reminder_id
        ).eq("status", "pending").execute()
    except Exception:
        logger.warning(
            "_finalize_pending: failed to write status=%s for reminder %s",
            status,
            reminder_id,
            exc_info=True,
        )


def _finalize_claimed(
    db, reminder_id: str, status: str, set_sent_at: bool = False
) -> None:
    """Write a terminal status after a successful claim (an SMS was attempted)."""
    payload: dict = {"status": status}
    if set_sent_at:
        payload["sent_at"] = datetime.now(timezone.utc).isoformat()
    try:
        db.table("appointment_reminders").update(payload).eq("id", reminder_id).eq(
            "status", "sending"
        ).execute()
    except Exception:
        logger.warning(
            "_finalize_claimed: failed to write status=%s for reminder %s",
            status,
            reminder_id,
            exc_info=True,
        )


def _force_finalize(db, reminder_id: str, status: str) -> None:
    """Last-resort finalize with no status precondition.

    Only used when ``_send_one_reminder`` raises an exception nothing else
    caught — makes sure a reminder never gets stuck in 'sending' forever
    because of a bug rather than an expected failure mode.
    """
    try:
        db.table("appointment_reminders").update({"status": status}).eq(
            "id", reminder_id
        ).execute()
    except Exception:
        logger.warning(
            "_force_finalize: failed to write status=%s for reminder %s",
            status,
            reminder_id,
            exc_info=True,
        )


async def _send_one_reminder(db, row: dict) -> str:
    """Send a single due reminder row. Returns 'sent' | 'skipped' | 'failed'.

    Never raises for expected failure modes (missing/cancelled appointment,
    no phone, opted out, tenant disabled reminders, Twilio failure) — each
    resolves to a terminal status write and a return value.
    """
    reminder_id = row["id"]
    tenant_id = row["tenant_id"]
    appointment_id = row["appointment_id"]
    reminder_type = row["reminder_type"]

    appt_result = (
        db.table("appointments")
        .select("id, tenant_id, status, customer_name, customer_phone, start_time")
        .eq("id", appointment_id)
        .limit(1)
        .execute()
    )
    appointment = appt_result.data[0] if appt_result.data else None

    if (
        not appointment
        or appointment.get("tenant_id") != tenant_id
        or appointment.get("status") == "cancelled"
    ):
        _finalize_pending(db, reminder_id, "skipped")
        return "skipped"

    phone = appointment.get("customer_phone")
    if not phone:
        _finalize_pending(db, reminder_id, "skipped")
        return "skipped"

    tenant_result = (
        db.table("tenants")
        .select("business_name, appointment_reminders_enabled")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    tenant_row = tenant_result.data[0] if tenant_result.data else {}
    if tenant_row.get("appointment_reminders_enabled") is False:
        _finalize_pending(db, reminder_id, "skipped")
        return "skipped"

    if sms_compliance.is_suppressed(db, tenant_id, phone):
        logger.info(
            "send_due_reminders: reminder %s suppressed (opt-out) for tenant %s",
            reminder_id,
            tenant_id,
        )
        _finalize_pending(db, reminder_id, "skipped")
        return "skipped"

    # Claim right before the side-effecting send — a worker that reaches this
    # point a moment after another worker already claimed it loses the race
    # and no-ops instead of sending a second text.
    if not _claim_pending(db, reminder_id):
        return "skipped"

    business_name = tenant_row.get("business_name") or "Us"
    body = _build_message(reminder_type, appointment, business_name)

    try:
        ok = await send_sms(to=phone, body=body, tenant_id=tenant_id)
    except Exception:
        logger.exception(
            "send_due_reminders: send_sms raised for reminder %s", reminder_id
        )
        ok = False

    if ok:
        _finalize_claimed(db, reminder_id, "sent", set_sent_at=True)
        return "sent"

    _finalize_claimed(db, reminder_id, "failed")
    return "failed"


async def send_due_reminders() -> dict:
    """Send every reminder whose ``scheduled_for`` time has arrived.

    Per-reminder failures are logged and never stop the batch. Returns
    ``{"checked": N, "sent": N, "skipped": N, "failed": N}``.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    counts = {"checked": 0, "sent": 0, "skipped": 0, "failed": 0}

    try:
        due = (
            db.table("appointment_reminders")
            .select("id, tenant_id, appointment_id, reminder_type, scheduled_for, status")
            .eq("status", "pending")
            .lte("scheduled_for", now.isoformat())
            .limit(_DUE_BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_due_reminders: failed to query due reminders")
        return counts

    for row in due.data or []:
        counts["checked"] += 1
        try:
            outcome = await _send_one_reminder(db, row)
        except Exception:
            logger.exception(
                "send_due_reminders: unhandled error for reminder %s — marking failed",
                row.get("id"),
            )
            _force_finalize(db, row["id"], "failed")
            outcome = "failed"
        counts[outcome] = counts.get(outcome, 0) + 1

    return counts
