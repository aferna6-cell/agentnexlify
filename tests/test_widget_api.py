"""Tests for the widget chat API endpoints.

Tests the core widget functionality: config retrieval, chat messaging,
and lead capture. Uses mocked Supabase and Anthropic API.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


VALID_API_KEY = "wk_test_valid_key_123"
TENANT_ID = "tenant-widget-test"


def _make_widget_config(api_key=VALID_API_KEY, tenant_id=TENANT_ID):
    return {
        "id": "wc-1",
        "tenant_id": tenant_id,
        "api_key": api_key,
        "bot_name": "Test Bot",
        "primary_color": "#3B82F6",
        "greeting_message": "Hello! How can I help?",
        "position": "bottom-right",
        "booking_enabled": True,
        "is_online": True,
        "knowledge_base": "We handle plumbing repairs, installs, and emergency visits.",
        "custom_instructions": "Answer like a helpful front desk teammate.",
        "branding": {},
    }


def _make_tenant(tenant_id=TENANT_ID):
    return {
        "id": tenant_id,
        "business_name": "Test Plumbing",
        "business_type": "plumbing",
        "owner_email": "owner@test.com",
        "plan": "professional",
    }


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase."""
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

    try:
        from backend.routers.widget_helpers import _cache
        _cache.clear()
    except Exception:
        pass

    try:
        from backend.limiter import limiter
        limiter.reset()
    except Exception:
        pass

    for p in patches:
        p.stop()


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

        for method in ["select", "insert", "update", "delete", "eq", "neq",
                       "gte", "lte", "gt", "lt", "limit", "order", "ilike",
                       "in_", "is_", "or_", "contains", "range", "single"]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


class TestWidgetConfig:
    """Test widget config retrieval."""

    @patch("backend.routers.widget_config._get_tenant")
    @patch("backend.routers.widget_config._get_widget_config")
    def test_valid_api_key_returns_config(self, mock_get_widget, mock_get_tenant, test_client):
        """Valid API key should return widget config."""
        client, db_mock = test_client

        mock_get_widget.return_value = _make_widget_config()
        mock_get_tenant.return_value = _make_tenant()

        _setup_table_mock(db_mock, {"menu_items": []})

        response = client.get(f"/api/v1/widget/config/{VALID_API_KEY}")
        assert response.status_code == 200
        data = response.json()
        assert data["bot_name"] == "Test Bot"

    def test_invalid_api_key_returns_404(self, test_client):
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "widget_configs": [],
        })

        response = client.get("/api/v1/widget/config/invalid_key_xyz")
        assert response.status_code == 404


class TestWidgetChat:
    """Test widget chat endpoint."""

    def test_chat_missing_session_id_returns_422(self, test_client):
        client, db_mock = test_client

        response = client.post("/api/v1/widget/chat", json={
            "api_key": VALID_API_KEY,
            "message": "Hello",
        })
        assert response.status_code == 422

    def test_chat_missing_message_returns_422(self, test_client):
        client, db_mock = test_client

        response = client.post("/api/v1/widget/chat", json={
            "api_key": VALID_API_KEY,
            "session_id": "sess-123",
        })
        assert response.status_code == 422

    def test_chat_invalid_api_key_returns_error(self, test_client):
        client, db_mock = test_client

        _setup_table_mock(db_mock, {
            "widget_configs": [],
            "tenants": [],
        })

        # Clear cache to force fresh lookup
        try:
            from backend.routers.widget_helpers import _cache
            _cache.clear()
        except Exception:
            pass

        response = client.post("/api/v1/widget/chat", json={
            "api_key": "invalid_key",
            "session_id": "sess-123",
            "message": "Hello",
        })
        # Should return 404 or error, not 500
        assert response.status_code in (404, 400, 403)

    @patch("backend.routers.widget_chat.call_claude_messages", new_callable=AsyncMock)
    def test_chat_happy_path(self, mock_call_claude, test_client):
        client, db_mock = test_client

        widget_config = _make_widget_config()
        tenant = _make_tenant()

        _setup_table_mock(db_mock, {
            "widget_configs": [widget_config],
            "tenants": [tenant],
            "chat_messages": [],
            "conversations": [],
            "faq_entries": [],
            "chat_flows": [],
            "website_content": [],
            "menu_items": [],
        })

        mock_call_claude.return_value = MagicMock(
            text="I can help with your plumbing needs!",
            duration_ms=123,
            input_tokens=100,
            output_tokens=50,
        )

        response = client.post("/api/v1/widget/chat", json={
            "api_key": VALID_API_KEY,
            "session_id": "sess-test-001",
            "message": "Do you fix leaky faucets?",
        })
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data or "response" in data or "message" in data
        mock_call_claude.assert_awaited_once()

    @patch("backend.routers.widget_chat.call_claude_messages", new_callable=AsyncMock)
    def test_chat_first_greeting_shortcircuits(self, mock_call_claude, test_client):
        client, db_mock = test_client

        widget_config = _make_widget_config()
        tenant = _make_tenant()
        widget_config["knowledge_base"] = ""
        widget_config["custom_instructions"] = ""

        _setup_table_mock(db_mock, {
            "widget_configs": [widget_config],
            "tenants": [tenant],
            "chat_messages": [],
            "conversations": [],
            "faq_entries": [],
            "chat_flows": [],
            "website_content": [],
            "menu_items": [],
        })

        response = client.post("/api/v1/widget/chat", json={
            "api_key": VALID_API_KEY,
            "session_id": "sess-test-greeting",
            "message": "Hello",
        })

        assert response.status_code == 200
        assert response.json()["response"] == widget_config["greeting_message"]
        mock_call_claude.assert_not_awaited()


class TestWidgetHealth:
    """Test widget health endpoint."""

    def test_health_endpoint_returns_200(self, test_client):
        client, db_mock = test_client

        response = client.get("/health")
        assert response.status_code == 200
