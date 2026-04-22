"""TDD tests for attribution_service.

Tests use sys.modules stubs so the backend package can be imported
in environments that only have the stdlib + yaml + pytest installed
(no supabase, httpx, pydantic-settings etc.).
"""

import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-32-characters-ok")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")


_VERTICAL_DEFAULTS = {
    "plumbing": {"avg_ticket": 325, "hours_saved_per_event": 0.5},
    "hvac": {"avg_ticket": 380, "hours_saved_per_event": 0.5},
    "cleaning": {"avg_ticket": 120, "hours_saved_per_event": 0.25},
    "landscaping": {"avg_ticket": 200, "hours_saved_per_event": 0.25},
    "auto_repair": {"avg_ticket": 280, "hours_saved_per_event": 0.5},
    "dental": {"avg_ticket": 450, "hours_saved_per_event": 0.75},
    "default": {"avg_ticket": 200, "hours_saved_per_event": 0.5},
}


class _YamlStub:
    """Minimal yaml stub — safe_load returns the vertical_defaults fixture."""

    def safe_load(self, _stream):
        return {"verticals": _VERTICAL_DEFAULTS}


def _ensure_stubs():
    """Inject minimal sys.modules stubs so backend.* can be imported."""
    stubs = {
        "yaml": _YamlStub(),
        "httpx": MagicMock(),
        "supabase": MagicMock(),
        "pydantic_settings": MagicMock(),
        "sentry_sdk": MagicMock(),
        "sentry_sdk.integrations": MagicMock(),
        "sentry_sdk.integrations.fastapi": MagicMock(),
        "sentry_sdk.integrations.starlette": MagicMock(),
        "jose": MagicMock(),
        "jose.jwt": MagicMock(),
        "bcrypt": MagicMock(),
    }
    for name, stub in stubs.items():
        sys.modules.setdefault(name, stub)

    # pydantic_settings.BaseSettings must be a real class for pydantic to subclass it
    if not hasattr(sys.modules["pydantic_settings"], "BaseSettings"):

        class _BaseSettings:
            model_config = {}

            def __init_subclass__(cls, **kwargs):
                pass

        sys.modules["pydantic_settings"].BaseSettings = _BaseSettings


_ensure_stubs()


# ---------------------------------------------------------------------------
# get_avg_ticket — pure YAML logic, no DB needed
# ---------------------------------------------------------------------------


def test_get_avg_ticket_plumbing():
    import backend.services.attribution_service as svc

    svc._load_defaults.cache_clear()
    assert svc.get_avg_ticket("plumbing") == 325.0


def test_get_avg_ticket_unknown_vertical():
    import backend.services.attribution_service as svc

    svc._load_defaults.cache_clear()
    assert svc.get_avg_ticket("unknown_vertical_xyz") == 200.0


def test_get_avg_ticket_none_vertical():
    import backend.services.attribution_service as svc

    svc._load_defaults.cache_clear()
    assert svc.get_avg_ticket(None) == 200.0


# ---------------------------------------------------------------------------
# compute_dollars_this_month — zero events returns 0.0
# ---------------------------------------------------------------------------


def _make_dollars_mock():
    mock_db = MagicMock()
    tenant_result = MagicMock()
    tenant_result.data = [{"avg_ticket_override": None, "vertical": "plumbing"}]
    (
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value
    ) = tenant_result

    activity_result = MagicMock()
    activity_result.count = 0
    activity_result.data = []
    (
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value
    ) = activity_result
    return mock_db


def test_compute_dollars_zero_events():
    import backend.services.attribution_service as svc

    svc._load_defaults.cache_clear()
    mock_db = _make_dollars_mock()
    with patch.object(svc, "get_service_supabase", return_value=mock_db):
        result = svc.compute_dollars_this_month("test-tenant-id")
    assert result == 0.0


# ---------------------------------------------------------------------------
# compute_hours_this_week — zero events returns 0.0
# ---------------------------------------------------------------------------


def _make_hours_mock():
    mock_db = MagicMock()
    tenant_result = MagicMock()
    tenant_result.data = [{"vertical": "plumbing"}]
    (
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value
    ) = tenant_result

    activity_result = MagicMock()
    activity_result.count = 0
    activity_result.data = []
    (
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value
    ) = activity_result
    return mock_db


def test_compute_hours_zero_events():
    import backend.services.attribution_service as svc

    svc._load_defaults.cache_clear()
    mock_db = _make_hours_mock()
    with patch.object(svc, "get_service_supabase", return_value=mock_db):
        result = svc.compute_hours_this_week("test-tenant-id")
    assert result == 0.0
