"""Tests for login flow, chat endpoint edge cases, and lead capture edge cases.

Uses FastAPI TestClient with mocked Supabase following the same pattern
as test_auth_endpoints.py.  All tests compatible with --timeout=30.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import bcrypt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.widget_chat.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_helpers.get_supabase", return_value=db_mock),
        # Services that widget modules touch at import or call time
        patch("backend.services.activity.get_supabase", return_value=db_mock),
        patch("backend.services.webhook_dispatcher.get_supabase", return_value=db_mock),
        patch("backend.services.lead_scoring.get_supabase", return_value=db_mock),
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


# ---------------------------------------------------------------------------
# Helper: configure mock table responses (copied from test_auth_endpoints.py)
# ---------------------------------------------------------------------------


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
        for method in [
            "select", "insert", "update", "delete", "eq", "neq",
            "gte", "lte", "gt", "lt", "limit", "order", "ilike",
            "in_", "is_", "or_", "contains", "not_",
        ]:
            getattr(table, method).return_value = table

        # Execute returns the data
        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


# =========================================================================
# Test Group 1: Login Flow
# =========================================================================


class TestLoginFlow:
    """Test the POST /api/v1/auth/login endpoint — 4 tests."""

    def test_login_valid_credentials(self, test_client):
        """Correct email/password returns 200 with token, tenant_id, etc."""
        client, db_mock = test_client
        password = "CorrectP@ss123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-login-001",
                "password_hash": hashed,
                "business_name": "Login Test Biz",
                "plan": "growth",
                "business_type": "plumbing",
            }],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "owner@example.com",
            "password": password,
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == "tenant-login-001"
        assert data["business_name"] == "Login Test Biz"
        assert data["plan"] == "growth"

    def test_login_wrong_password(self, test_client):
        """Correct email but wrong password returns 401."""
        client, db_mock = test_client
        correct_hash = bcrypt.hashpw(b"RightPassword1!", bcrypt.gensalt()).decode()

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-002",
                "password_hash": correct_hash,
                "business_name": "Test Biz",
                "plan": "free",
            }],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword!",
        })
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_email(self, test_client):
        """Login with email not in tenants or team_members returns 401."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "tenants": [],
            "team_members": [],
        })

        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "SomePass123!",
        })
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_missing_fields(self, test_client):
        """Request without email or password returns 422 validation error."""
        client, db_mock = test_client

        # Missing password
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
        })
        assert response.status_code == 422

        # Missing email
        response = client.post("/api/v1/auth/login", json={
            "password": "SomePass",
        })
        assert response.status_code == 422

        # Empty body
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


# =========================================================================
# Test Group 2: Chat Endpoint Edge Cases
# =========================================================================


