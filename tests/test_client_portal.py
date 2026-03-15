"""Tests for Client Portal endpoints — service records, portal links, and public portal."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_TEST_JWT_SECRET = "test-secret-key-for-jwt"


# ── Helper: create a valid JWT for tests ──────────────────────

def _make_token(tenant_id: str = "tenant-001") -> str:
    """Create a JWT signed with the test secret key."""
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "email": "owner@example.com",
        "plan": "growth",
        "business_name": "Test Biz",
        "role": "owner",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name.

    table_responses: dict of {table_name: data}
    - data can be a list of dicts (returned for every call)
    - data can be a list of lists (each call pops the next sub-list)
    """
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
            "in_", "is_", "or_", "contains",
        ]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    mock_settings.api_secret_key = _TEST_JWT_SECRET

    db_mock = MagicMock()

    # Create a mock settings object that auth.settings will use for JWT decode
    auth_settings_mock = MagicMock()
    auth_settings_mock.api_secret_key = _TEST_JWT_SECRET

    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", auth_settings_mock),
        patch("backend.routers.client_portal.get_supabase", return_value=db_mock),
        patch("backend.routers.widget.get_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    yield client, db_mock

    for p in patches:
        p.stop()


# ── Service Record CRUD Tests ─────────────────────────────────


class TestCreateServiceRecord:
    """Test POST /{tenant_id}/service-records."""

    def test_create_success(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [{"id": "sr-001", "tenant_id": "tenant-001", "title": "Oil Change"}],
        })

        resp = client.post(
            "/api/v1/portal/tenant-001/service-records",
            json={"title": "Oil Change", "invoice_amount": 49.99},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "sr-001"
        assert data["title"] == "Oil Change"

    def test_create_unauthorized(self, test_client):
        client, db_mock = test_client
        token = _make_token(tenant_id="other-tenant")

        resp = client.post(
            "/api/v1/portal/tenant-001/service-records",
            json={"title": "Oil Change"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_create_no_auth(self, test_client):
        client, _ = test_client

        resp = client.post(
            "/api/v1/portal/tenant-001/service-records",
            json={"title": "Oil Change"},
        )
        assert resp.status_code == 422  # Missing Authorization header


class TestListServiceRecords:
    """Test GET /{tenant_id}/service-records."""

    def test_list_success(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [
                {"id": "sr-001", "title": "Oil Change"},
                {"id": "sr-002", "title": "Tire Rotation"},
            ],
        })

        resp = client.get(
            "/api/v1/portal/tenant-001/service-records",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["service_records"]) == 2

    def test_list_with_lead_filter(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [{"id": "sr-001", "title": "Oil Change"}],
        })

        resp = client.get(
            "/api/v1/portal/tenant-001/service-records?lead_id=lead-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


class TestUpdateServiceRecord:
    """Test PUT /{tenant_id}/service-records/{record_id}."""

    def test_update_success(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [{"id": "sr-001", "title": "Updated Title"}],
        })

        resp = client.put(
            "/api/v1/portal/tenant-001/service-records/sr-001",
            json={"title": "Updated Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_no_fields(self, test_client):
        """Empty update body should return 400."""
        client, db_mock = test_client
        token = _make_token()

        resp = client.put(
            "/api/v1/portal/tenant-001/service-records/sr-001",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "No fields" in resp.json()["detail"]

    def test_update_not_found(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [],  # empty = not found
        })

        resp = client.put(
            "/api/v1/portal/tenant-001/service-records/nonexistent",
            json={"title": "Will Not Work"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestDeleteServiceRecord:
    """Test DELETE /{tenant_id}/service-records/{record_id}."""

    def test_delete_success(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [{"id": "sr-001"}],
        })

        resp = client.delete(
            "/api/v1/portal/tenant-001/service-records/sr-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    def test_delete_not_found(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "service_records": [],
        })

        resp = client.delete(
            "/api/v1/portal/tenant-001/service-records/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ── Portal Link Tests ──────────────────────────────────────────


class TestGeneratePortalLink:
    """Test POST /{tenant_id}/portal-link/{lead_id}."""

    def test_generate_new_token(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "portal_tokens": [
                [],  # first call: no existing token
                [{"token": "new-token-xyz"}],  # second call: insert result
            ],
        })

        resp = client.post(
            "/api/v1/portal/tenant-001/portal-link/lead-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "url" in data
        assert data["url"].startswith("https://agentnexlify.vercel.app/client/")

    def test_return_existing_token(self, test_client):
        client, db_mock = test_client
        token = _make_token()

        _setup_table_mock(db_mock, {
            "portal_tokens": [{"token": "existing-abc123"}],
        })

        resp = client.post(
            "/api/v1/portal/tenant-001/portal-link/lead-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "existing-abc123"
        assert data["url"] == "https://agentnexlify.vercel.app/client/existing-abc123"


# ── Public Portal Tests ────────────────────────────────────────


class TestPublicPortal:
    """Test GET /portal/{token} — public, no auth."""

    def test_portal_success(self, test_client):
        client, db_mock = test_client

        call_idx = {"n": 0}
        table_data = {
            "portal_tokens": [{"tenant_id": "tenant-001", "lead_id": "lead-001", "token": "abc"}],
            "tenants": [{"id": "tenant-001", "business_name": "Test Biz", "owner_email": "a@b.com", "industry": "auto", "city": "NYC"}],
            "leads": [{"id": "lead-001", "name": "Jane", "email": "jane@x.com", "phone": "555-1234"}],
            "service_records": [{"id": "sr-001", "title": "Oil Change"}],
            "widget_configs": [{"booking_enabled": True}],
        }

        def mock_table(name):
            table = MagicMock()
            data = table_data.get(name, [])
            for method in [
                "select", "insert", "update", "delete", "eq", "neq",
                "gte", "lte", "gt", "lt", "limit", "order", "ilike",
                "in_", "is_", "or_", "contains",
            ]:
                getattr(table, method).return_value = table
            result = MagicMock()
            result.data = data
            result.count = len(data)
            table.execute.return_value = result
            return table

        db_mock.table = mock_table

        resp = client.get("/api/v1/portal/portal/abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["business"]["business_name"] == "Test Biz"
        assert data["customer"]["name"] == "Jane"
        assert len(data["service_records"]) == 1
        assert data["rebook_enabled"] is True

    def test_portal_invalid_token(self, test_client):
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "portal_tokens": [],
        })

        resp = client.get("/api/v1/portal/portal/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_portal_booking_disabled(self, test_client):
        """When booking_enabled is false, rebook_enabled should be false."""
        client, db_mock = test_client

        table_data = {
            "portal_tokens": [{"tenant_id": "t1", "lead_id": "l1", "token": "tok"}],
            "tenants": [{"id": "t1", "business_name": "Biz"}],
            "leads": [{"id": "l1", "name": "Bob"}],
            "service_records": [],
            "widget_configs": [{"booking_enabled": False}],
        }

        def mock_table(name):
            table = MagicMock()
            data = table_data.get(name, [])
            for method in [
                "select", "insert", "update", "delete", "eq", "neq",
                "gte", "lte", "gt", "lt", "limit", "order", "ilike",
                "in_", "is_", "or_", "contains",
            ]:
                getattr(table, method).return_value = table
            result = MagicMock()
            result.data = data
            result.count = len(data)
            table.execute.return_value = result
            return table

        db_mock.table = mock_table

        resp = client.get("/api/v1/portal/portal/tok")
        assert resp.status_code == 200
        assert resp.json()["rebook_enabled"] is False
