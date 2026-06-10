"""Tests for rubric criterion 3.6 — refund matrix.

Contracts under test:
- Partial refund: amount_cents < full charge — Stripe.Refund.create called with
  the specific amount, audit row records that amount.
- Full refund: amount_cents=None — Stripe.Refund.create called without amount
  (Stripe refunds the full charge), audit row records amount from Stripe response.
- Idempotent replay for both: second call with same refund_request_id returns
  existing audit row without calling Stripe again.
- Audit row always contains the exact amount returned by Stripe (or passed in).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_launch_risk_guardrails.py)
# ---------------------------------------------------------------------------


class Chain:
    """Minimal Supabase chain mock."""

    def __init__(self, data=None):
        self.data = data or []
        self.updated = None
        self.inserted = None

    def select(self, *a, **kw):
        return self

    def update(self, data):
        self.updated = data
        return self

    def insert(self, data):
        self.inserted = data
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        return MagicMock(data=self.data)


# ---------------------------------------------------------------------------
# 3.6 — Partial refund
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_partial_refund_passes_amount_to_stripe(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Partial refund (amount_cents=5000, full charge=24900) passes amount=5000 to Stripe."""
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[])
    refund_insert = Chain(data=[{"id": "refund-row"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select, refund_insert]
    mock_db_factory.return_value = db

    mock_refund_create.return_value = {
        "id": "re_partial",
        "amount": 5000,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_123",
        "reason": "requested_by_customer",
    }

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-partial-001",
            payment_intent="pi_123",
            amount_cents=5000,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested partial refund.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_called_once()
    call_kwargs = mock_refund_create.call_args.kwargs
    assert call_kwargs.get("amount") == 5000, (
        f"Expected amount=5000 passed to Stripe, got {call_kwargs.get('amount')!r}"
    )
    assert result["status"] == "refunded"
    assert result["idempotent_replay"] is False


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_partial_refund_audit_row_records_actual_amount(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Audit row inserted for partial refund must record the refunded amount_cents."""
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[])
    refund_insert = Chain(data=[{"id": "refund-row"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select, refund_insert]
    mock_db_factory.return_value = db

    mock_refund_create.return_value = {
        "id": "re_partial",
        "amount": 5000,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_123",
        "reason": "requested_by_customer",
    }

    await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-partial-002",
            payment_intent="pi_123",
            amount_cents=5000,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested partial refund.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    assert refund_insert.inserted is not None, "billing_refunds.insert() was not called"
    assert refund_insert.inserted.get("amount_cents") == 5000, (
        f"Audit row amount_cents should be 5000, got {refund_insert.inserted.get('amount_cents')!r}"
    )
    assert refund_insert.inserted.get("stripe_refund_id") == "re_partial"
    assert refund_insert.inserted.get("tenant_id") == "tenant-1"


# ---------------------------------------------------------------------------
# 3.6 — Full refund (no amount_cents)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_full_refund_omits_amount_from_stripe_call(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Full refund (amount_cents=None) should NOT pass an amount kwarg to Stripe.Refund.create.

    When amount is absent, Stripe refunds the full charge automatically.
    """
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[])
    refund_insert = Chain(data=[{"id": "refund-row"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select, refund_insert]
    mock_db_factory.return_value = db

    mock_refund_create.return_value = {
        "id": "re_full",
        "amount": 24900,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_456",
        "reason": "requested_by_customer",
    }

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-full-001",
            payment_intent="pi_456",
            amount_cents=None,  # full refund
            stripe_reason="requested_by_customer",
            internal_reason="Full refund requested.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_called_once()
    call_kwargs = mock_refund_create.call_args.kwargs
    assert "amount" not in call_kwargs or call_kwargs.get("amount") is None, (
        f"Full refund should not pass amount to Stripe, got {call_kwargs.get('amount')!r}"
    )
    assert result["status"] == "refunded"
    assert result["idempotent_replay"] is False


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_full_refund_audit_row_records_stripe_amount(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Full refund audit row should record the amount Stripe returned (24900)."""
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[])
    refund_insert = Chain(data=[{"id": "refund-row"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select, refund_insert]
    mock_db_factory.return_value = db

    mock_refund_create.return_value = {
        "id": "re_full",
        "amount": 24900,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_456",
        "reason": "requested_by_customer",
    }

    await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-full-002",
            payment_intent="pi_456",
            amount_cents=None,
            stripe_reason="requested_by_customer",
            internal_reason="Full refund requested.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    assert refund_insert.inserted is not None, "billing_refunds.insert() was not called"
    # The audit row amount_cents should come from Stripe's response (24900)
    assert refund_insert.inserted.get("amount_cents") == 24900, (
        f"Audit row should record Stripe amount 24900, got {refund_insert.inserted.get('amount_cents')!r}"
    )
    assert refund_insert.inserted.get("stripe_refund_id") == "re_full"


# ---------------------------------------------------------------------------
# 3.6 — Idempotent replay for partial refund
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_partial_refund_idempotent_replay(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Second call for same partial refund_request_id returns existing row without calling Stripe."""
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[{
        "stripe_refund_id": "re_partial_existing",
        "amount_cents": 5000,
        "currency": "usd",
        "status": "succeeded",
        "refund_request_id": "refund-partial-001",
    }])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select]
    mock_db_factory.return_value = db

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-partial-001",  # same ID as first call
            payment_intent="pi_123",
            amount_cents=5000,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested partial refund.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_not_called()
    mock_log_activity.assert_not_called()
    assert result["idempotent_replay"] is True
    assert result["stripe_refund_id"] == "re_partial_existing"
    assert result["status"] == "refunded"


# ---------------------------------------------------------------------------
# 3.6 — Idempotent replay for full refund
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_full_refund_idempotent_replay(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    """Second call for same full refund_request_id returns existing row without calling Stripe."""
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[{
        "stripe_refund_id": "re_full_existing",
        "amount_cents": 24900,
        "currency": "usd",
        "status": "succeeded",
        "refund_request_id": "refund-full-001",
    }])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select]
    mock_db_factory.return_value = db

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-full-001",  # same ID as first call
            payment_intent="pi_456",
            amount_cents=None,
            stripe_reason="requested_by_customer",
            internal_reason="Full refund requested.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_not_called()
    mock_log_activity.assert_not_called()
    assert result["idempotent_replay"] is True
    assert result["stripe_refund_id"] == "re_full_existing"
    assert result["status"] == "refunded"