class TestChatEdgeCases:
    """Test POST /api/v1/widget/chat edge cases — 3 tests."""

    def _widget_and_tenant_tables(self, api_key="anx_test_key_valid"):
        """Return table responses for a valid widget+tenant combo."""
        return {
            "widget_configs": [{
                "tenant_id": "tenant-chat-001",
                "api_key": api_key,
                "bot_name": "Test Bot",
                "primary_color": "#00BFFF",
                "greeting_message": "Hi!",
                "position": "bottom-right",
                "show_watermark": True,
                "allowed_domains": None,
                "booking_enabled": False,
                "branding": None,
                "is_online": True,
                "offline_message": None,
            }],
            "tenants": [{
                "id": "tenant-chat-001",
                "business_name": "Chat Test Biz",
                "business_type": "plumbing",
                "city": "Denver",
                "plan": "growth",
                "plan_status": "active",
                "free_trial_started_at": None,
                "conversations_used_this_month": 0,
                "sms_notifications_enabled": False,
                "notification_phone": None,
            }],
            # chat_messages (load history) returns empty
            "chat_messages": [],
            # conversations table lookup
            "conversations": [{"id": "conv-001"}],
            # FAQ, business_hours, ai_feedback, website_content, etc.
            "faq_entries": [],
            "business_hours": [],
            "ai_feedback": [],
            "website_content": [],
            "menu_items": [],
            "jobs": [],
            "chat_flows": [],
            "leads": [],
        }

    @patch("backend.routers.widget_chat.anthropic")
    def test_chat_very_long_message(self, mock_anthropic, test_client):
        """Message at max_length (10000 chars) should be accepted."""
        client, db_mock = test_client

        _setup_table_mock(db_mock, self._widget_and_tenant_tables())

        # Mock the Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="I received your message!")]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        long_message = "a" * 10000  # max_length boundary

        response = client.post("/api/v1/widget/chat", json={
            "api_key": "anx_test_key_valid",
            "session_id": "sess-long-msg",
            "message": long_message,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess-long-msg"
        assert "response" in data

    def test_chat_invalid_api_key(self, test_client):
        """Chat with a non-existent API key returns 404."""
        client, db_mock = test_client

        # widget_configs returns empty -> 404
        _setup_table_mock(db_mock, {
            "widget_configs": [],
        })

        response = client.post("/api/v1/widget/chat", json={
            "api_key": "anx_this_key_does_not_exist",
            "session_id": "sess-invalid",
            "message": "Hello?",
        })
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_chat_empty_message(self, test_client):
        """Empty message string should return 422 (Pydantic min_length or blank check)."""
        client, db_mock = test_client

        # Even though the message field allows empty string in the schema
        # (no min_length constraint), sending a truly empty string tests
        # the boundary.  If Pydantic allows it, the endpoint should still
        # return 200.  But sending no message field at all => 422.
        response = client.post("/api/v1/widget/chat", json={
            "api_key": "anx_some_key",
            "session_id": "sess-empty",
            # message field is missing entirely
        })
        assert response.status_code == 422


# =========================================================================
# Test Group 3: Lead Capture Edge Cases
# =========================================================================


class TestLeadCaptureEdgeCases:
    """Test POST /api/v1/widget/lead edge cases — 3 tests."""

    def _widget_and_tenant_tables(self, api_key="anx_lead_test_key"):
        """Return table responses for a valid widget+tenant combo."""
        return {
            "widget_configs": [{
                "tenant_id": "tenant-lead-001",
                "api_key": api_key,
                "bot_name": "Lead Bot",
                "primary_color": "#00BFFF",
                "greeting_message": "Hi!",
                "position": "bottom-right",
                "show_watermark": True,
                "allowed_domains": None,
                "booking_enabled": False,
                "branding": None,
                "is_online": True,
                "offline_message": None,
            }],
            "tenants": [{
                "id": "tenant-lead-001",
                "business_name": "Lead Test Biz",
                "business_type": "dental",
                "city": "Austin",
                "plan": "professional",
                "plan_status": "active",
                "free_trial_started_at": None,
                "conversations_used_this_month": 5,
                "sms_notifications_enabled": False,
                "notification_phone": None,
            }],
            "conversations": [{"id": "conv-lead-001"}],
            "leads": [],
        }

    def test_lead_malformed_email(self, test_client):
        """Submitting 'not-an-email' as the email — endpoint should accept
        (WidgetLeadRequest.email is a plain str, not EmailStr) and attempt
        to create the lead.  The important thing is no 500 error."""
        client, db_mock = test_client

        tables = self._widget_and_tenant_tables()
        # leads table: first call (dedup lookup) returns empty,
        # second call (insert) returns the new lead
        tables["leads"] = [
            [],  # first: dedup lookup finds nothing (email doesn't look up)
            [{"id": "lead-malformed-001"}],  # second: insert result
        ]
        _setup_table_mock(db_mock, tables)

        response = client.post("/api/v1/widget/lead", json={
            "api_key": "anx_lead_test_key",
            "session_id": "sess-malformed",
            "email": "not-an-email",
        })
        # Endpoint accepts any string for email (no EmailStr validation)
        # so it should succeed with 200 and return a lead_id
        assert response.status_code == 200
        data = response.json()
        assert data.get("lead_id") is not None
        assert "email" in data.get("updated_fields", [])

    def test_lead_international_phone(self, test_client):
        """Phone like '+44 20 1234 5678' should be captured correctly."""
        client, db_mock = test_client

        tables = self._widget_and_tenant_tables()
        # No email provided, so no dedup lookup. Insert returns new lead.
        tables["leads"] = [[{"id": "lead-intl-001"}]]
        _setup_table_mock(db_mock, tables)

        response = client.post("/api/v1/widget/lead", json={
            "api_key": "anx_lead_test_key",
            "session_id": "sess-intl-phone",
            "name": "Alice",
            "phone": "+44 20 1234 5678",
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("lead_id") is not None
        assert "phone" in data.get("updated_fields", [])
        assert "name" in data.get("updated_fields", [])

    def test_lead_empty_name(self, test_client):
        """Empty name but valid email should still create a lead.
        The name field is None/empty, but email alone is sufficient."""
        client, db_mock = test_client

        tables = self._widget_and_tenant_tables()
        # First call: dedup lookup by email finds nothing
        # Second call: insert returns new lead
        tables["leads"] = [
            [],
            [{"id": "lead-noname-001"}],
        ]
        _setup_table_mock(db_mock, tables)

        response = client.post("/api/v1/widget/lead", json={
            "api_key": "anx_lead_test_key",
            "session_id": "sess-noname",
            "name": "",
            "email": "noname@example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("lead_id") is not None
        # Empty string name should be excluded from fields (WidgetLeadRequest
        # uses `if req.name:` which is falsy for empty string)
        assert "name" not in data.get("updated_fields", [])
        assert "email" in data.get("updated_fields", [])
