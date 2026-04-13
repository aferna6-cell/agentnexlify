"""Tests for Cycle 39 quick fixes: holiday hours, lead temperature, score factors.

Tests run with mocked Supabase and no external dependencies.
Compatible with --timeout=30.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fix 1: Holiday/Special Hours — _get_exception_for_date + generate_available_slots
# ---------------------------------------------------------------------------


class TestGetExceptionForDate:
    """Unit tests for _get_exception_for_date helper."""

    def test_no_exceptions_key(self):
        from backend.services.booking import _get_exception_for_date
        hours = {"monday": {"enabled": True, "start": "09:00", "end": "17:00"}}
        result = _get_exception_for_date(hours, date(2026, 12, 25))
        assert result is None

    def test_empty_exceptions_list(self):
        from backend.services.booking import _get_exception_for_date
        hours = {"exceptions": []}
        result = _get_exception_for_date(hours, date(2026, 12, 25))
        assert result is None

    def test_matching_closed_exception(self):
        from backend.services.booking import _get_exception_for_date
        hours = {
            "exceptions": [
                {"date": "2026-12-25", "closed": True},
            ]
        }
        result = _get_exception_for_date(hours, date(2026, 12, 25))
        assert result is not None
        assert result["closed"] is True

    def test_matching_partial_day_exception(self):
        from backend.services.booking import _get_exception_for_date
        hours = {
            "exceptions": [
                {"date": "2026-12-31", "open": "10:00", "close": "14:00"},
            ]
        }
        result = _get_exception_for_date(hours, date(2026, 12, 31))
        assert result is not None
        assert result["open"] == "10:00"
        assert result["close"] == "14:00"

    def test_no_matching_date(self):
        from backend.services.booking import _get_exception_for_date
        hours = {
            "exceptions": [
                {"date": "2026-12-25", "closed": True},
            ]
        }
        result = _get_exception_for_date(hours, date(2026, 12, 26))
        assert result is None

    def test_exceptions_not_a_list(self):
        from backend.services.booking import _get_exception_for_date
        hours = {"exceptions": "not-a-list"}
        result = _get_exception_for_date(hours, date(2026, 12, 25))
        assert result is None

    def test_malformed_exception_entry_skipped(self):
        from backend.services.booking import _get_exception_for_date
        hours = {
            "exceptions": [
                "bad-entry",
                {"date": "2026-12-25", "closed": True},
            ]
        }
        result = _get_exception_for_date(hours, date(2026, 12, 25))
        assert result is not None
        assert result["closed"] is True


class TestGenerateSlotsWithExceptions:
    """Test that generate_available_slots respects exception dates."""

    def _make_config(self, exceptions=None):
        """Build a business_hours config dict."""
        hours = {
            "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "saturday": {"enabled": False, "start": "09:00", "end": "17:00"},
            "sunday": {"enabled": False, "start": "09:00", "end": "17:00"},
        }
        if exceptions:
            hours["exceptions"] = exceptions
        return {
            "tenant_id": "test-tenant",
            "timezone": "UTC",
            "hours": hours,
            "slot_duration_minutes": 60,
            "buffer_minutes": 0,
            "max_advance_days": 90,
        }

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_closed_holiday_returns_no_slots(self, mock_get_bh, mock_db):
        """A date marked closed in exceptions should return zero slots."""
        from backend.services.booking import generate_available_slots

        # 2026-12-25 is a Friday (normally enabled)
        target = date(2026, 12, 25)
        config = self._make_config(exceptions=[
            {"date": "2026-12-25", "closed": True}
        ])
        mock_get_bh.return_value = config

        slots = generate_available_slots("test-tenant", target)
        assert slots == []

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_partial_day_override_limits_slots(self, mock_get_bh, mock_db):
        """A date with open/close override should use those hours instead of normal day hours."""
        from backend.services.booking import generate_available_slots

        # 2026-12-31 is a Wednesday (normally 09:00-17:00 = 8 one-hour slots)
        # Override to 10:00-14:00 = 4 one-hour slots
        target = date(2026, 12, 31)
        config = self._make_config(exceptions=[
            {"date": "2026-12-31", "open": "10:00", "close": "14:00"}
        ])
        mock_get_bh.return_value = config

        # Mock DB for booked appointments query (returns empty)
        db_mock = MagicMock()
        table_mock = MagicMock()
        for method in ["select", "eq", "gte", "lte", "limit", "order"]:
            getattr(table_mock, method).return_value = table_mock
        result_mock = MagicMock()
        result_mock.data = []
        table_mock.execute.return_value = result_mock
        db_mock.table.return_value = table_mock
        mock_db.return_value = db_mock

        slots = generate_available_slots("test-tenant", target)
        # With 60-min slots from 10:00-14:00, we get: 10:00, 11:00, 12:00, 13:00
        # But only future slots are returned; since 2026-12-31 is in the future, all should appear
        assert len(slots) == 4
        assert slots[0]["start"] == "10:00"
        assert slots[-1]["start"] == "13:00"

    @patch("backend.services.booking.get_service_supabase")
    @patch("backend.services.booking.get_business_hours")
    def test_normal_day_unaffected_by_other_exceptions(self, mock_get_bh, mock_db):
        """Days not in exceptions should use normal hours."""
        from backend.services.booking import generate_available_slots

        # 2026-12-29 is a Monday, no exception for it
        target = date(2026, 12, 29)
        config = self._make_config(exceptions=[
            {"date": "2026-12-25", "closed": True}
        ])
        mock_get_bh.return_value = config

        # Mock DB
        db_mock = MagicMock()
        table_mock = MagicMock()
        for method in ["select", "eq", "gte", "lte", "limit", "order"]:
            getattr(table_mock, method).return_value = table_mock
        result_mock = MagicMock()
        result_mock.data = []
        table_mock.execute.return_value = result_mock
        db_mock.table.return_value = table_mock
        mock_db.return_value = db_mock

        slots = generate_available_slots("test-tenant", target)
        # Normal Monday 09:00-17:00 with 60-min slots = 8 slots
        assert len(slots) == 8
        assert slots[0]["start"] == "09:00"


# ---------------------------------------------------------------------------
# Fix 2: lead_temperature Auto-Calculation
# ---------------------------------------------------------------------------


class TestLeadTemperatureCalculation:
    """Test that score_lead sets lead_temperature based on score."""

    def _mock_db(self, lead_data, messages=None):
        """Create a mock DB that returns lead and conversation data."""
        db = MagicMock()
        call_counts = {}

        def mock_table(name):
            call_counts.setdefault(name, 0)
            call_counts[name] += 1

            table = MagicMock()
            for method in [
                "select", "insert", "update", "delete", "eq", "neq",
                "gte", "lte", "limit", "order",
            ]:
                getattr(table, method).return_value = table

            result = MagicMock()

            if name == "leads":
                result.data = [lead_data]
            elif name == "conversations":
                result.data = (
                    [{"session_id": "sess-001", "last_message_at": None}]
                    if messages
                    else []
                )
            elif name == "chat_messages":
                result.data = messages or []
            elif name == "activity_log":
                result.data = [{"id": "log-001"}]
            else:
                result.data = []

            table.execute.return_value = result
            return table

        db.table = mock_table
        return db

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_hot_temperature(self, mock_get_db):
        """Lead with email + phone + pricing + availability + recent = hot."""
        from backend.services.lead_scoring import score_lead

        now_iso = datetime.now(timezone.utc).isoformat()
        lead = {
            "id": "lead-hot-001",
            "client_id": "tenant-001",
            "email": "john@example.com",
            "phone": "+15551234567",
            "name": "John",
            "created_at": now_iso,
            "conversation_id": "conv-001",
        }
        messages = [
            {"role": "user", "content": "What is the price for your service?"},
            {"role": "user", "content": "When are you available?"},
            {"role": "user", "content": "I need this done urgently today"},
            {"role": "user", "content": "Can I book an appointment?"},
        ]
        mock_get_db.return_value = self._mock_db(lead, messages)

        result = score_lead("lead-hot-001")
        assert result["temperature"] == "hot"
        assert result["score"] >= 70

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_warm_temperature(self, mock_get_db):
        """Lead with email + name + some messages = warm."""
        now_iso = datetime.now(timezone.utc).isoformat()
        lead = {
            "id": "lead-warm-001",
            "client_id": "tenant-001",
            "email": "jane@example.com",
            "phone": None,
            "name": "Jane",
            "created_at": now_iso,
            "conversation_id": "conv-002",
        }
        messages = [
            {"role": "user", "content": "What services do you offer?"},
            {"role": "user", "content": "That sounds good"},
            {"role": "user", "content": "I need help with a project"},
            {"role": "user", "content": "Can you tell me more?"},
        ]
        mock_get_db.return_value = self._mock_db(lead, messages)

        from backend.services.lead_scoring import score_lead
        result = score_lead("lead-warm-001")
        assert result["temperature"] == "warm"
        assert 40 <= result["score"] < 70

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_cold_temperature(self, mock_get_db):
        """Lead with minimal info = cold."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        lead = {
            "id": "lead-cold-001",
            "client_id": "tenant-001",
            "email": None,
            "phone": None,
            "name": None,
            "created_at": old_time,
            "conversation_id": None,
        }
        mock_get_db.return_value = self._mock_db(lead)

        from backend.services.lead_scoring import score_lead
        result = score_lead("lead-cold-001")
        assert result["temperature"] == "cold"
        assert result["score"] < 40


