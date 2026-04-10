"""Tests for appointment endpoints — booking, listing, status updates, cancellation.

Uses FastAPI TestClient with mocked Supabase following the same pattern
as test_auth_endpoints.py.  All tests compatible with --timeout=30.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helper: generate a valid JWT for authenticated endpoints
# ---------------------------------------------------------------------------


def _make_jwt(tenant_id: str = "tenant-appt-001", role: str = "owner",
              plan: str = "growth", secret: str = "test-secret-key-for-jwt") -> str:
    """Create a valid JWT bearer token for testing."""
    from jose import jwt
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "owner@example.com",
        "plan": plan,
        "business_name": "Test Biz",
        "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Helper: configure mock table responses (same pattern as other test files)
# ---------------------------------------------------------------------------


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name."""
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

        for method in [
            "select", "insert", "update", "delete", "eq", "neq",
            "gte", "lte", "gt", "lt", "limit", "order", "ilike",
            "in_", "is_", "or_", "contains", "not_",
        ]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


# ---------------------------------------------------------------------------
# Fixture: TestClient with full Supabase mock
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase everywhere."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_helpers.get_service_supabase", return_value=db_mock),
        patch("backend.routers.appointments.get_service_supabase", return_value=db_mock),
        patch("backend.services.booking.get_service_supabase", return_value=db_mock),
        patch("backend.services.activity.get_service_supabase", return_value=db_mock),
        patch("backend.services.webhook_dispatcher.get_service_supabase", return_value=db_mock),
        patch("backend.services.lead_scoring.get_service_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    yield client, db_mock

    # Clear widget module in-memory cache between tests
    try:
        from backend.routers.widget_helpers import _cache
        _cache.clear()
    except Exception:
        pass

    for p in patches:
        p.stop()


# =========================================================================
# Test Group: Appointment Endpoints
# =========================================================================


_TENANT_ID = "tenant-appt-001"
_FUTURE_START = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
_FUTURE_END = (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat()
_PAST_START = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
_PAST_END = (datetime.now(timezone.utc) - timedelta(days=3) + timedelta(hours=1)).isoformat()


class TestCreateAppointmentSuccess:
    """Test POST /{tenant_id} — booking an appointment with valid data."""

    def test_create_appointment_success(self, test_client):
        """POST with valid data returns 200 and appointment details."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            # _get_widget_config looks up widget_configs by api_key
            "widget_configs": [{"tenant_id": _TENANT_ID, "api_key": "anx_test_key"}],
            # create_appointment first checks for overlap, then inserts
            "appointments": [
                [],  # overlap check finds no conflicting appointment
                # First call: insert returns the new appointment
                [{
                    "id": "appt-001",
                    "tenant_id": _TENANT_ID,
                    "customer_name": "Jane Doe",
                    "customer_email": "jane@example.com",
                    "customer_phone": "+15551234567",
                    "start_time": _FUTURE_START,
                    "end_time": _FUTURE_END,
                    "status": "confirmed",
                    "notes": "First visit",
                }],
            ],
            # link_appointment_to_lead queries leads table
            "leads": [
                [],  # no existing lead
                [{"id": "lead-new-001"}],  # insert returns new lead
            ],
            # webhook dispatcher queries webhooks
            "webhooks": [],
        })

        response = client.post(
            f"/api/v1/appointments/{_TENANT_ID}",
            json={
                "api_key": "anx_test_key",
                "customer_name": "Jane Doe",
                "customer_email": "jane@example.com",
                "customer_phone": "+15551234567",
                "start_utc": _FUTURE_START,
                "end_utc": _FUTURE_END,
                "notes": "First visit",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "appt-001"
        assert data["status"] == "confirmed"
        assert data["customer_name"] == "Jane Doe"
        assert data["customer_email"] == "jane@example.com"


class TestCreateAppointmentPastDate:
    """Test POST /{tenant_id} — booking in the past.

    The endpoint does not explicitly block past dates (it relies on slot
    generation to filter), so a direct POST with a past time should still
    succeed at the API level (the DB constraint or slot logic handles it).
    We verify the endpoint does not crash.
    """

    def test_create_appointment_past_date(self, test_client):
        """Booking with a past start time still processes (no 500)."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "widget_configs": [{"tenant_id": _TENANT_ID, "api_key": "anx_test_key"}],
            "appointments": [
                [],  # overlap check
                [{
                    "id": "appt-past-001",
                    "tenant_id": _TENANT_ID,
                    "customer_name": "Past Booker",
                    "customer_email": "past@example.com",
                    "start_time": _PAST_START,
                    "end_time": _PAST_END,
                    "status": "confirmed",
                }],
            ],
            "leads": [[], [{"id": "lead-past-001"}]],
            "webhooks": [],
        })

        response = client.post(
            f"/api/v1/appointments/{_TENANT_ID}",
            json={
                "api_key": "anx_test_key",
                "customer_name": "Past Booker",
                "customer_email": "past@example.com",
                "start_utc": _PAST_START,
                "end_utc": _PAST_END,
            },
        )
        # Endpoint accepts past dates; the slot system is what prevents them
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "appt-past-001"


