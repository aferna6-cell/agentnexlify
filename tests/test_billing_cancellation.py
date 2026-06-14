"""Tests for rubric criterion 3.4 — cancellation preserves access until period end.

Contracts under test:
- billing_cancel calls stripe.Subscription.modify with cancel_at_period_end=True
  (not an immediate delete).
- After billing_cancel, plan_status is NOT set to 'canceled'/'cancelled' in the DB
  immediately. Only cancellation_requested_at / cancellation_reason are written.
- _handle_subscription_deleted (the webhook fired later) is what sets plan='free',
  plan_status='cancelled'. A tenant that has merely requested cancellation still
  has their original plan_status and retains access.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers
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


def _make_active_sub(sub_id="sub_test_123", current_period_end=9999999999):
    sub = MagicMock()
    sub.id = sub_id
    sub.current_period_end = current_period_end
    return sub


# ---------------------------------------------------------------------------
# 3.4 — cancel sets cancel_at_period_end=True (not immediate delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.auth_billing.log_activity")
@patch("backend.routers.auth_billing.stripe.Subscription.modify")
@patch("backend.routers.auth_billing.stripe.Subscription.list")
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_cancel_sets_cancel_at_period_end_true(
    mock_db_factory,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """billing_cancel must pass cancel_at_period_end=True to Stripe, not delete the sub."""
    from backend.routers.auth_billing import billing_cancel

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "growth",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    cancel_event_chain = Chain(data=[{"id": "event-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain, cancel_event_chain]
    mock_db_factory.return_value = db

    mock_sub_list.return_value = MagicMock(data=[_make_active_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"reason": "too_expensive"}

    request.json = json_body

    result = await billing_cancel(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    mock_sub_modify.assert_called_once()
    call_kwargs = mock_sub_modify.call_args.kwargs
    assert call_kwargs.get("cancel_at_period_end") is True, (
        f"Expected cancel_at_period_end=True, got {call_kwargs.get('cancel_at_period_end')!r}"
    )
    assert result["status"] == "cancellation_scheduled"


@pytest.mark.asyncio
@patch("backend.routers.auth_billing.log_activity")
@patch("backend.routers.auth_billing.stripe.Subscription.modify")
@patch("backend.routers.auth_billing.stripe.Subscription.list")
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_cancel_does_not_set_plan_status_immediately(
    mock_db_factory,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """After billing_cancel, the tenant row must NOT have plan_status set to 'canceled'.

    The cancel endpoint only records cancellation_requested_at and cancellation_reason.
    plan_status stays at its previous value until Stripe fires customer.subscription.deleted,
    which is handled by _handle_subscription_deleted. This is what preserves access
    until the end of the billing period.
    """
    from backend.routers.auth_billing import billing_cancel

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "professional",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    cancel_event_chain = Chain(data=[{"id": "event-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain, cancel_event_chain]
    mock_db_factory.return_value = db

    mock_sub_list.return_value = MagicMock(data=[_make_active_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"reason": "missing_feature"}

    request.json = json_body

    await billing_cancel(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    # The tenant update should NOT contain plan_status
    assert tenant_update_chain.updated is not None, "tenants.update() was not called"
    written_keys = set(tenant_update_chain.updated.keys())
    assert "plan_status" not in written_keys, (
        f"billing_cancel must not set plan_status immediately; "
        f"got {written_keys!r} in the update payload"
    )
    # Should contain cancellation metadata
    assert "cancellation_requested_at" in written_keys
    assert "cancellation_reason" in written_keys


@pytest.mark.asyncio
@patch("backend.routers.auth_billing.log_activity")
@patch("backend.routers.auth_billing.stripe.Subscription.modify")
@patch("backend.routers.auth_billing.stripe.Subscription.list")
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_cancel_records_cancellation_reason_in_events_table(
    mock_db_factory,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """billing_cancel should insert a row in tenant_cancellation_events."""
    from backend.routers.auth_billing import billing_cancel

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "enterprise",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    cancel_event_chain = Chain(data=[{"id": "event-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain, cancel_event_chain]
    mock_db_factory.return_value = db

    mock_sub_list.return_value = MagicMock(data=[_make_active_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"reason": "switching_tools", "reason_detail": "Moving to a different platform"}

    request.json = json_body

    await billing_cancel(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    assert cancel_event_chain.inserted is not None, "tenant_cancellation_events.insert() was not called"
    assert cancel_event_chain.inserted.get("tenant_id") == "tenant-1"
    assert cancel_event_chain.inserted.get("reason") == "switching_tools"


# ---------------------------------------------------------------------------
# 3.4 — access gate: webhook _handle_subscription_deleted sets plan='free'
# ---------------------------------------------------------------------------


def test_subscription_deleted_webhook_sets_plan_to_free():
    """_handle_subscription_deleted sets plan='free', plan_status='cancelled'.

    This is the hook that fires when the billing period ends. BEFORE this event,
    the tenant still has their original plan because billing_cancel does not
    change plan_status.

    When tenant_id is in subscription metadata, _resolve_tenant_from_subscription
    returns it directly (no DB lookup), so only ONE db.table call is made (the update).
    """
    from backend.routers.billing import _handle_subscription_deleted

    update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    # metadata has tenant_id → no DB lookup needed for resolution, only the update call
    db.table.return_value = update_chain

    subscription = {
        "metadata": {"tenant_id": "tenant-1"},
        "customer": "cus_test",
    }

    _handle_subscription_deleted(db, subscription)

    assert update_chain.updated is not None, "tenants.update() was not called"
    assert update_chain.updated.get("plan") == "free"
    assert update_chain.updated.get("plan_status") == "cancelled"


def test_subscription_deleted_via_customer_id_lookup():
    """_handle_subscription_deleted resolves tenant via stripe_customer_id when metadata missing."""
    from backend.routers.billing import _handle_subscription_deleted

    db = MagicMock()
    lookup_chain = Chain(data=[{"id": "tenant-abc"}])
    update_chain = Chain(data=[{"id": "tenant-abc"}])
    # First call: select tenants where stripe_customer_id = cus_test
    # Second call: update tenants
    db.table.side_effect = [lookup_chain, update_chain]

    subscription = {
        "metadata": {},  # no tenant_id in metadata
        "customer": "cus_test",
    }

    _handle_subscription_deleted(db, subscription)

    assert update_chain.updated.get("plan") == "free"
    assert update_chain.updated.get("plan_status") == "cancelled"


# ---------------------------------------------------------------------------
# 3.4 — reject cancel without a valid reason
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_cancel_requires_valid_reason(
    mock_db_factory,
    _mock_ensure,
):
    """billing_cancel must return 400 if reason is missing or invalid."""
    from fastapi import HTTPException
    from backend.routers.auth_billing import billing_cancel

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "growth",
    }])
    db = MagicMock()
    db.table.side_effect = [tenant_chain]
    mock_db_factory.return_value = db

    request = MagicMock()

    async def json_body():
        return {"reason": ""}  # empty reason

    request.json = json_body

    with pytest.raises(HTTPException) as exc_info:
        await billing_cancel(
            request,
            claims={"tenant_id": "tenant-1", "role": "owner"},
        )
    assert exc_info.value.status_code == 400
