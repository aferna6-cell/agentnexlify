"""Coverage tests for MCP server tool functions.

These tests mock Supabase and exercise the 6 MCP tools directly so that
changed-lines coverage stays above 85% for backend/mcp_server.py.
"""

import os

os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch

from backend.mcp_server import (
    get_action_items,
    get_analytics_summary,
    get_unread_conversations,
    list_recent_leads,
    list_today_appointments,
    reply_to_conversation,
)

_TENANT = {
    "id": "tenant-001",
    "business_name": "Test Biz",
    "plan": "professional",
}


def _db_mock(table_data: dict):
    """Supabase mock with chainable query methods returning per-table data."""
    db = MagicMock()

    def _table(name):
        data = table_data.get(name, [])
        t = MagicMock()
        for method in (
            "select",
            "insert",
            "update",
            "eq",
            "neq",
            "gte",
            "lte",
            "lt",
            "limit",
            "order",
            "in_",
            "is_",
        ):
            getattr(t, method).return_value = t
        result = MagicMock()
        result.data = data
        result.count = len(data)
        t.execute.return_value = result
        return t

    db.table = _table
    return db


class TestListRecentLeads:
    def test_returns_leads(self):
        db = _db_mock(
            {
                "leads": [
                    {
                        "name": "Alice",
                        "email": "alice@example.com",
                        "phone": "555-1234",
                        "status": "new",
                        "lead_score": 80,
                        "areas_of_interest": "plumbing",
                        "conversation_summary": "needs pipe fix",
                        "created_at": "2026-08-01T10:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_recent_leads()
        assert "Alice" in result
        assert "Test Biz" in result
        assert "new" in result

    def test_no_leads_returns_message(self):
        db = _db_mock({"leads": []})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_recent_leads()
        assert "No new leads" in result

    def test_invalid_key_returns_error(self):
        with patch("backend.mcp_server._get_tenant_by_api_key", return_value=None):
            result = list_recent_leads()
        assert "Error" in result

    def test_lead_without_optional_fields(self):
        db = _db_mock(
            {
                "leads": [
                    {
                        "name": None,
                        "email": None,
                        "phone": None,
                        "status": "new",
                        "lead_score": None,
                        "areas_of_interest": None,
                        "conversation_summary": None,
                        "created_at": "2026-08-01T10:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_recent_leads()
        assert "Unknown" in result


class TestListTodayAppointments:
    def test_returns_appointments(self):
        db = _db_mock(
            {
                "appointments": [
                    {
                        "customer_name": "Bob",
                        "customer_email": "bob@example.com",
                        "customer_phone": "555-5678",
                        "start_time": "2026-08-02T09:00:00+00:00",
                        "end_time": "2026-08-02T10:00:00+00:00",
                        "status": "booked",
                        "notes": "",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_today_appointments()
        assert "Bob" in result
        assert "booked" in result

    def test_no_appointments(self):
        db = _db_mock({"appointments": []})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_today_appointments()
        assert "No appointments" in result

    def test_invalid_start_time_falls_back(self):
        db = _db_mock(
            {
                "appointments": [
                    {
                        "customer_name": "Carol",
                        "customer_phone": "",
                        "start_time": "invalid-date",
                        "status": "booked",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = list_today_appointments()
        assert "Carol" in result


class TestGetUnreadConversations:
    def test_returns_conversations(self):
        db = _db_mock(
            {
                "conversations": [
                    {
                        "id": "c1",
                        "session_id": "s1",
                        "status": "active",
                        "lead_id": None,
                        "tags": ["urgent"],
                        "created_at": "2026-08-02T09:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_unread_conversations()
        assert "active" in result
        assert "urgent" in result

    def test_no_conversations(self):
        db = _db_mock({"conversations": []})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_unread_conversations()
        assert "No recent" in result

    def test_conversation_with_no_tags(self):
        db = _db_mock(
            {
                "conversations": [
                    {
                        "id": "c2",
                        "session_id": "s2",
                        "status": "closed",
                        "lead_id": None,
                        "tags": None,
                        "created_at": "2026-08-02T08:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_unread_conversations()
        assert "no tags" in result


class TestGetActionItems:
    def test_returns_items(self):
        db = _db_mock(
            {
                "action_items": [
                    {
                        "description": "Call Alice back",
                        "due_date": "2026-08-05",
                        "priority": "high",
                        "status": "pending",
                        "created_at": "2026-08-02T09:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_action_items()
        assert "Call Alice back" in result
        assert "🔴" in result

    def test_no_items(self):
        db = _db_mock({"action_items": []})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_action_items()
        assert "No pending action items" in result

    def test_status_all_passes_filter(self):
        db = _db_mock(
            {
                "action_items": [
                    {
                        "description": "Done task",
                        "due_date": None,
                        "priority": "low",
                        "status": "done",
                        "created_at": "2026-08-01T00:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_action_items(status="all")
        assert "Done task" in result


class TestGetAnalyticsSummary:
    def test_returns_summary(self):
        db = _db_mock(
            {
                "leads": [1, 2],
                "conversations": [1, 2, 3],
                "appointments": [1],
            }
        )
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_analytics_summary()
        assert "Analytics Summary" in result
        assert "Test Biz" in result
        assert "Conversations" in result

    def test_zero_conversations_no_divide_by_zero(self):
        db = _db_mock({"leads": [], "conversations": [], "appointments": []})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = get_analytics_summary()
        assert "0%" in result

    def test_invalid_key_returns_error(self):
        with patch("backend.mcp_server._get_tenant_by_api_key", return_value=None):
            result = get_analytics_summary()
        assert "Error" in result


class TestReplyToConversation:
    def test_sends_reply(self):
        db = _db_mock({})
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = reply_to_conversation("session-123", "Hello there!")
        assert "session-123" in result
        assert "Hello there" in result

    def test_long_message_is_truncated_in_reply(self):
        db = _db_mock({})
        long_msg = "A" * 100
        with patch(
            "backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT
        ), patch("backend.mcp_server.get_service_supabase", return_value=db):
            result = reply_to_conversation("session-456", long_msg)
        assert "..." in result

    def test_empty_message_returns_error(self):
        with patch("backend.mcp_server._get_tenant_by_api_key", return_value=_TENANT):
            result = reply_to_conversation("session-789", "   ")
        assert "Error" in result

    def test_invalid_key_returns_error(self):
        with patch("backend.mcp_server._get_tenant_by_api_key", return_value=None):
            result = reply_to_conversation("s", "msg")
        assert "Error" in result
