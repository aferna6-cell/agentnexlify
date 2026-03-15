"""Tests for Google Calendar OAuth integration endpoints.

Validates the status check and disconnect endpoints with mocked Supabase,
following the same patterns as test_auth_endpoints.py and test_appointments.py.
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

_TENANT_ID = "tenant-gcal-001"


def _make_jwt(tenant_id: str = _TENANT_ID, role: str = "owner",
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
# Helper: configure mock table responses
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
        patch("backend.routers.auth.get_supabase", return_value=db_mock),
        patch("backend.routers.widget.get_supabase", return_value=db_mock),
        patch("backend.services.google_calendar.get_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    yield client, db_mock

    for p in patches:
        p.stop()


# =========================================================================
# Tests
# =========================================================================


class TestGcalStatusNotConnected:
    """GET /api/v1/integrations/google/status when no integration exists."""

    def test_gcal_status_not_connected(self, test_client):
        """Should return connected=false when no integration row exists."""
        client, db_mock = test_client
        token = _make_jwt()

        # integrations table returns empty — no Google Calendar row
        _setup_table_mock(db_mock, {
            "integrations": [],
        })

        response = client.get(
            "/api/v1/integrations/google/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["email"] is None
        assert data["calendar_name"] is None


class TestGcalDisconnect:
    """DELETE /api/v1/integrations/google when no integration exists."""

    def test_gcal_disconnect(self, test_client):
        """Should return gracefully even when no integration row exists."""
        client, db_mock = test_client
        token = _make_jwt()

        # delete_integration calls db.table("integrations").delete().eq().eq().execute()
        # Even with no rows, the delete should succeed gracefully
        _setup_table_mock(db_mock, {
            "integrations": [],
        })

        response = client.delete(
            "/api/v1/integrations/google",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disconnected"


class TestGcalStatusConnected:
    """GET /api/v1/integrations/google/status when integration row exists."""

    def test_gcal_status_connected(self, test_client):
        """Should return connected=true with email when integration exists."""
        client, db_mock = test_client
        token = _make_jwt()

        _setup_table_mock(db_mock, {
            "integrations": [{
                "id": "integration-001",
                "tenant_id": _TENANT_ID,
                "provider": "google_calendar",
                "access_token": "ya29.fake-access-token",
                "refresh_token": "1//fake-refresh-token",
                "token_expiry": "2026-12-31T23:59:59Z",
                "metadata": {
                    "email": "owner@gmail.com",
                    "calendar_name": "Primary",
                },
            }],
        })

        response = client.get(
            "/api/v1/integrations/google/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["email"] == "owner@gmail.com"
        assert data["calendar_name"] == "Primary"
