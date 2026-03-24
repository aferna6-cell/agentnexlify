"""Tests for authentication endpoints — signup and login.

These use FastAPI's TestClient with mocked Supabase to test
the register and login flows without hitting the real database.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase everywhere."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    # Patch get_supabase in every module that imports it
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
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


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name.

    table_responses: dict of {table_name: [list of response dicts]}
    Supports chained calls: .select().eq().limit().execute()
    """
    call_counts = {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1

        table = MagicMock()
        data = table_responses.get(name, [])

        # If data is a list of lists, pop the first one each call (multi-call support)
        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data

        # Make all chainable methods return the same mock
        for method in ["select", "insert", "update", "delete", "eq", "neq",
                       "gte", "lte", "gt", "lt", "limit", "order", "ilike",
                       "in_", "is_", "or_", "contains"]:
            getattr(table, method).return_value = table

        # Execute returns the data
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


class TestRegister:
    """Test the POST /api/v1/auth/register endpoint."""

    def test_duplicate_email_returns_409(self, test_client):
        """Signing up with an existing email should return 409."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "tenants": [{"id": "existing-tenant"}],  # duplicate check finds a match
        })

        response = client.post("/api/v1/auth/register", json={
            "email": "existing@example.com",
            "password": "TestPass123!",
            "business_name": "Test Business",
            "owner_name": "Test Owner",
            "industry": "plumbing",
            "city": "New York",
        })
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_successful_register(self, test_client):
        """New email should create tenant and return 200 with token."""
        client, db_mock = test_client

        # First call (duplicate check) returns empty, second call (insert) returns new tenant
        _setup_table_mock(db_mock, {
            "tenants": [
                [],  # first call: no duplicate
                [{"id": "new-tenant-001", "business_name": "Test Biz", "owner_email": "new@example.com", "plan": "free"}],  # second call: insert result
            ],
            "widget_configs": [{"id": "wc-001"}],  # widget config insert
        })

        response = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "TestPass123!",
            "business_name": "Test Biz",
            "owner_name": "Test Owner",
            "industry": "plumbing",
            "city": "New York",
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == "new-tenant-001"
        assert "api_key" in data
        assert data["api_key"].startswith("anx_")


class TestLogin:
    """Test the POST /api/v1/auth/login endpoint."""

    def test_wrong_email_returns_401(self, test_client):
        """Login with non-existent email should return 401."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "tenants": [],
            "team_members": [],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123",
        })
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_wrong_password_returns_401(self, test_client):
        """Login with correct email but wrong password should return 401."""
        client, db_mock = test_client
        import bcrypt
        correct_hash = bcrypt.hashpw(b"CorrectPass123", bcrypt.gensalt()).decode()

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-001",
                "password_hash": correct_hash,
                "business_name": "Test Biz",
                "plan": "free",
            }],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPass123",
        })
        assert response.status_code == 401

    def test_successful_login(self, test_client):
        """Login with correct credentials should return token."""
        client, db_mock = test_client
        import bcrypt
        password = "CorrectPass123!"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-001",
                "password_hash": hashed,
                "business_name": "Test Business",
                "plan": "growth",
            }],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": password,
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == "tenant-001"
        assert data["business_name"] == "Test Business"
        assert data["plan"] == "growth"

    def test_no_password_hash_returns_401(self, test_client):
        """Tenant without password_hash (legacy) should get 401."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-001",
                "password_hash": None,
                "business_name": "Legacy Biz",
                "plan": "free",
            }],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "legacy@example.com",
            "password": "anything",
        })
        assert response.status_code == 401
