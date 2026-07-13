"""Voice booking — let the AI phone assistant book real appointments (G3 Phase 1).

The widget books through a calendar UI; on a phone call the AI must offer
slots aloud and book from spoken confirmation. Same marker-JSON pattern as
widget_booking.py (ORDER_JSON / BID_REQUEST): the slot list is injected into
the system prompt, and when the caller has picked a time and given a name,
Claude appends one line

    BOOK_JSON: {"name": "...", "date": "YYYY-MM-DD", "start": "HH:MM"}

which the backend strips, validates against the live slot list (so a
hallucinated time can't book), and turns into a confirmed appointment via
``booking.create_appointment`` (EXCLUDE constraint guards double-booking).
Conversation history is the state — no per-call state store is needed, so the
flow is safe across the 4 uvicorn workers.

Failure contract mirrors the rest of the voice path: helpers never raise; a
booking failure degrades to the assistant's normal callback promise, never a
dropped call.

Refs: audits/audit-voice-g3-scope-2026-07-09.md Phase 1.
Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import json
import logging
import re
from datetime import date, timedelta

from backend.models.database import get_service_supabase
from backend.services.booking import create_appointment, generate_available_slots

logger = logging.getLogger(__name__)

BOOKING_MARKER = "BOOK_JSON:"

# Same intent net the widget uses (widget/agentnexlify-widget.js handleSend),
# plus spoken-language variants.
_INTENT_RE = re.compile(
    r"\b(book|appointment|schedule|reserve|come in|available|availability|opening)\b",
    re.IGNORECASE,
)

# How far ahead to look for a day with open slots, and how many slots to speak.
_LOOKAHEAD_DAYS = 7
_MAX_SPOKEN_SLOTS = 4


def wants_booking(texts) -> bool:
    """True when any caller utterance shows booking intent."""
    return any(_INTENT_RE.search(t or "") for t in texts)


def _booking_enabled(tenant_id: str) -> bool:
    """Mirror of the widget gate: widget_configs.booking_enabled."""
    try:
        db = get_service_supabase()
        result = (
            db.table("widget_configs")
            .select("booking_enabled")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        return bool(result.data and result.data[0].get("booking_enabled"))
    except Exception:
        logger.warning(
            "voice_booking: booking_enabled lookup failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return False


def _next_open_slots(tenant_id: str) -> tuple[str, list[dict]] | None:
    """First day within the lookahead window that has open slots.

    Returns (ISO date, slots) or None. Slots are the booking-service dicts:
    {"start": "HH:MM", "end": "HH:MM", "start_utc": ISO, "end_utc": ISO}.
    """
    today = date.today()
    for offset in range(_LOOKAHEAD_DAYS):
        target = today + timedelta(days=offset)
        try:
            slots = generate_available_slots(tenant_id, target)
        except Exception:
            logger.warning(
                "voice_booking: slot generation failed for tenant %s date %s",
                tenant_id,
                target,
                exc_info=True,
            )
            return None
        if slots:
            return target.isoformat(), slots
    return None


def _spoken_time(hhmm: str) -> str:
    """'14:30' -> '2:30 PM' for natural speech."""
    try:
        hour, minute = int(hhmm[:2]), int(hhmm[3:5])
    except (ValueError, IndexError):
        return hhmm
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}" if minute else f"{hour12} {suffix}"


def booking_prompt_context(tenant_id: str) -> str | None:
    """System-prompt block offering real slots, or None when booking is off
    or nothing is open in the lookahead window."""
    if not _booking_enabled(tenant_id):
        return None
    found = _next_open_slots(tenant_id)
    if not found:
        return None
    day_iso, slots = found
    day = date.fromisoformat(day_iso)
    spoken_day = day.strftime("%A, %B %d")
    offered = slots[:_MAX_SPOKEN_SLOTS]
    times = ", ".join(_spoken_time(s["start"]) for s in offered)
    return (
        "APPOINTMENT BOOKING: You can book appointments directly. "
        f"The earliest openings are on {spoken_day} ({day_iso}) at: {times}. "
        "If the caller wants to book, offer these times, then collect their "
        "name and confirm the chosen time back to them. Once they have "
        "confirmed a specific time AND given their name, append this EXACT "
        "final line to your response (the caller never hears it):\n"
        f'{BOOKING_MARKER} {{"name": "<caller name>", "date": "{day_iso}", '
        '"start": "<HH:MM in 24-hour format from the offered times>"}\n'
        "Only emit that line for times you actually offered, never for other "
        "times, and never before the caller has clearly confirmed."
    )


def _extract_marker(ai_text: str) -> tuple[str, dict | None]:
    """Split the marker payload out of Claude's reply. Returns (clean, data)."""
    idx = ai_text.find(BOOKING_MARKER)
    if idx == -1:
        return ai_text, None
    clean = ai_text[:idx].strip()
    raw = ai_text[idx + len(BOOKING_MARKER):].strip()
    match = re.search(r"\{[\s\S]*?\}", raw)
    if not match:
        logger.warning("voice_booking: marker present but no JSON payload")
        return clean, None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        logger.warning("voice_booking: marker JSON parse failed")
        return clean, None
    return clean, data if isinstance(data, dict) else None


