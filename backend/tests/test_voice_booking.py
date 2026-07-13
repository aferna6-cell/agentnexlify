"""Tests for voice booking (G3 Phase 1) — backend/services/voice_booking.py.

Contracts:
  - intent detection catches spoken booking phrasing, ignores small talk
  - prompt context only exists when booking is on AND slots are open, and it
    carries the BOOK_JSON marker contract with real slot times
  - handle_booking_marker books ONLY times present in the live slot list,
    strips the marker from the speakable text, and degrades to a callback
    promise on conflicts/failures (never raises)
  - the phone lead gets the caller's name backfilled
"""

from unittest.mock import MagicMock, patch

from backend.services import voice_booking as vb


def _slot(start="09:00"):
    return {
        "start": start,
        "end": "09:30",
        "start_utc": f"2026-07-14T{start}:00+00:00",
        "end_utc": "2026-07-14T09:30:00+00:00",
    }


class TestIntentDetection:
    def test_booking_phrases_detected(self):
        assert vb.wants_booking(["I'd like to book an appointment"])
        assert vb.wants_booking(["what times are available tomorrow"])
        assert vb.wants_booking(["hi", "can I schedule a visit"])
        assert vb.wants_booking(["when can I come in"])

    def test_small_talk_ignored(self):
        assert not vb.wants_booking(["what are your prices"])
        assert not vb.wants_booking(["do you fix water heaters", ""])
        assert not vb.wants_booking([])


class TestSpokenTime:
    def test_formats(self):
        assert vb._spoken_time("09:00") == "9 AM"
        assert vb._spoken_time("14:30") == "2:30 PM"
        assert vb._spoken_time("12:00") == "12 PM"
        assert vb._spoken_time("00:15") == "12:15 AM"


class TestBookingPromptContext:
    def test_none_when_booking_disabled(self):
        with patch.object(vb, "_booking_enabled", return_value=False):
            assert vb.booking_prompt_context("t1") is None

    def test_none_when_no_slots_anywhere(self):
        with patch.object(vb, "_booking_enabled", return_value=True), patch.object(
            vb, "generate_available_slots", return_value=[]
        ):
            assert vb.booking_prompt_context("t1") is None

    def test_context_carries_marker_and_times(self):
        with patch.object(vb, "_booking_enabled", return_value=True), patch.object(
            vb, "generate_available_slots", return_value=[_slot("09:00"), _slot("14:30")]
        ):
            ctx = vb.booking_prompt_context("t1")
        assert ctx is not None
        assert vb.BOOKING_MARKER in ctx
        assert "9 AM" in ctx and "2:30 PM" in ctx
        assert "24-hour" in ctx


class TestHandleBookingMarker:
    def test_no_marker_passthrough(self):
        text = "We open at nine tomorrow."
        out, appt = vb.handle_booking_marker("t1", "+19145551234", text)
        assert out == text
        assert appt is None

    def test_books_offered_slot_and_strips_marker(self):
        reply = (
            'Great, you are booked for 9 AM. '
            f'{vb.BOOKING_MARKER} {{"name": "Jane Doe", "date": "2026-07-14", "start": "09:00"}}'
        )
        appt_row = {"id": "appt-1", "lead_id": None}
        with patch.object(
            vb, "generate_available_slots", return_value=[_slot("09:00")]
        ), patch.object(vb, "create_appointment", return_value=appt_row) as create, patch.object(
            vb, "_backfill_lead_name"
        ) as backfill:
            out, appt = vb.handle_booking_marker("t1", "+19145551234", reply)
        assert appt == appt_row
        assert vb.BOOKING_MARKER not in out
        assert "Jane" not in out or "BOOK_JSON" not in out
        kwargs = create.call_args.kwargs
        assert kwargs["customer_name"] == "Jane Doe"
        assert kwargs["customer_phone"] == "+19145551234"
        assert kwargs["start_time"] == "2026-07-14T09:00:00+00:00"
        assert kwargs["customer_email"] == ""  # NOT NULL column, no email on a call
        backfill.assert_called_once()

    def test_rejects_time_not_in_open_slots(self):
        reply = (
            'Booked! '
            f'{vb.BOOKING_MARKER} {{"name": "Jane", "date": "2026-07-14", "start": "23:00"}}'
        )
        with patch.object(
            vb, "generate_available_slots", return_value=[_slot("09:00")]
        ), patch.object(vb, "create_appointment") as create:
            out, appt = vb.handle_booking_marker("t1", "+1914", reply)
        assert appt is None
        create.assert_not_called()
        assert vb.BOOKING_MARKER not in out
        assert "call you back" in out

    def test_double_booking_race_degrades_to_callback(self):
        reply = (
            'Done. '
            f'{vb.BOOKING_MARKER} {{"name": "Jane", "date": "2026-07-14", "start": "09:00"}}'
        )
        with patch.object(
            vb, "generate_available_slots", return_value=[_slot("09:00")]
        ), patch.object(
            vb, "create_appointment", side_effect=ValueError("slot taken")
        ):
            out, appt = vb.handle_booking_marker("t1", "+1914", reply)
        assert appt is None
        assert "call you back" in out
        assert vb.BOOKING_MARKER not in out

    def test_malformed_marker_never_raises(self):
        reply = f"Sure. {vb.BOOKING_MARKER} not-json-at-all"
        out, appt = vb.handle_booking_marker("t1", "+1914", reply)
        assert appt is None
        assert vb.BOOKING_MARKER not in out

    def test_incomplete_payload_not_booked(self):
        reply = f'Ok. {vb.BOOKING_MARKER} {{"name": "Jane"}}'
        with patch.object(vb, "create_appointment") as create:
            out, appt = vb.handle_booking_marker("t1", "+1914", reply)
        assert appt is None
        create.assert_not_called()


class TestLeadBackfill:
    def test_sets_name_on_nameless_phone_lead(self):
        lead_row = {"id": "lead-1", "name": None}
        result = MagicMock()
        result.data = [lead_row]
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        chain.update.return_value = chain
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(vb, "get_service_supabase", return_value=db):
            vb._backfill_lead_name("t1", "+19145551234", "Jane Doe", {"id": "appt-1"})
        chain.update.assert_any_call({"name": "Jane Doe"})

    def test_keeps_existing_real_name(self):
        lead_row = {"id": "lead-1", "name": "Existing Name"}
        result = MagicMock()
        result.data = [lead_row]
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        chain.update.return_value = chain
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(vb, "get_service_supabase", return_value=db):
            vb._backfill_lead_name("t1", "+19145551234", "Jane Doe", {"id": "a", "lead_id": "x"})
        for call in chain.update.call_args_list:
            assert call.args[0] != {"name": "Jane Doe"}

    def test_never_raises_on_db_failure(self):
        with patch.object(vb, "get_service_supabase", side_effect=RuntimeError("db down")):
            vb._backfill_lead_name("t1", "+1914", "Jane", {})
