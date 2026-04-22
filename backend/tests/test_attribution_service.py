"""TDD tests for backend/services/attribution_service.py.

Written BEFORE the service implementation per TDD rule.
Tests verify: vertical default lookup, override override, zero-event returns $0.

Supabase client mocked via _stub_supabase_singletons (autouse in conftest).
"""

from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# get_avg_ticket
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAvgTicket:
    """get_avg_ticket(tenant_id, vertical) returns correct dollar amount."""

    def test_plumbing_returns_325(self):
        """Plumbing vertical default = $325 per plan spec."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(
            tenant_id="tenant-1", vertical="plumbing", override=None
        )
        assert result == 325

    def test_hvac_returns_380(self):
        """HVAC vertical default = $380 per plan spec."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(tenant_id="tenant-1", vertical="hvac", override=None)
        assert result == 380

    def test_cleaning_returns_120(self):
        """Cleaning vertical default = $120 per plan spec."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(
            tenant_id="tenant-1", vertical="cleaning", override=None
        )
        assert result == 120

    def test_landscaping_returns_200(self):
        """Landscaping vertical default = $200 per plan spec."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(
            tenant_id="tenant-1", vertical="landscaping", override=None
        )
        assert result == 200

    def test_unknown_vertical_returns_global_default_200(self):
        """Unrecognized vertical falls back to global default $200."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(
            tenant_id="tenant-1", vertical="underwater_basket_weaving", override=None
        )
        assert result == 200

    def test_none_vertical_returns_global_default_200(self):
        """None vertical falls back to global default $200."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(tenant_id="tenant-1", vertical=None, override=None)
        assert result == 200

    def test_override_overrides_yaml(self):
        """avg_ticket_override column value wins over YAML default."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(
            tenant_id="tenant-1", vertical="plumbing", override=999.0
        )
        assert result == 999.0

    def test_override_overrides_unknown_vertical(self):
        """Override wins even when vertical is unknown."""
        from backend.services.attribution_service import get_avg_ticket

        result = get_avg_ticket(tenant_id="tenant-1", vertical=None, override=500.0)
        assert result == 500.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_dollars_this_month
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeDollarsThisMonth:
    """compute_dollars_this_month returns sum of avg_ticket * events."""

    def _make_tenant_result(self, mock_db, tenant_row):
        """Wire mock_db to return a tenant row for the tenant lookup."""
        tenant_result = MagicMock()
        tenant_result.data = [tenant_row] if tenant_row else []
        return tenant_result

    def test_zero_events_returns_zero(self, mock_supabase):
        """No activity events this month → $0."""
        # Wire tenant lookup
        tenant_result = MagicMock()
        tenant_result.data = [
            {"id": "t1", "business_type": "plumbing", "avg_ticket_override": None}
        ]
        count_result = MagicMock()
        count_result.count = 0
        count_result.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            tenant_result
        )

        from backend.services.attribution_service import compute_dollars_this_month

        with patch(
            "backend.services.attribution_service._count_events_this_month",
            return_value=0,
        ):
            result = compute_dollars_this_month("t1")

        assert result == 0.0

    def test_one_event_plumbing_returns_325(self, mock_supabase):
        """1 event for plumbing tenant → $325."""
        tenant_result = MagicMock()
        tenant_result.data = [
            {"id": "t1", "business_type": "plumbing", "avg_ticket_override": None}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            tenant_result
        )

        from backend.services.attribution_service import compute_dollars_this_month

        with patch(
            "backend.services.attribution_service._count_events_this_month",
            return_value=1,
        ):
            result = compute_dollars_this_month("t1")

        assert result == 325.0

    def test_three_events_plumbing_returns_975(self, mock_supabase):
        """3 events for plumbing tenant → $975."""
        tenant_result = MagicMock()
        tenant_result.data = [
            {"id": "t1", "business_type": "plumbing", "avg_ticket_override": None}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            tenant_result
        )

        from backend.services.attribution_service import compute_dollars_this_month

        with patch(
            "backend.services.attribution_service._count_events_this_month",
            return_value=3,
        ):
            result = compute_dollars_this_month("t1")

        assert result == 975.0

    def test_override_used_when_set(self, mock_supabase):
        """avg_ticket_override=400 used instead of vertical YAML default."""
        tenant_result = MagicMock()
        tenant_result.data = [
            {"id": "t1", "business_type": "plumbing", "avg_ticket_override": 400.0}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            tenant_result
        )

        from backend.services.attribution_service import compute_dollars_this_month

        with patch(
            "backend.services.attribution_service._count_events_this_month",
            return_value=2,
        ):
            result = compute_dollars_this_month("t1")

        assert result == 800.0

    def test_db_error_returns_zero(self, mock_supabase):
        """DB failure → $0, no raise."""
        mock_supabase.table.side_effect = RuntimeError("DB gone")

        from backend.services.attribution_service import compute_dollars_this_month

        result = compute_dollars_this_month("t1")
        assert result == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_hours_this_week
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeHoursThisWeek:
    """compute_hours_this_week returns hours saved from activity events."""

    def test_zero_events_returns_zero(self, mock_supabase):
        """No events this week → 0.0 hours."""
        from backend.services.attribution_service import compute_hours_this_week

        with patch(
            "backend.services.attribution_service._get_events_this_week",
            return_value=[],
        ):
            result = compute_hours_this_week("t1")

        assert result == 0.0

    def test_one_missed_call_event_returns_quarter_hour(self, mock_supabase):
        """1 missed_call_textback event → 0.25 hours."""
        from backend.services.attribution_service import compute_hours_this_week

        events = [{"activity_type": "missed_call_textback"}]
        with patch(
            "backend.services.attribution_service._get_events_this_week",
            return_value=events,
        ):
            result = compute_hours_this_week("t1")

        assert result == pytest.approx(0.25)

    def test_mixed_events_sum_correctly(self, mock_supabase):
        """Mixed event types sum to correct hours total."""
        from backend.services.attribution_service import compute_hours_this_week

        events = [
            {"activity_type": "missed_call_textback"},  # 0.25
            {"activity_type": "appointment_booked"},  # 0.50
            {"activity_type": "sms_conversation"},  # 0.10
        ]
        with patch(
            "backend.services.attribution_service._get_events_this_week",
            return_value=events,
        ):
            result = compute_hours_this_week("t1")

        assert result == pytest.approx(0.85)

    def test_unknown_event_type_uses_default(self, mock_supabase):
        """Unknown activity_type falls back to default 0.2 hours."""
        from backend.services.attribution_service import compute_hours_this_week

        events = [{"activity_type": "mystery_event"}]
        with patch(
            "backend.services.attribution_service._get_events_this_week",
            return_value=events,
        ):
            result = compute_hours_this_week("t1")

        assert result == pytest.approx(0.2)

    def test_db_error_returns_zero(self, mock_supabase):
        """DB failure → 0.0 hours, no raise."""
        from backend.services.attribution_service import compute_hours_this_week

        with patch(
            "backend.services.attribution_service._get_events_this_week",
            side_effect=RuntimeError("DB gone"),
        ):
            result = compute_hours_this_week("t1")

        assert result == 0.0
