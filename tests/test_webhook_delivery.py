"""Tests for webhook delivery and retry logic."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.webhook_dispatcher import (
    SUPPORTED_EVENTS,
    _check_daily_limit,
    _daily_deliveries,
    _increment_daily,
    _sign_payload,
    fire_event,
    _deliver,
    _DAILY_LIMIT,
    _MAX_FAILURES,
    _MAX_RETRIES,
)


# ── HMAC signing tests ──────────────────────────────────────


class TestHMACSigning:
    def test_sign_payload_deterministic(self):
        payload = b'{"event": "test"}'
        sig1 = _sign_payload(payload, "secret123")
        sig2 = _sign_payload(payload, "secret123")
        assert sig1 == sig2

    def test_different_secret_different_sig(self):
        payload = b'{"event": "test"}'
        sig1 = _sign_payload(payload, "secret-a")
        sig2 = _sign_payload(payload, "secret-b")
        assert sig1 != sig2

    def test_different_payload_different_sig(self):
        sig1 = _sign_payload(b"payload1", "secret")
        sig2 = _sign_payload(b"payload2", "secret")
        assert sig1 != sig2

    def test_sign_returns_hex_string(self):
        sig = _sign_payload(b"test", "secret")
        assert isinstance(sig, str)
        # SHA-256 hex = 64 chars
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)


# ── Daily limit tests ────────────────────────────────────────


class TestDailyLimit:
    def setup_method(self):
        _daily_deliveries.clear()

    def test_under_limit(self):
        assert _check_daily_limit("tenant-1") is True

    def test_at_limit(self):
        _daily_deliveries["tenant-1"] = _DAILY_LIMIT
        assert _check_daily_limit("tenant-1") is False

    def test_increment(self):
        assert _daily_deliveries.get("tenant-1", 0) == 0
        _increment_daily("tenant-1")
        assert _daily_deliveries["tenant-1"] == 1
        _increment_daily("tenant-1")
        assert _daily_deliveries["tenant-1"] == 2

    def test_limits_are_per_tenant(self):
        _daily_deliveries["tenant-1"] = _DAILY_LIMIT
        assert _check_daily_limit("tenant-1") is False
        assert _check_daily_limit("tenant-2") is True


# ── Supported events tests ───────────────────────────────────


class TestSupportedEvents:
    def test_lead_events(self):
        assert "lead.created" in SUPPORTED_EVENTS
        assert "lead.updated" in SUPPORTED_EVENTS

    def test_appointment_events(self):
        assert "appointment.booked" in SUPPORTED_EVENTS
        assert "appointment.cancelled" in SUPPORTED_EVENTS

    def test_conversation_events(self):
        assert "conversation.started" in SUPPORTED_EVENTS
        assert "conversation.message" in SUPPORTED_EVENTS

    def test_automation_events(self):
        assert "automation.email_sent" in SUPPORTED_EVENTS

    def test_unsupported_event(self):
        assert "fake.event" not in SUPPORTED_EVENTS


# ── fire_event tests ─────────────────────────────────────────


class TestFireEvent:
    def setup_method(self):
        _daily_deliveries.clear()

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.get_supabase")
    async def test_unknown_event_skipped(self, mock_db):
        assert _daily_deliveries.get("tenant-1", 0) == 0
        await fire_event("tenant-1", "not.a.real.event", {})
        mock_db.assert_not_called()
        assert _daily_deliveries.get("tenant-1", 0) == 0

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.get_supabase")
    async def test_no_matching_webhooks_skipped(self, mock_db):
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_db.return_value.table.return_value = mock_table

        await fire_event("tenant-1", "lead.created", {"lead_id": "123"})
        # Should query webhooks but not deliver
        mock_table.select.assert_called_once()
        assert _daily_deliveries.get("tenant-1", 0) == 0
        assert mock_table.eq.call_count >= 2

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher._deliver")
    @patch("backend.services.webhook_dispatcher.get_supabase")
    async def test_fires_to_matching_webhooks(self, mock_db, mock_deliver):
        mock_deliver.return_value = None
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[
            {"id": "wh-1", "url": "https://hook.test/a", "events": ["lead.created"], "secret": "s1"},
        ])
        mock_db.return_value.table.return_value = mock_table

        _daily_deliveries.clear()
        await fire_event("tenant-1", "lead.created", {"lead_id": "123"})
        await asyncio.sleep(0)

        mock_deliver.assert_awaited_once()
        assert mock_deliver.await_args.args[0] == "tenant-1"
        assert mock_deliver.await_args.args[1]["id"] == "wh-1"
        payload = mock_deliver.await_args.args[2]
        assert payload["event"] == "lead.created"
        assert payload["data"] == {"lead_id": "123"}
        assert "timestamp" in payload

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.get_supabase")
    async def test_daily_limit_blocks_fire(self, mock_db):
        _daily_deliveries["tenant-full"] = _DAILY_LIMIT
        await fire_event("tenant-full", "lead.created", {"lead_id": "123"})
        mock_db.assert_not_called()
        assert _daily_deliveries["tenant-full"] == _DAILY_LIMIT


# ── _deliver tests ───────────────────────────────────────────


class TestDeliver:
    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.get_supabase")
    @patch("backend.services.webhook_dispatcher.httpx.AsyncClient")
    async def test_successful_delivery_logs(self, mock_client_cls, mock_db):
        # Mock HTTP response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"failure_count": 0}])
        mock_db.return_value.table.return_value = mock_table

        _daily_deliveries.clear()
        webhook = {"id": "wh-1", "url": "https://hook.test/a", "secret": "test-secret"}
        payload = {"event": "lead.created", "data": {}}

        await _deliver("tenant-1", webhook, payload)

        # Should have posted to the URL
        mock_client.post.assert_called_once()
        post_kwargs = mock_client.post.call_args.kwargs
        assert post_kwargs["headers"]["X-Webhook-Signature"]
        assert json.loads(post_kwargs["content"].decode()) == payload

        assert _daily_deliveries["tenant-1"] == 1
        mock_table.insert.assert_called_once()
        insert_payload = mock_table.insert.call_args.args[0]
        assert insert_payload["webhook_id"] == "wh-1"
        assert insert_payload["event"] == "lead.created"
        assert insert_payload["response_status"] == 200
        assert insert_payload["success"] is True

        mock_table.update.assert_called_once()
        update_payload = mock_table.update.call_args.args[0]
        assert update_payload["failure_count"] == 0
        assert "last_triggered_at" in update_payload

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.services.webhook_dispatcher.get_supabase")
    @patch("backend.services.webhook_dispatcher.httpx.AsyncClient")
    async def test_failed_delivery_retries_until_max_attempts(self, mock_client_cls, mock_db, mock_sleep):
        # Mock HTTP response with 500
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"failure_count": 1}])
        mock_db.return_value.table.return_value = mock_table

        _daily_deliveries.clear()
        webhook = {"id": "wh-1", "url": "https://hook.test/fail", "secret": None}
        payload = {"event": "lead.created", "data": {}}

        await _deliver("tenant-1", webhook, payload, attempt=0)

        # Should sleep once per retry and stop after the configured max.
        assert mock_sleep.await_count == _MAX_RETRIES
        assert mock_client.post.call_count == _MAX_RETRIES + 1

    @pytest.mark.asyncio
    @patch("backend.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.services.webhook_dispatcher.get_supabase")
    @patch("backend.services.webhook_dispatcher.httpx.AsyncClient")
    async def test_retry_does_not_retry_again(self, mock_client_cls, mock_db, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"failure_count": 2}])
        mock_db.return_value.table.return_value = mock_table

        _daily_deliveries.clear()
        webhook = {"id": "wh-1", "url": "https://hook.test/fail", "secret": None}
        payload = {"event": "lead.created", "data": {}}

        # Calling at the max attempt count should not schedule another retry.
        await _deliver("tenant-1", webhook, payload, attempt=_MAX_RETRIES)

        mock_sleep.assert_not_awaited()
        assert mock_client.post.call_count == 1
