"""Tests for backend/services/vertical_preset_loader.py.

Tests:
- get_vertical_preset("plumbing") with mocked Supabase → returns dict with default_services
- get_vertical_preset("unknown") → returns None
- YAML fallback when DB raises exception → still returns data
- list_verticals() → returns list of all 6 vertical names
"""

import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DB_PLUMBING_ROW = {
    "vertical": "plumbing",
    "display_name": "Plumbing",
    "default_services": [
        "Drain Cleaning",
        "Water Heater Installation",
        "Leak Detection & Repair",
    ],
    "default_faqs": [{"q": "Do you offer emergency service?", "a": "Yes, 24/7."}],
    "default_hours": {
        "monday": {"open": "08:00", "close": "18:00"},
        "sunday": None,
    },
    "avg_ticket_amount": 350.00,
    "avg_hours_saved_per_lead": 0.5,
}

_ALL_VERTICALS = [
    "plumbing",
    "hvac",
    "cleaning",
    "power_washing",
    "landscaping",
    "electrical",
]


def _make_supabase_result(data: list):
    """Build a mock Supabase execute() response."""
    result = MagicMock()
    result.data = data
    return result


def _make_supabase_chain(data: list):
    """Build the full fluent chain: table().select().eq().limit().execute()"""
    execute_mock = MagicMock(return_value=_make_supabase_result(data))
    limit_mock = MagicMock()
    limit_mock.execute = execute_mock
    eq_mock = MagicMock()
    eq_mock.limit = MagicMock(return_value=limit_mock)
    select_mock = MagicMock()
    select_mock.eq = MagicMock(return_value=eq_mock)
    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_mock)
    client_mock = MagicMock()
    client_mock.table = MagicMock(return_value=table_mock)
    return client_mock


def _make_supabase_list_chain(data: list):
    """Build chain for list_verticals: table().select().order().execute()"""
    execute_mock = MagicMock(return_value=_make_supabase_result(data))
    order_mock = MagicMock()
    order_mock.execute = execute_mock
    select_mock = MagicMock()
    select_mock.order = MagicMock(return_value=order_mock)
    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_mock)
    client_mock = MagicMock()
    client_mock.table = MagicMock(return_value=table_mock)
    return client_mock


# ---------------------------------------------------------------------------
# get_vertical_preset
# ---------------------------------------------------------------------------


class TestGetVerticalPreset:
    @pytest.mark.asyncio
    async def test_returns_dict_from_db(self):
        """Happy path: DB returns a row, we get it back."""
        client_mock = _make_supabase_chain([_DB_PLUMBING_ROW])

        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            return_value=client_mock,
        ):
            from backend.services.vertical_preset_loader import get_vertical_preset

            result = await get_vertical_preset("plumbing")

        assert result is not None
        assert result["vertical"] == "plumbing"
        assert "Drain Cleaning" in result["default_services"]

    @pytest.mark.asyncio
    async def test_unknown_vertical_returns_none(self):
        """Unrecognised vertical slug → None without hitting DB."""
        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase"
        ) as mock_get:
            from backend.services.vertical_preset_loader import get_vertical_preset

            result = await get_vertical_preset("unknown_trade")

        assert result is None
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_yaml_fallback_on_db_exception(self):
        """DB raises → YAML fallback still returns data."""
        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            side_effect=Exception("DB connection refused"),
        ):
            from backend.services.vertical_preset_loader import get_vertical_preset

            result = await get_vertical_preset("plumbing")

        assert result is not None
        assert result["vertical"] == "plumbing"
        assert isinstance(result["default_services"], list)
        assert len(result["default_services"]) > 0

    @pytest.mark.asyncio
    async def test_yaml_fallback_on_db_miss(self):
        """DB returns empty data → falls back to YAML."""
        client_mock = _make_supabase_chain([])

        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            return_value=client_mock,
        ):
            from backend.services.vertical_preset_loader import get_vertical_preset

            result = await get_vertical_preset("hvac")

        assert result is not None
        assert result["vertical"] == "hvac"

    @pytest.mark.asyncio
    async def test_all_valid_verticals_resolve(self):
        """Every vertical slug in the enum resolves to a non-None result via YAML."""
        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            side_effect=Exception("force YAML"),
        ):
            from backend.services.vertical_preset_loader import get_vertical_preset

            for vertical in _ALL_VERTICALS:
                result = await get_vertical_preset(vertical)
                assert result is not None, f"Expected result for {vertical!r}"
                assert result["vertical"] == vertical


# ---------------------------------------------------------------------------
# list_verticals
# ---------------------------------------------------------------------------


class TestListVerticals:
    @pytest.mark.asyncio
    async def test_returns_list_from_db(self):
        """DB returns rows — list_verticals passes them through."""
        db_rows = [
            {
                "vertical": v,
                "display_name": v.title(),
                "avg_ticket_amount": 100.0,
                "avg_hours_saved_per_lead": 0.5,
            }
            for v in _ALL_VERTICALS
        ]
        client_mock = _make_supabase_list_chain(db_rows)

        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            return_value=client_mock,
        ):
            from backend.services.vertical_preset_loader import list_verticals

            result = await list_verticals()

        assert len(result) == 6
        verticals_returned = {row["vertical"] for row in result}
        assert verticals_returned == set(_ALL_VERTICALS)

    @pytest.mark.asyncio
    async def test_returns_all_6_from_yaml_on_db_error(self):
        """DB fails → YAML fallback returns all 6 verticals."""
        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            side_effect=Exception("DB down"),
        ):
            from backend.services.vertical_preset_loader import list_verticals

            result = await list_verticals()

        assert len(result) == 6
        names = {row["vertical"] for row in result}
        assert names == set(_ALL_VERTICALS)

    @pytest.mark.asyncio
    async def test_each_entry_has_display_name(self):
        """Every entry returned must have a display_name field."""
        with patch(
            "backend.services.vertical_preset_loader.get_service_supabase",
            side_effect=Exception("force YAML"),
        ):
            from backend.services.vertical_preset_loader import list_verticals

            result = await list_verticals()

        for row in result:
            assert "display_name" in row
            assert row["display_name"]  # non-empty


# ---------------------------------------------------------------------------
# _load_yaml_preset (private, tested indirectly via YAML fallback paths above,
# but also directly to cover edge cases)
# ---------------------------------------------------------------------------


class TestLoadYamlPreset:
    def test_unknown_vertical_returns_none(self):
        from backend.services.vertical_preset_loader import _load_yaml_preset

        result = _load_yaml_preset("not_a_real_trade")
        assert result is None

    def test_plumbing_has_required_keys(self):
        from backend.services.vertical_preset_loader import _load_yaml_preset

        result = _load_yaml_preset("plumbing")
        assert result is not None
        for key in (
            "vertical",
            "display_name",
            "default_services",
            "default_faqs",
            "default_hours",
        ):
            assert key in result, f"Missing key: {key}"

    def test_yaml_path_exists(self):
        """YAML_PATH must point to an actual file."""
        from backend.services.vertical_preset_loader import YAML_PATH

        assert YAML_PATH.exists(), f"YAML file not found at {YAML_PATH}"
