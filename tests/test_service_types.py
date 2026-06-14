"""Tests for service types, form presets, and birthday automation."""

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
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.appointments.get_service_supabase", return_value=db_mock),
        patch("backend.routers.forms.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat_helpers.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead_helpers.get_service_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock
    for p in patches:
        p.stop()


# --- Service Types Tests ---

class TestServiceTypes:
    def test_list_service_types(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"service_types": [
            {"id": "st1", "name": "Haircut", "duration_minutes": 30, "price": 45.0},
        ]})
        resp = client.get("/api/v1/appointments/t1/service-types",
                         headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_create_service_type(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"service_types": [
            {"id": "st2", "name": "Color", "duration_minutes": 120, "price": 150.0},
        ]})
        resp = client.post("/api/v1/appointments/t1/service-types", json={
            "name": "Full Color", "duration_minutes": 120, "price": 150.0,
        }, headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_delete_service_type(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"service_types": [{"id": "st1", "is_active": False}]})
        resp = client.delete("/api/v1/appointments/t1/service-types/st1",
                            headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_public_service_types(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {
            "widget_configs": [{"tenant_id": "t1"}],
            "service_types": [{"id": "st1", "name": "Cleaning", "duration_minutes": 30}],
        })
        resp = client.get("/api/v1/appointments/public/t1/service-types?api_key=test-key")
        assert resp.status_code == 200


# --- Form Presets Tests ---

class TestFormPresets:
    def test_list_presets(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {})
        resp = client.get("/api/v1/forms/t1/presets",
                         headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3  # dental_intake, medical_intake, contractor_estimate

    def test_create_from_preset(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {"forms": [
            {"id": "f1", "name": "New Patient Health History", "public_token": "tok123"},
        ]})
        resp = client.post("/api/v1/forms/t1/presets/dental_intake",
                          headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 200

    def test_create_from_invalid_preset(self, test_client):
        client, db = test_client
        _setup_table_mock(db, {})
        resp = client.post("/api/v1/forms/t1/presets/nonexistent",
                          headers={"Authorization": f"Bearer {_make_jwt()}"})
        assert resp.status_code == 404


# --- Birthday Automation Tests ---

class TestBirthdayAutomation:
    def test_birthday_function_exists(self):
        """Verify the birthday function can be imported."""
        from backend.services.automation_engine import send_birthday_greetings
        assert callable(send_birthday_greetings)

    def test_birthday_filter_logic(self):
        """Verify the month-day matching works."""
        today = datetime.now(timezone.utc).strftime("%m-%d")
        test_leads = [
            {"date_of_birth": f"1990-{today}", "id": "l1", "client_id": "t1", "name": "Birthday Person", "email": "b@e.com"},
            {"date_of_birth": "1990-01-01", "id": "l2", "client_id": "t1", "name": "Not Today", "email": "n@e.com"},
        ]
        birthday_leads = [l for l in test_leads if l.get("date_of_birth", "")[5:10] == today]
        assert len(birthday_leads) == 1
        assert birthday_leads[0]["name"] == "Birthday Person"
