"""Tests for automation extras: aftercare, rebook, birthday, lead sources."""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_jwt(tenant_id="t1", role="owner", secret="test-secret-key-for-jwt"):
    from jose import jwt
    payload = {
        "tenant_id": tenant_id, "sub": tenant_id, "email": "o@e.com",
        "plan": "professional", "business_name": "Test Biz", "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _setup_table_mock(db_mock, table_responses):
    call_counts = {}
    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1
        table = MagicMock()
        data = table_responses.get(name, [])
        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data
        for m in ["select", "insert", "update", "delete", "eq", "neq", "gte", "lte",
                  "gt", "lt", "limit", "order", "ilike", "in_", "is_", "or_", "contains", "not_"]:
            getattr(table, m).return_value = table
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result
        return table
    db_mock.table = mock_table


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.analytics.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_helpers.get_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock
    for p in patches:
        p.stop()


# --- Aftercare Template Tests ---

class TestAftercareTemplates:
    def test_aftercare_templates_exist(self):
        from backend.services.automation_engine import _AFTERCARE_TEMPLATES
        assert "dental" in _AFTERCARE_TEMPLATES
        assert "salon" in _AFTERCARE_TEMPLATES
        assert "fitness" in _AFTERCARE_TEMPLATES

    def test_dental_has_procedure_variants(self):
        from backend.services.automation_engine import _AFTERCARE_TEMPLATES
        dental = _AFTERCARE_TEMPLATES["dental"]
        assert "default" in dental
        assert "cleaning" in dental
        assert "filling" in dental
        assert "extraction" in dental
        assert "root canal" in dental

    def test_aftercare_function_importable(self):
        from backend.services.automation_engine import send_aftercare_instructions
        assert callable(send_aftercare_instructions)


# --- Rebook Tests ---

class TestRebookIntervals:
    def test_rebook_intervals_exist(self):
        from backend.services.automation_engine import _REBOOK_INTERVALS
        assert "dental" in _REBOOK_INTERVALS
        assert _REBOOK_INTERVALS["dental"][0] == 180  # days
        assert "salon" in _REBOOK_INTERVALS
        assert _REBOOK_INTERVALS["salon"][0] == 42  # days

    def test_rebook_function_importable(self):
        from backend.services.automation_engine import send_rebook_suggestions
        assert callable(send_rebook_suggestions)


# --- Reminder Extras Tests ---

class TestReminderExtras:
    def test_dental_extras(self):
        from backend.services.automation_engine import _get_reminder_extras
        extras = _get_reminder_extras("dental", "")
        assert "Insurance card" in extras
        assert "Photo ID" in extras

    def test_dental_root_canal_adds_ride(self):
        from backend.services.automation_engine import _get_reminder_extras
        extras = _get_reminder_extras("dental", "Service: Root Canal")
        assert any("ride" in e.lower() for e in extras)

    def test_dental_cleaning_adds_floss(self):
        from backend.services.automation_engine import _get_reminder_extras
        extras = _get_reminder_extras("dental", "Service: Cleaning")
        assert any("floss" in e.lower() for e in extras)

    def test_unknown_type_returns_empty(self):
        from backend.services.automation_engine import _get_reminder_extras
        extras = _get_reminder_extras("unknown_business", "")
        assert extras == []


# --- Lead Source Analytics Tests ---

class TestLeadSourceAnalytics:
    def test_lead_sources_endpoint(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"leads": [
            {"source": "widget"},
            {"source": "widget"},
            {"source": "booking"},
            {"source": "missed_call"},
        ]})
        # Clear cache
        from backend.routers.analytics import _cache
        _cache.clear()

        resp = client.get("/api/v1/analytics/t1/lead-sources",
                         headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "breakdown" in data
        assert data["total"] == 4

    def test_lead_sources_empty(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"leads": []})
        from backend.routers.analytics import _cache
        _cache.clear()

        resp = client.get("/api/v1/analytics/t1/lead-sources",
                         headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
