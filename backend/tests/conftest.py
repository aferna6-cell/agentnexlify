"""Shared test fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.main import app


@pytest.fixture()
def client():
    """Unauthenticated test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def mock_supabase():
    """Mock Supabase client to avoid hitting real DB in unit tests."""
    mock = MagicMock()
    with patch("backend.models.database.get_supabase", return_value=mock):
        yield mock


def _make_tenant_row(tenant_id="00000000-0000-0000-0000-000000000001", **overrides):
    """Factory for tenant DB rows."""
    row = {
        "id": tenant_id,
        "business_name": "Test Business",
        "owner_email": "owner@test.com",
        "plan": "growth",
        "plan_status": "active",
        "password_hash": "$2b$12$LJ3m4ys5sE8gR8c8G8v0eOSAkRsF5F5F5F5F5F5F5F5F5F5F5F5F5",
        "business_type": "general",
        "owner_name": "Test Owner",
    }
    row.update(overrides)
    return row


def _make_auth_token(tenant_id="00000000-0000-0000-0000-000000000001"):
    """Create a valid JWT for testing authenticated endpoints."""
    from jose import jwt
    from backend.config import settings
    from datetime import datetime, timedelta, timezone

    payload = {
        "tenant_id": tenant_id,
        "email": "owner@test.com",
        "plan": "growth",
        "business_name": "Test Business",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm="HS256")


@pytest.fixture()
def auth_headers():
    """Authorization headers with valid JWT."""
    token = _make_auth_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_for():
    """Factory: Authorization headers for a specific tenant."""
    def _make(tenant_id):
        token = _make_auth_token(tenant_id)
        return {"Authorization": f"Bearer {token}"}
    return _make
