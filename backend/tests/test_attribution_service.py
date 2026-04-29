"""Tests for attribution_service — dollar/hours attribution from activity_log.

Slice 1 of ops-automation Phase 2. Tests written FIRST per TDD.

Locked defaults (per plan §Phase 2):
- avg_ticket precedence: tenants.avg_ticket_override → vertical default → 200
- Dollars window: current calendar month (UTC)
- Hours window: ISO week (Mon-Sun UTC)
- Hours formula: missed_call_textback=8, appointment_booked=15,
  lead_captured=5, no_show_recovered=10, default=5
- YAML loaded via functools.lru_cache
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


TENANT_ID = "00000000-0000-0000-0000-000000000010"


def _build_tenant_query_mock(rows: list[dict]) -> MagicMock:
    """Build the chain mock for `db.table('tenants').select(...).eq(...).limit(1).execute()`."""
    chain = MagicMock()
    execute_result = MagicMock()
    execute_result.data = rows
    (
        chain.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = execute_result
    return chain


def _build_activity_query_mock(rows: list[dict]) -> MagicMock:
    """Build the chain mock for `db.table('activity_log').select(...).eq(...).gte(...).execute()`."""
    chain = MagicMock()
    execute_result = MagicMock()
    execute_result.data = rows
    (
        chain.table.return_value
        .select.return_value
        .eq.return_value
        .gte.return_value
        .execute.return_value
    ) = execute_result
    return chain


def _build_dual_table_mock(tenant_rows: list[dict], activity_rows: list[dict]) -> MagicMock:
    """Build a mock that routes tenants vs activity_log to different chains."""
    db = MagicMock()

    tenant_execute = MagicMock()
    tenant_execute.data = tenant_rows
    tenant_chain = MagicMock()
    (
        tenant_chain.select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = tenant_execute

    activity_execute = MagicMock()
    activity_execute.data = activity_rows
    activity_chain = MagicMock()
    (
        activity_chain.select.return_value
        .eq.return_value
        .gte.return_value
        .execute.return_value
    ) = activity_execute

    def _route(table_name: str):
        if table_name == "tenants":
            return tenant_chain
        if table_name == "activity_log":
            return activity_chain
        raise AssertionError(f"unexpected table {table_name}")

    db.table.side_effect = _route
    return db


@pytest.fixture(autouse=True)
def _clear_yaml_cache():
    """Reset lru_cache between tests to avoid cross-test leakage."""
    from backend.services import attribution_service

    attribution_service._load_vertical_defaults.cache_clear()
    attribution_service._load_hours_formula.cache_clear()
    yield
    attribution_service._load_vertical_defaults.cache_clear()
    attribution_service._load_hours_formula.cache_clear()


class TestGetAvgTicket:
    def test_tenant_override_wins_over_vertical(self, mock_supabase):
        from backend.services.attribution_service import get_avg_ticket

        rows = [{"avg_ticket_override": 999.99, "business_type": "plumbing"}]
        chain = _build_tenant_query_mock(rows)
        mock_supabase.table.side_effect = chain.table.side_effect
        mock_supabase.table = chain.table

        result = get_avg_ticket(TENANT_ID)

        assert result == Decimal("999.99")
        assert isinstance(result, Decimal)

    def test_vertical_default_when_no_override(self, mock_supabase):
        from backend.services.attribution_service import get_avg_ticket

        rows = [{"avg_ticket_override": None, "business_type": "plumbing"}]
        chain = _build_tenant_query_mock(rows)
        mock_supabase.table = chain.table

        result = get_avg_ticket(TENANT_ID)

        # plumbing default per locked config: 325
        assert result == Decimal("325")

    def test_unknown_vertical_falls_back_to_default(self, mock_supabase):
        from backend.services.attribution_service import get_avg_ticket

        rows = [{"avg_ticket_override": None, "business_type": "tutoring"}]
        chain = _build_tenant_query_mock(rows)
        mock_supabase.table = chain.table

        result = get_avg_ticket(TENANT_ID)

        # tutoring not in seeded list → default 200
        assert result == Decimal("200")

    def test_missing_tenant_row_returns_default(self, mock_supabase):
        from backend.services.attribution_service import get_avg_ticket

        chain = _build_tenant_query_mock([])
        mock_supabase.table = chain.table

        result = get_avg_ticket(TENANT_ID)

        assert result == Decimal("200")

    def test_null_business_type_returns_default(self, mock_supabase):
        from backend.services.attribution_service import get_avg_ticket

        rows = [{"avg_ticket_override": None, "business_type": None}]
        chain = _build_tenant_query_mock(rows)
        mock_supabase.table = chain.table

        result = get_avg_ticket(TENANT_ID)

        assert result == Decimal("200")


class TestComputeDollarsThisMonth:
    def test_zero_when_no_events(self, mock_supabase):
        from backend.services.attribution_service import compute_dollars_this_month

        db = _build_dual_table_mock(
            tenant_rows=[{"avg_ticket_override": None, "business_type": "plumbing"}],
            activity_rows=[],
        )
        mock_supabase.table = db.table

        result = compute_dollars_this_month(TENANT_ID)

        assert result == Decimal("0")
        assert isinstance(result, Decimal)

    def test_one_missed_call_returns_avg_ticket(self, mock_supabase):
        """Plan gate: tenant w/ 1 missed call → $325 for plumbing."""
        from backend.services.attribution_service import compute_dollars_this_month

        db = _build_dual_table_mock(
            tenant_rows=[{"avg_ticket_override": None, "business_type": "plumbing"}],
            activity_rows=[{"id": "e1", "activity_type": "missed_call_textback"}],
        )
        mock_supabase.table = db.table

        result = compute_dollars_this_month(TENANT_ID)

        assert result == Decimal("325")

    def test_multiple_events_multiply_avg_ticket(self, mock_supabase):
        from backend.services.attribution_service import compute_dollars_this_month

        db = _build_dual_table_mock(
            tenant_rows=[{"avg_ticket_override": 100, "business_type": "salon"}],
            activity_rows=[
                {"id": "e1", "activity_type": "missed_call_textback"},
                {"id": "e2", "activity_type": "appointment_booked"},
                {"id": "e3", "activity_type": "lead_captured"},
            ],
        )
        mock_supabase.table = db.table

        result = compute_dollars_this_month(TENANT_ID)

        assert result == Decimal("300")

    def test_uses_calendar_month_start_utc(self, mock_supabase):
        """Verify the .gte filter argument is start of current calendar month UTC."""
        from backend.services.attribution_service import compute_dollars_this_month

        tenant_execute = MagicMock()
        tenant_execute.data = [{"avg_ticket_override": None, "business_type": "plumbing"}]
        tenant_chain = MagicMock()
        (
            tenant_chain.select.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ) = tenant_execute

        activity_execute = MagicMock()
        activity_execute.data = []
        activity_chain = MagicMock()
        gte_mock = MagicMock()
        (
            activity_chain.select.return_value
            .eq.return_value
            .gte.return_value
        ) = gte_mock
        gte_mock.execute.return_value = activity_execute

        def _route(table_name: str):
            return tenant_chain if table_name == "tenants" else activity_chain

        mock_supabase.table.side_effect = _route

        compute_dollars_this_month(TENANT_ID)

        # Inspect the .gte call
        gte_args = activity_chain.select.return_value.eq.return_value.gte.call_args
        assert gte_args is not None
        column, iso_value = gte_args[0]
        assert column == "created_at"
        parsed = datetime.fromisoformat(iso_value)
        now = datetime.now(timezone.utc)
        assert parsed.tzinfo is not None
        assert parsed.year == now.year
        assert parsed.month == now.month
        assert parsed.day == 1
        assert parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0


class TestComputeHoursThisWeek:
    def test_zero_when_no_events(self, mock_supabase):
        from backend.services.attribution_service import compute_hours_this_week

        chain = _build_activity_query_mock([])
        mock_supabase.table = chain.table

        result = compute_hours_this_week(TENANT_ID)

        assert result == Decimal("0")
        assert isinstance(result, Decimal)

    def test_known_event_types_use_formula(self, mock_supabase):
        """8 + 15 + 5 + 10 = 38 minutes = 0.63 hours."""
        from backend.services.attribution_service import compute_hours_this_week

        chain = _build_activity_query_mock(
            [
                {"activity_type": "missed_call_textback"},
                {"activity_type": "appointment_booked"},
                {"activity_type": "lead_captured"},
                {"activity_type": "no_show_recovered"},
            ]
        )
        mock_supabase.table = chain.table

        result = compute_hours_this_week(TENANT_ID)

        # 38/60 = 0.6333... → quantize to 0.63
        assert result == Decimal("0.63")

    def test_unknown_event_type_uses_default_minutes(self, mock_supabase):
        """default 5 min × 2 events = 10 min = 0.17 hours."""
        from backend.services.attribution_service import compute_hours_this_week

        chain = _build_activity_query_mock(
            [
                {"activity_type": "weird_unmapped_event"},
                {"activity_type": "another_weird_event"},
            ]
        )
        mock_supabase.table = chain.table

        result = compute_hours_this_week(TENANT_ID)

        assert result == Decimal("0.17")

    def test_uses_iso_week_start_utc(self, mock_supabase):
        """Verify the .gte filter is Monday 00:00 UTC of the current ISO week."""
        from backend.services.attribution_service import compute_hours_this_week

        execute_result = MagicMock()
        execute_result.data = []
        chain = MagicMock()
        gte_mock = MagicMock()
        (
            chain.select.return_value
            .eq.return_value
            .gte.return_value
        ) = gte_mock
        gte_mock.execute.return_value = execute_result
        mock_supabase.table = MagicMock(return_value=chain)

        compute_hours_this_week(TENANT_ID)

        gte_args = chain.select.return_value.eq.return_value.gte.call_args
        assert gte_args is not None
        column, iso_value = gte_args[0]
        assert column == "created_at"
        parsed = datetime.fromisoformat(iso_value)
        assert parsed.tzinfo is not None
        # Monday = weekday 0
        assert parsed.weekday() == 0
        assert parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0
        # Within the last 7 days
        delta = datetime.now(timezone.utc) - parsed
        assert 0 <= delta.days <= 6


class TestYamlCaching:
    def test_vertical_defaults_loaded_once(self, mock_supabase):
        from backend.services import attribution_service

        attribution_service._load_vertical_defaults.cache_clear()

        a = attribution_service._load_vertical_defaults()
        b = attribution_service._load_vertical_defaults()

        # Same dict object → cached
        assert a is b
        assert attribution_service._load_vertical_defaults.cache_info().hits >= 1

    def test_hours_formula_loaded_once(self, mock_supabase):
        from backend.services import attribution_service

        attribution_service._load_hours_formula.cache_clear()

        a = attribution_service._load_hours_formula()
        b = attribution_service._load_hours_formula()

        assert a is b
        assert attribution_service._load_hours_formula.cache_info().hits >= 1

    def test_yaml_files_have_required_keys(self):
        from backend.services import attribution_service

        verticals = attribution_service._load_vertical_defaults()
        formula = attribution_service._load_hours_formula()

        # Locked defaults
        assert verticals.get("default") == 200
        assert verticals.get("plumbing") == 325
        assert verticals.get("hvac") == 450
        assert verticals.get("salon") == 100

        assert formula.get("default_minutes") == 5
        per_type = formula.get("minutes_per_event_type", {})
        assert per_type.get("missed_call_textback") == 8
        assert per_type.get("appointment_booked") == 15
        assert per_type.get("lead_captured") == 5
        assert per_type.get("no_show_recovered") == 10
