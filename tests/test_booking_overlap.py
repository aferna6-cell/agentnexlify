"""Tests for appointment booking — slot generation and overlap detection."""

import sys
from pathlib import Path
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.booking import (
    generate_available_slots,
    create_appointment,
    link_appointment_to_lead,
)

# ── Test fixtures ────────────────────────────────────────────


MOCK_CONFIG = {
    "timezone": "America/New_York",
    "hours": {
        "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "saturday": {"enabled": False, "start": "09:00", "end": "17:00"},
        "sunday": {"enabled": False, "start": "09:00", "end": "17:00"},
    },
    "slot_duration_minutes": 30,
    "buffer_minutes": 0,
    "max_advance_days": 30,
}


# ── Slot generation tests ───────────────────────────────────


class TestSlotGeneration:
    """Test slot generation logic."""

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_no_config_returns_empty(self, mock_hours, mock_db):
        mock_hours.return_value = None
        slots = generate_available_slots("tenant-1", date(2026, 3, 16))  # Monday
        assert slots == []

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_disabled_day_returns_empty(self, mock_hours, mock_db):
        mock_hours.return_value = MOCK_CONFIG
        # Saturday is disabled
        slots = generate_available_slots("tenant-1", date(2026, 3, 14))  # Saturday
        assert slots == []

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_generates_slots_for_enabled_day(self, mock_hours, mock_db):
        mock_hours.return_value = MOCK_CONFIG

        # Mock DB to return no existing appointments
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_db.return_value.table.return_value = mock_table

        # Use a far future Monday so all slots are in the future
        slots = generate_available_slots("tenant-1", date(2027, 3, 15))  # Monday
        # 9:00 to 17:00 with 30min slots = 16 slots max
        assert len(slots) > 0
        assert len(slots) <= 16
        for slot in slots:
            assert "start" in slot
            assert "end" in slot
            assert "start_utc" in slot
            assert "end_utc" in slot

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_filters_out_booked_slots(self, mock_hours, mock_db):
        """Slots overlapping with existing appointments should be excluded."""
        mock_hours.return_value = MOCK_CONFIG

        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/New_York")
        target = date(2027, 3, 15)  # Monday

        # One existing appointment at 10:00-10:30
        booked_start = datetime(2027, 3, 15, 10, 0, tzinfo=tz).astimezone(timezone.utc)
        booked_end = datetime(2027, 3, 15, 10, 30, tzinfo=tz).astimezone(timezone.utc)

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "start_time": booked_start.isoformat(),
                    "end_time": booked_end.isoformat(),
                },
            ]
        )
        mock_db.return_value.table.return_value = mock_table

        slots = generate_available_slots("tenant-1", target)

        # The 10:00 slot should NOT be in the results
        slot_starts = [s["start"] for s in slots]
        assert "10:00" not in slot_starts

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_buffer_minutes_respected(self, mock_hours, mock_db):
        """Buffer minutes should increase the step between slots."""
        config = {**MOCK_CONFIG, "buffer_minutes": 15}
        mock_hours.return_value = config

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_db.return_value.table.return_value = mock_table

        slots = generate_available_slots("tenant-1", date(2027, 3, 15))
        # With 30min slots + 15min buffer = 45min step: 9:00-17:00 = ~10-11 slots
        assert len(slots) <= 11


# ── Overlap detection tests ──────────────────────────────────


class TestOverlapDetection:
    """Test double-booking prevention at the slot filtering level."""

    def _check_overlap(self, slot_start_utc, slot_end_utc, booked_ranges):
        """Replicating the overlap check from booking.py."""
        s_start = datetime.fromisoformat(slot_start_utc)
        s_end = datetime.fromisoformat(slot_end_utc)
        return any(
            s_start < b_end and s_end > b_start for b_start, b_end in booked_ranges
        )

    def test_no_overlap(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            )
        ]
        # Slot at 15:00-15:30 — no overlap
        assert not self._check_overlap(
            "2027-03-15T15:00:00+00:00",
            "2027-03-15T15:30:00+00:00",
            booked,
        )

    def test_exact_overlap(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            )
        ]
        # Same slot — full overlap
        assert self._check_overlap(
            "2027-03-15T14:00:00+00:00",
            "2027-03-15T14:30:00+00:00",
            booked,
        )

    def test_partial_overlap_start(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            )
        ]
        # Slot 13:45-14:15 overlaps the start
        assert self._check_overlap(
            "2027-03-15T13:45:00+00:00",
            "2027-03-15T14:15:00+00:00",
            booked,
        )

    def test_partial_overlap_end(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            )
        ]
        # Slot 14:15-14:45 overlaps the end
        assert self._check_overlap(
            "2027-03-15T14:15:00+00:00",
            "2027-03-15T14:45:00+00:00",
            booked,
        )

    def test_adjacent_no_overlap(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            )
        ]
        # Slot starts exactly when booked ends — NOT an overlap
        assert not self._check_overlap(
            "2027-03-15T14:30:00+00:00",
            "2027-03-15T15:00:00+00:00",
            booked,
        )

    def test_multiple_booked_ranges(self):
        booked = [
            (
                datetime(2027, 3, 15, 10, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 10, 30, tzinfo=timezone.utc),
            ),
            (
                datetime(2027, 3, 15, 14, 0, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 30, tzinfo=timezone.utc),
            ),
        ]
        # Slot overlapping second booking
        assert self._check_overlap(
            "2027-03-15T14:00:00+00:00",
            "2027-03-15T14:30:00+00:00",
            booked,
        )
        # Slot between bookings — no overlap
        assert not self._check_overlap(
            "2027-03-15T11:00:00+00:00",
            "2027-03-15T11:30:00+00:00",
            booked,
        )

    def test_slot_containing_booking(self):
        booked = [
            (
                datetime(2027, 3, 15, 14, 10, tzinfo=timezone.utc),
                datetime(2027, 3, 15, 14, 20, tzinfo=timezone.utc),
            )
        ]
        # Slot fully contains the booking
        assert self._check_overlap(
            "2027-03-15T14:00:00+00:00",
            "2027-03-15T14:30:00+00:00",
            booked,
        )