class TestListAppointments:
    """Test GET /{tenant_id} — listing appointments."""

    def test_list_appointments(self, test_client):
        """GET returns list of appointments for the tenant."""
        client, db_mock = test_client
        token = _make_jwt(tenant_id=_TENANT_ID)

        _setup_table_mock(db_mock, {
            "appointments": [
                {
                    "id": "appt-list-001",
                    "tenant_id": _TENANT_ID,
                    "customer_name": "Alice",
                    "customer_email": "alice@test.com",
                    "start_time": _FUTURE_START,
                    "end_time": _FUTURE_END,
                    "status": "confirmed",
                },
                {
                    "id": "appt-list-002",
                    "tenant_id": _TENANT_ID,
                    "customer_name": "Bob",
                    "customer_email": "bob@test.com",
                    "start_time": _FUTURE_START,
                    "end_time": _FUTURE_END,
                    "status": "completed",
                },
            ],
            "business_hours": [{
                "tenant_id": _TENANT_ID,
                "timezone": "America/Chicago",
                "hours": {},
                "slot_duration_minutes": 30,
                "buffer_minutes": 0,
                "max_advance_days": 30,
            }],
        })

        response = client.get(
            f"/api/v1/appointments/{_TENANT_ID}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "appointments" in data
        assert len(data["appointments"]) == 2
        assert data["timezone"] == "America/Chicago"


class TestAppointmentStatusUpdate:
    """Test PATCH /{tenant_id}/{appointment_id} — updating status."""

    def test_appointment_status_update(self, test_client):
        """Updating status from confirmed to completed returns the updated record."""
        client, db_mock = test_client
        token = _make_jwt(tenant_id=_TENANT_ID)

        _setup_table_mock(db_mock, {
            "appointments": [{
                "id": "appt-upd-001",
                "tenant_id": _TENANT_ID,
                "customer_name": "Charlie",
                "customer_email": "charlie@test.com",
                "start_time": _FUTURE_START,
                "end_time": _FUTURE_END,
                "status": "completed",
                "lead_id": None,
            }],
        })

        response = client.patch(
            f"/api/v1/appointments/{_TENANT_ID}/appt-upd-001",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "completed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["id"] == "appt-upd-001"


class TestAppointmentCancel:
    """Test DELETE /{tenant_id}/{appointment_id} — cancelling an appointment."""

    def test_appointment_cancel(self, test_client):
        """Cancelling sets status to cancelled and returns confirmation."""
        client, db_mock = test_client
        token = _make_jwt(tenant_id=_TENANT_ID)

        _setup_table_mock(db_mock, {
            "appointments": [
                # First call: fetch appointment details (in DELETE handler)
                [{
                    "customer_name": "Diana",
                    "customer_email": "diana@test.com",
                    "start_time": _FUTURE_START,
                    "end_time": _FUTURE_END,
                }],
                # Second call: cancel_appointment -> select google_event_id
                [{"google_event_id": None}],
                # Third call: update_appointment -> update status
                [{
                    "id": "appt-cancel-001",
                    "tenant_id": _TENANT_ID,
                    "customer_name": "Diana",
                    "customer_email": "diana@test.com",
                    "start_time": _FUTURE_START,
                    "end_time": _FUTURE_END,
                    "status": "cancelled",
                }],
            ],
            "webhooks": [],
        })

        response = client.delete(
            f"/api/v1/appointments/{_TENANT_ID}/appt-cancel-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["id"] == "appt-cancel-001"