def handle_booking_marker(
    tenant_id: str, caller_phone: str, ai_text: str
) -> tuple[str, dict | None]:
    """Strip a BOOK_JSON marker and book the appointment it describes.

    Returns (speakable_text, appointment_or_None). On any validation or
    booking failure, the appointment is None and the speakable text falls
    back to a callback promise — never raises.
    """
    clean, data = _extract_marker(ai_text)
    if data is None:
        return clean or ai_text, None

    name = (data.get("name") or "").strip()
    day_iso = (data.get("date") or "").strip()
    start_hhmm = (data.get("start") or "").strip()
    if not (name and day_iso and start_hhmm):
        logger.warning("voice_booking: incomplete marker payload %s", sorted(data))
        return clean, None

    # Re-validate against the live slot list — the marker must name a slot
    # that is genuinely still open (guards hallucinated times and races).
    try:
        slots = generate_available_slots(tenant_id, date.fromisoformat(day_iso))
    except Exception:
        logger.warning(
            "voice_booking: revalidation slot fetch failed tenant=%s", tenant_id,
            exc_info=True,
        )
        slots = []
    slot = next((s for s in slots if s.get("start") == start_hhmm), None)
    if slot is None:
        logger.info(
            "voice_booking: marker time %s %s not in open slots — not booking",
            day_iso,
            start_hhmm,
        )
        return (
            f"{clean} Actually, it looks like that exact time just became "
            "unavailable. Someone from the team will call you back to lock in "
            "a time that works.",
            None,
        )

    try:
        appointment = create_appointment(
            tenant_id=tenant_id,
            customer_name=name,
            customer_email="",  # phone bookings have no email; column is NOT NULL
            customer_phone=caller_phone or None,
            start_time=slot["start_utc"],
            end_time=slot["end_utc"],
            notes="Booked by AI phone assistant",
        )
    except ValueError:
        # Double-booking race caught by the EXCLUDE constraint / overlap check
        return (
            f"{clean} Actually, that time was just taken. Someone from the "
            "team will call you back to find another time.",
            None,
        )
    except Exception:
        logger.exception("voice_booking: create_appointment failed tenant=%s", tenant_id)
        return (
            f"{clean} I've made a note of your preferred time and someone "
            "will call you back shortly to confirm.",
            None,
        )

    _backfill_lead_name(tenant_id, caller_phone, name, appointment)
    logger.info(
        "voice_booking: booked appointment %s tenant=%s at %s",
        appointment.get("id"),
        tenant_id,
        slot["start_utc"],
    )
    return clean, appointment


def _backfill_lead_name(
    tenant_id: str, caller_phone: str, name: str, appointment: dict
) -> None:
    """Set the phone-lead's name (voice leads start name-less) and link the
    appointment to it. Best-effort; leads uses client_id (schema invariant)."""
    if not caller_phone:
        return
    try:
        db = get_service_supabase()
        result = (
            db.table("leads")
            .select("id, name")
            .eq("client_id", tenant_id)
            .eq("phone", caller_phone)
            .limit(1)
            .execute()
        )
        if not result.data:
            return
        lead = result.data[0]
        current = (lead.get("name") or "").strip().lower()
        if not current or current.startswith("caller"):
            db.table("leads").update({"name": name}).eq("id", lead["id"]).execute()
        if appointment.get("id") and not appointment.get("lead_id"):
            db.table("appointments").update({"lead_id": lead["id"]}).eq(
                "id", appointment["id"]
            ).execute()
    except Exception:
        logger.warning(
            "voice_booking: lead backfill failed tenant=%s", tenant_id, exc_info=True
        )
