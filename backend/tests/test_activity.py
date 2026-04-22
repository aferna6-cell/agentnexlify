"""Tests for backend/services/activity.py read-side functions.

Env vars patched BEFORE any backend import per conftest.py pattern.
Supabase client mocked via the module-level singleton (_stub_supabase_singletons).
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# conftest.py sets TESTING=1 and stubs Supabase singletons before any import.
# The _stub_supabase_singletons fixture is autouse — active for all tests here.


class TestMaskPhone:
    """Unit tests for _mask_phone helper."""

    def test_standard_e164_masked(self):
        from backend.services.activity import _mask_phone
        result = _mask_phone("+12345557890")
        assert result == "+1234****7890"

    def test_no_plus_masked(self):
        from backend.services.activity import _mask_phone
        result = _mask_phone("12345557890")
        assert result == "1234****7890"

    def test_last_four_visible(self):
        from backend.services.activity import _mask_phone
        result = _mask_phone("+12345557890")
        assert result.endswith("7890")

    def test_middle_digits_starred(self):
        from backend.services.activity import _mask_phone
        result = _mask_phone("+12345557890")
        assert "****" in result

    def test_short_number_fallback(self):
        from backend.services.activity import _mask_phone
        result = _mask_phone("5557890")
        assert result.endswith("7890")
        assert "***" in result

    def test_brief_format_plus1234_stars_7890(self):
        """Plan spec mask: +12345557890 -> +1234****7890."""
        from backend.services.activity import _mask_phone
        assert _mask_phone("+12345557890") == "+1234****7890"


class TestGetActivityEvents:
    """Tests for get_activity_events()."""

    def _make_db_mock(self, rows: list) -> MagicMock:
        """Build a MagicMock Supabase client that returns rows."""
        mock_db = MagicMock()
        execute_result = MagicMock()
        execute_result.data = rows
        # Chain: table().select().eq().order().limit().execute()
        (
            mock_db.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result
        return mock_db

    def _make_db_mock_with_since(self, rows: list) -> MagicMock:
        """Build a mock that handles the extra .gte() call when since= is set."""
        mock_db = MagicMock()
        execute_result = MagicMock()
        execute_result.data = rows
        # Chain: table().select().eq().gte().order().limit().execute()
        (
            mock_db.table.return_value
            .select.return_value
            .eq.return_value
            .gte.return_value
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result
        return mock_db

    def _make_db_mock_with_type_filter(self, rows: list) -> MagicMock:
        """Build a mock that handles the extra .eq() for type_filter."""
        mock_db = MagicMock()
        execute_result = MagicMock()
        execute_result.data = rows
        # Chain: table().select().eq(tenant).eq(type).order().limit().execute()
        inner_eq = MagicMock()
        (
            inner_eq
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result
        (
            mock_db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
        ) = inner_eq
        return mock_db

    def test_get_activity_events_returns_tenant_scoped(self, mock_supabase):
        """Events filtered by tenant_id only — no cross-tenant leak."""
        rows = [
            {
                "id": "row-1",
                "tenant_id": "tenant-A",
                "activity_type": "missed_call_textback",
                "description": "Missed call",
                "metadata": {"caller": "+15555550001"},
                "lead_id": None,
                "created_at": "2026-04-22T12:00:00+00:00",
            }
        ]
        # Wire the mock chain
        execute_result = MagicMock()
        execute_result.data = rows
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result

        from backend.services.activity import get_activity_events

        result = get_activity_events("tenant-A")
        assert len(result) == 1
        assert result[0]["tenant_id"] == "tenant-A"
        # Verify eq was called with tenant_id
        mock_supabase.table.return_value.select.return_value.eq.assert_called_with(
            "tenant_id", "tenant-A"
        )

    def test_get_activity_events_masks_phone_last_4(self, mock_supabase):
        """Phone +12345557890 in metadata renders as +1234****7890."""
        rows = [
            {
                "id": "row-1",
                "tenant_id": "tenant-A",
                "activity_type": "missed_call_textback",
                "description": "Missed call",
                "metadata": {"caller": "+12345557890"},
                "lead_id": None,
                "created_at": "2026-04-22T12:00:00+00:00",
            }
        ]
        execute_result = MagicMock()
        execute_result.data = rows
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result

        from backend.services.activity import get_activity_events

        result = get_activity_events("tenant-A")
        assert result[0]["metadata"]["caller"] == "+1234****7890"

    def test_get_activity_events_filter_by_type(self, mock_supabase):
        """type_filter='missed_call_textback' results in second .eq() call."""
        rows = []
        execute_result = MagicMock()
        execute_result.data = rows
        inner_chain = MagicMock()
        (
            inner_chain
            .order.return_value
            .limit.return_value
            .execute.return_value
        ) = execute_result
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
        ) = inner_chain

        from backend.services.activity import get_activity_events

        result = get_activity_events("tenant-A", type_filter="missed_call_textback")
        assert isinstance(result, list)
        # Verify second .eq() was called with activity_type
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.assert_called_with(
            "activity_type", "missed_call_textback"
        )

    def test_get_activity_events_respects_limit(self, mock_supabase):
        """limit=5 passed to .limit() call."""
        execute_result = MagicMock()
        execute_result.data = []
        limit_mock = MagicMock()
        limit_mock.execute.return_value = execute_result
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
        ) = limit_mock

        from backend.services.activity import get_activity_events

        result = get_activity_events("tenant-A", limit=5)
        assert result == []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.assert_called_with(5)

    def test_get_activity_events_returns_empty_on_db_error(self, mock_supabase):
        """DB error returns [] without raising."""
        mock_supabase.table.side_effect = RuntimeError("DB exploded")

        from backend.services.activity import get_activity_events

        result = get_activity_events("tenant-A")
        assert result == []


class TestGetActivityTotals:
    """Tests for get_activity_totals()."""

    def test_get_activity_totals_returns_count(self, mock_supabase):
        """Returns dict with events_count key."""
        execute_result = MagicMock()
        execute_result.count = 3
        execute_result.data = []
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value
        ) = execute_result

        from backend.services.activity import get_activity_totals

        result = get_activity_totals("tenant-A")
        assert "events_count" in result
        assert result["events_count"] == 3

    def test_get_activity_totals_falls_back_to_data_len(self, mock_supabase):
        """When .count is None, falls back to len(data)."""
        execute_result = MagicMock()
        execute_result.count = None
        execute_result.data = [{"id": "a"}, {"id": "b"}]
        (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value
        ) = execute_result

        from backend.services.activity import get_activity_totals

        result = get_activity_totals("tenant-A")
        assert result["events_count"] == 2

    def test_get_activity_totals_returns_zero_on_error(self, mock_supabase):
        """DB error returns {events_count: 0} without raising."""
        mock_supabase.table.side_effect = RuntimeError("DB gone")

        from backend.services.activity import get_activity_totals

        result = get_activity_totals("tenant-A")
        assert result == {"events_count": 0}