# ── Lead linkage tests ───────────────────────────────────────


class TestLeadLinkage:
    """Test that appointments get linked to existing or new leads."""

    @patch("backend.services.booking.get_service_supabase")
    def test_links_to_existing_lead(self, mock_db):
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "lead-123"}])
        mock_db.return_value.table.return_value = mock_table

        result = link_appointment_to_lead(
            "tenant-1",
            {
                "customer_email": "john@test.com",
                "customer_name": "John",
            },
        )
        assert result == "lead-123"

    @patch("backend.services.booking.get_service_supabase")
    def test_no_email_returns_none(self, mock_db):
        result = link_appointment_to_lead("tenant-1", {"customer_name": "John"})
        assert result is None

    @patch("backend.services.booking.get_service_supabase")
    def test_creates_new_lead_when_none_exists(self, mock_db):
        """When no lead exists for the email, creates a new one with client_id."""
        call_count = 0
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table

        def execute_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: no existing lead
                return MagicMock(data=[])
            else:
                # Second call: insert returns new lead
                return MagicMock(data=[{"id": "new-lead-456"}])

        mock_table.execute.side_effect = execute_side_effect
        mock_table.insert.return_value = mock_table
        mock_db.return_value.table.return_value = mock_table

        result = link_appointment_to_lead(
            "tenant-1",
            {
                "customer_email": "new@test.com",
                "customer_name": "New Person",
                "customer_phone": "+15551234567",
            },
        )
        assert result == "new-lead-456"

        # Verify insert was called with client_id (not tenant_id)
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["client_id"] == "tenant-1"
        assert insert_call["status"] == "appointment_booked"


# ── Create appointment tests ─────────────────────────────────


class TestCreateAppointment:
    """Test appointment creation."""

    @patch("backend.services.booking._send_appointment_confirmation")
    @patch("backend.services.booking.link_appointment_to_lead")
    @patch("backend.services.booking.get_service_supabase")
    def test_creates_confirmed_appointment(self, mock_db, mock_link, mock_confirm):
        mock_link.return_value = None
        mock_table = MagicMock()
        for method in ["select", "eq", "neq", "lt", "gt", "limit", "insert"]:
            getattr(mock_table, method).return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(
                data=[
                    {
                        "id": "appt-001",
                        "tenant_id": "tenant-1",
                        "customer_name": "John",
                        "customer_email": "john@test.com",
                        "start_time": "2027-03-15T14:00:00+00:00",
                        "end_time": "2027-03-15T14:30:00+00:00",
                        "status": "confirmed",
                    }
                ]
            ),
        ]
        mock_db.return_value.table.return_value = mock_table

        result = create_appointment(
            tenant_id="tenant-1",
            customer_name="John",
            customer_email="john@test.com",
            start_time="2027-03-15T14:00:00+00:00",
            end_time="2027-03-15T14:30:00+00:00",
        )
        assert result["status"] == "confirmed"
        assert result["id"] == "appt-001"
        mock_confirm.assert_called_once()

        # Verify the insert payload
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["status"] == "confirmed"
        assert insert_call["tenant_id"] == "tenant-1"

    @patch("backend.services.booking.log_activity")
    @patch("backend.services.booking._send_appointment_confirmation")
    @patch("backend.services.booking.link_appointment_to_lead")
    @patch("backend.services.booking.get_service_supabase")
    def test_logs_appointment_booked_activity(
        self, mock_db, mock_link, mock_confirm, mock_log
    ):
        """Booking an appointment emits an activity_log row so the dashboard
        AI-employee card is honest, not empty."""
        mock_link.return_value = "lead-99"
        mock_table = MagicMock()
        for method in ["select", "eq", "neq", "lt", "gt", "limit", "insert", "update"]:
            getattr(mock_table, method).return_value = mock_table
        mock_table.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(
                data=[
                    {
                        "id": "appt-001",
                        "tenant_id": "tenant-1",
                        "customer_name": "John",
                        "customer_email": "john@test.com",
                        "start_time": "2027-03-15T14:00:00+00:00",
                        "end_time": "2027-03-15T14:30:00+00:00",
                        "status": "confirmed",
                    }
                ]
            ),
            MagicMock(data=[]),  # lead-link update
        ]
        mock_db.return_value.table.return_value = mock_table

        create_appointment(
            tenant_id="tenant-1",
            customer_name="John",
            customer_email="john@test.com",
            customer_phone="+12345557890",
            start_time="2027-03-15T14:00:00+00:00",
            end_time="2027-03-15T14:30:00+00:00",
        )

        mock_log.assert_called_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["tenant_id"] == "tenant-1"
        assert kwargs["activity_type"] == "appointment_booked"
        assert kwargs["lead_id"] == "lead-99"
        assert "John" in kwargs["description"]
        assert kwargs["metadata"]["appointment_id"] == "appt-001"
        # Never log the raw phone number in activity metadata.
        assert "+12345557890" not in str(kwargs["metadata"])
