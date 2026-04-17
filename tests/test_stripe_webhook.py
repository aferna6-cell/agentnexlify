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

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_marketing_addon_checkout_routed_to_addon_handler(
        self, mock_construct, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("checkout.session.completed", {
            "id": "cs_addon",
            "metadata": {"tenant_id": "tenant-1", "addon": "marketing"},
            "subscription": "sub_addon",
        })
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body
        db_client = MagicMock()
        mock_db.return_value = db_client

        with patch("backend.routers.stripe_webhooks._handle_addon_checkout_completed") as mock_addon, \
             patch("backend.routers.stripe_webhooks._handle_checkout_completed") as mock_plan:
            result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_addon.assert_called_once_with(db_client, event["data"]["object"])
        mock_plan.assert_not_called()

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_marketing_addon_subscription_updated_routed_to_addon_handler(
        self, mock_construct, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("customer.subscription.updated", {
            "id": "sub_addon",
            "status": "active",
            "metadata": {"tenant_id": "tenant-1", "addon": "marketing"},
        })
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body
        db_client = MagicMock()
        mock_db.return_value = db_client

        with patch("backend.routers.stripe_webhooks._handle_addon_subscription_updated") as mock_addon, \
             patch("backend.routers.stripe_webhooks._handle_subscription_updated") as mock_plan:
            result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_addon.assert_called_once_with(db_client, event["data"]["object"])
        mock_plan.assert_not_called()

    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    @pytest.mark.asyncio
    async def test_marketing_addon_subscription_deleted_routed_to_addon_handler(
        self, mock_construct, mock_db
    ):
        from backend.routers.stripe_webhooks import stripe_webhook

        event = self._make_event("customer.subscription.deleted", {
            "id": "sub_addon",
            "metadata": {"tenant_id": "tenant-1", "addon": "marketing"},
        })
        mock_construct.return_value = event

        request = MagicMock()
        request.headers = {"stripe-signature": "valid"}

        async def mock_body():
            return b"{}"

        request.body = mock_body
        db_client = MagicMock()
        mock_db.return_value = db_client

        with patch("backend.routers.stripe_webhooks._handle_addon_subscription_deleted") as mock_addon, \
             patch("backend.routers.stripe_webhooks._handle_subscription_deleted") as mock_plan:
            result = await stripe_webhook(request)

        assert result == {"status": "ok"}
        mock_addon.assert_called_once_with(db_client, event["data"]["object"])
        mock_plan.assert_not_called()


class TestBillingPlanResolution:
    def test_autopilot_resolves_from_metadata(self):
        from backend.routers.billing import _resolve_plan

        assert _resolve_plan({"metadata": {"plan": "autopilot"}}) == "autopilot"

    def test_autopilot_resolves_from_amount_total(self):
        from backend.routers.billing import _resolve_plan

        assert _resolve_plan({"metadata": {}, "amount_total": 29900}) == "autopilot"

    def test_autopilot_resolves_from_line_item_description(self):
        from backend.routers.billing import _resolve_plan

        assert _resolve_plan({
            "metadata": {},
            "line_items": {"data": [{"description": "Autopilot monthly"}]},
        }) == "autopilot"


class TestInvoiceStripePayments:
    @patch("backend.routers.invoices.ensure_stripe_configured")
    @patch("backend.routers.invoices.stripe.Price.create")
    @patch("backend.routers.invoices.stripe.PaymentLink.create")
    @pytest.mark.asyncio
    async def test_invoice_payment_link_is_limited_to_one_completed_payment(
        self, mock_payment_link_create, mock_price_create, _mock_ensure
    ):
        from backend.routers.invoices import _get_or_create_stripe_payment_link

        mock_price_create.return_value = MagicMock(id="price_invoice_123")
        mock_payment_link_create.return_value = MagicMock(
            url="https://buy.stripe.com/test_invoice"
        )

        url = await _get_or_create_stripe_payment_link(
            invoice_id="invoice-1",
            tenant_id="tenant-1",
            invoice_number="INV-001",
            total=123.45,
        )

        assert url == "https://buy.stripe.com/test_invoice"
        create_kwargs = mock_payment_link_create.call_args.kwargs
        assert create_kwargs["restrictions"] == {
            "completed_sessions": {"limit": 1}
        }
        assert create_kwargs["metadata"] == {
            "invoice_id": "invoice-1",
            "tenant_id": "tenant-1",
        }
        assert create_kwargs["payment_intent_data"]["metadata"] == {
            "invoice_id": "invoice-1",
            "tenant_id": "tenant-1",
        }

    @patch("backend.routers.stripe_webhooks.fire_event_background")
    def test_invoice_payment_webhook_is_idempotent_when_already_paid(
        self, mock_fire_event
    ):
        from backend.routers.stripe_webhooks import _handle_invoice_payment

        table = MagicMock()
        for method in ("select", "eq", "limit"):
            getattr(table, method).return_value = table
        table.execute.return_value = MagicMock(
            data=[{"status": "paid", "stripe_payment_id": "pi_existing"}]
        )

        db = MagicMock()
        db.table.return_value = table

        result = _handle_invoice_payment(
            db,
            {
                "metadata": {"invoice_id": "invoice-1", "tenant_id": "tenant-1"},
                "amount_total": 12345,
                "payment_intent": "pi_existing",
            },
        )

        # Idempotency contract: returns None without mutating state
        assert result is None
        # No DB write attempted after detecting already-paid status
        assert not any(
            call[0] == "update" for call in table.method_calls
        ), "Expected no update() on already-paid invoice"
        table.update.assert_not_called()
        mock_fire_event.assert_not_called()
