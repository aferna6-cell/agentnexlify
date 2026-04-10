"""Tests for Stripe webhook signature verification and event handling."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Stripe signature verification tests ─────────────────────


class TestStripeSignatureVerification:
    """Test that the Stripe webhook endpoint validates signatures correctly."""

    @pytest.fixture
    def mock_stripe_event(self):
        return {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {"tenant_id": "tenant-1", "plan": "growth"},
                    "mode": "subscription",
                }
            },
        }

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks._handle_checkout_completed")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_valid_signature_processes_event(
        self, mock_construct, mock_handler, mock_db, mock_stripe_event
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        mock_construct.return_value = mock_stripe_event

        request = MagicMock()
        request.body = MagicMock(return_value=b'{"test": true}')
        request.headers = {"stripe-signature": "valid_sig"}

        # Make request.body() awaitable
        async def mock_body():
            return b'{"test": true}'

        request.body = mock_body

        result = await stripe_webhook(request)
        assert result == {"status": "ok"}
        mock_handler.assert_called_once()

    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_invalid_payload_returns_400(self, mock_construct):
        from backend.routers.stripe_webhooks import stripe_webhook
        from fastapi import HTTPException

        mock_construct.side_effect = ValueError("Invalid payload")

        request = MagicMock()
        request.headers = {"stripe-signature": "bad_sig"}

        async def mock_body():
            return b"not json"

        request.body = mock_body

        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook(request)
        assert exc_info.value.status_code == 400
        assert "Invalid payload" in exc_info.value.detail

    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_invalid_signature_returns_400(self, mock_construct):
        from backend.routers.stripe_webhooks import stripe_webhook
        from fastapi import HTTPException

        # Simulate SignatureVerificationError
        class FakeSignatureError(Exception):
            pass

        FakeSignatureError.__name__ = "SignatureVerificationError"
        mock_construct.side_effect = FakeSignatureError("bad sig")

        request = MagicMock()
        request.headers = {"stripe-signature": "bad_sig"}

        async def mock_body():
            return b'{"test": true}'

        request.body = mock_body

        with pytest.raises(HTTPException) as exc_info:
            await stripe_webhook(request)
        assert exc_info.value.status_code == 400
        assert "Invalid signature" in exc_info.value.detail


# ── Event routing tests ──────────────────────────────────────


class TestStripeEventRouting:
    """Test that different Stripe event types are routed to correct handlers."""

    def _make_event(self, event_type, data_object=None):
        return {
            "id": "evt_test",
            "type": event_type,
            "data": {"object": data_object or {}},
        }

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks._handle_subscription_updated")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_subscription_updated_routed(
        self, mock_construct, mock_handler, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("customer.subscription.updated", {
            "id": "sub_test",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_growth"}}]},
        })
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body

        db_client = MagicMock()
        mock_db.return_value = db_client

        result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_handler.assert_called_once_with(db_client, event["data"]["object"])
        mock_construct.assert_called_once()

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks._handle_subscription_deleted")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_subscription_deleted_routed(
        self, mock_construct, mock_handler, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("customer.subscription.deleted", {"id": "sub_test"})
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body

        db_client = MagicMock()
        mock_db.return_value = db_client

        result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_handler.assert_called_once_with(db_client, event["data"]["object"])
        mock_construct.assert_called_once()

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks._handle_payment_failed", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_payment_failed_routed(
        self, mock_construct, mock_handler, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("invoice.payment_failed", {"id": "inv_test"})
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body

        db_client = MagicMock()
        mock_db.return_value = db_client

        result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_handler.assert_awaited_once_with(db_client, event["data"]["object"])
        mock_construct.assert_called_once()

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_unhandled_event_still_returns_ok(self, mock_construct, mock_db):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("some.unknown.event", {})
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body

        result = await stripe_webhook(request)
        assert result == {"status": "ok"}
