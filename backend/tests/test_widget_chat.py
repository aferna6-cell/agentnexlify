"""Tests for widget chat endpoints."""

import pytest
from unittest.mock import MagicMock, patch


class TestWidgetChat:
    """POST /api/v1/widget/chat"""

    def test_chat_missing_api_key(self, client):
        """Missing api_key returns 422."""
        resp = client.post("/api/v1/widget/chat", json={
            "message": "Hello",
            "session_id": "sess-123",
        })
        assert resp.status_code == 422

    def test_chat_invalid_api_key(self, client, mock_supabase):
        """Invalid api_key returns 404 (tenant not found)."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.post("/api/v1/widget/chat", json={
            "api_key": "invalid-key",
            "message": "Hello",
            "session_id": "sess-123",
        })
        assert resp.status_code in (404, 400)


class TestWidgetConfig:
    """GET /api/v1/widget/config/{api_key}"""

    def test_config_invalid_key(self, client, mock_supabase):
        """Invalid api_key returns 404."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.get("/api/v1/widget/config/nonexistent-key")
        assert resp.status_code == 404
