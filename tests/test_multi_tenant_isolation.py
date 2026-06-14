"""Tests for multi-tenant data isolation.

Verifies that Tenant A cannot access Tenant B's data across all major
data models. This is the single most critical security property of the platform.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


TENANT_A_ID = "tenant-aaa-111"
TENANT_B_ID = "tenant-bbb-222"


def _make_token(tenant_id, secret="test-secret-key-for-jwt", role="owner"):
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": f"owner@{tenant_id}.com",
        "plan": "professional",
        "business_name": f"Biz {tenant_id}",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        # billing endpoints moved to auth_billing (2026-06-11 god-file split)
        patch("backend.routers.auth_billing.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth_billing.settings", mock_settings),
        patch("backend.routers.leads.get_service_supabase", return_value=db_mock),
        patch("backend.routers.appointments.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat_helpers.get_service_supabase", return_value=db_mock),
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

    try:
        from backend.limiter import limiter
        limiter.reset()
    except Exception:
        pass

    for p in patches:
        p.stop()


class TestTenantIsolationLeads:
    """Tenant A cannot see or modify Tenant B's leads."""

    def test_tenant_a_cannot_list_tenant_b_leads(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/leads/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403

    def test_tenant_a_cannot_update_tenant_b_lead(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.patch(
            f"/api/v1/leads/{TENANT_B_ID}/lead-1",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Hacked Name"},
        )
        assert response.status_code == 403


class TestTenantIsolationConversations:
    """Tenant A cannot see Tenant B's conversations."""

    def test_tenant_a_cannot_list_tenant_b_conversations(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/auth/conversations/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403

    def test_tenant_a_cannot_read_tenant_b_conversation(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/auth/conversations/{TENANT_B_ID}/session-123",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403


class TestTenantIsolationAppointments:
    """Tenant A cannot see Tenant B's appointments."""

    def test_tenant_a_cannot_list_tenant_b_appointments(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/appointments/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403


class TestTenantIsolationWidgetConfig:
    """Tenant A cannot modify Tenant B's widget config."""

    def test_tenant_a_cannot_update_tenant_b_widget(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.put(
            f"/api/v1/auth/widget-config/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"bot_name": "Hacked Bot"},
        )
        assert response.status_code == 403


class TestTenantIsolationDashboard:
    """Tenant A cannot access Tenant B's dashboard."""

    def test_tenant_a_cannot_view_tenant_b_dashboard(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/auth/dashboard/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403


class TestTenantIsolationSettings:
    """Tenant A cannot modify Tenant B's settings."""

    def test_tenant_a_cannot_update_tenant_b_settings(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.put(
            f"/api/v1/auth/settings/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"business_name": "Hacked Name"},
        )
        assert response.status_code == 403


class TestTenantIsolationBilling:
    """Tenant A cannot access Tenant B's billing."""

    def test_tenant_a_cannot_access_tenant_b_billing_portal(self, test_client):
        client, db_mock = test_client
        token_a = _make_token(TENANT_A_ID)

        response = client.get(
            f"/api/v1/auth/billing/portal/{TENANT_B_ID}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 403