# ---------------------------------------------------------------------------
# Fix 4: Lead Score Factors / Explanation
# ---------------------------------------------------------------------------


class TestScoreFactors:
    """Test that score_lead returns human-readable factor explanations."""

    def _mock_db(self, lead_data, messages=None):
        """Create a mock DB."""
        db = MagicMock()

        def mock_table(name):
            table = MagicMock()
            for method in [
                "select", "insert", "update", "delete", "eq", "neq",
                "gte", "lte", "limit", "order",
            ]:
                getattr(table, method).return_value = table

            result = MagicMock()
            if name == "leads":
                result.data = [lead_data]
            elif name == "conversations":
                result.data = (
                    [{"session_id": "sess-001", "last_message_at": None}]
                    if messages
                    else []
                )
            elif name == "chat_messages":
                result.data = messages or []
            elif name == "activity_log":
                result.data = [{"id": "log-001"}]
            else:
                result.data = []
            table.execute.return_value = result
            return table

        db.table = mock_table
        return db

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_factors_include_email_phone(self, mock_get_db):
        """Factors list includes email and phone when present."""
        from backend.services.lead_scoring import score_lead

        now_iso = datetime.now(timezone.utc).isoformat()
        lead = {
            "id": "lead-f-001",
            "client_id": "tenant-001",
            "email": "test@example.com",
            "phone": "+15551234567",
            "name": "Test User",
            "created_at": now_iso,
            "conversation_id": None,
        }
        mock_get_db.return_value = self._mock_db(lead)

        result = score_lead("lead-f-001")
        assert "factors" in result
        factor_texts = result["factors"]
        assert any("Has email" in f for f in factor_texts)
        assert any("Has phone" in f for f in factor_texts)
        assert any("Has name" in f for f in factor_texts)

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_factors_include_intent_keywords(self, mock_get_db):
        """Factors list includes intent keywords when user asked about pricing."""
        from backend.services.lead_scoring import score_lead

        now_iso = datetime.now(timezone.utc).isoformat()
        lead = {
            "id": "lead-f-002",
            "client_id": "tenant-001",
            "email": "user@example.com",
            "phone": None,
            "name": None,
            "created_at": now_iso,
            "conversation_id": "conv-f-002",
        }
        messages = [
            {"role": "user", "content": "How much does it cost?"},
        ]
        mock_get_db.return_value = self._mock_db(lead, messages)

        result = score_lead("lead-f-002")
        factor_texts = result["factors"]
        assert any("pricing" in f.lower() for f in factor_texts)

    @patch("backend.services.lead_scoring.get_service_supabase")
    def test_factors_returned_in_result(self, mock_get_db):
        """Result dict always has factors and temperature keys."""
        from backend.services.lead_scoring import score_lead

        now_iso = datetime.now(timezone.utc).isoformat()
        lead = {
            "id": "lead-f-003",
            "client_id": "tenant-001",
            "email": None,
            "phone": None,
            "name": None,
            "created_at": now_iso,
            "conversation_id": None,
        }
        mock_get_db.return_value = self._mock_db(lead)

        result = score_lead("lead-f-003")
        assert "factors" in result
        assert "temperature" in result
        assert isinstance(result["factors"], list)
        assert result["temperature"] in ("hot", "warm", "cold")
