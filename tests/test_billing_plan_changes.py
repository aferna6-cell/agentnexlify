"""Tests for rubric criterion 3.3 — proration on plan upgrade/downgrade.

Contract under test:
- billing_change_plan calls stripe.Subscription.modify with
  proration_behavior="create_prorations" (not "none" or "always_invoice").
- The tenant plan is updated immediately in the DB (not waiting for webhook).
- Downgrade follows the same proration contract as upgrade.
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

    def select(self, *a, **kw):
        return self

    def update(self, data):
        self.updated = data
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        return MagicMock(data=self.data)


def _make_sub(sub_id="sub_test_123", item_id="si_test_item"):
    sub = MagicMock()
    sub.id = sub_id
    sub["items"] = {"data": [{"id": item_id}]}
    return sub


# ---------------------------------------------------------------------------
# Task 1 — 3.3: proration on upgrade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.routers.auth.log_activity")
@patch("backend.routers.auth.stripe.Subscription.modify")
@patch("backend.routers.auth.stripe.Subscription.list")
@patch("backend.routers.auth.ensure_stripe_configured")
@patch("backend.routers.auth.ensure_plan_prices_configured")
@patch("backend.routers.auth.get_service_supabase")
async def test_plan_upgrade_calls_stripe_with_create_prorations(
    mock_db_factory,
    mock_prices,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """Upgrading from growth → professional passes proration_behavior='create_prorations'."""
    from backend.routers.auth import billing_change_plan

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "growth",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain]
    mock_db_factory.return_value = db

    mock_prices.return_value = {"monthly": "price_professional"}
    mock_sub_list.return_value = MagicMock(data=[_make_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"plan": "professional"}

    request.json = json_body

    result = await billing_change_plan(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    mock_sub_modify.assert_called_once()
    call_kwargs = mock_sub_modify.call_args.kwargs
    assert call_kwargs.get("proration_behavior") == "create_prorations", (
        f"Expected proration_behavior='create_prorations', got {call_kwargs.get('proration_behavior')!r}"
    )
    assert result["status"] == "changed"
    assert result["new_plan"] == "professional"


@pytest.mark.asyncio
@patch("backend.routers.auth.log_activity")
@patch("backend.routers.auth.stripe.Subscription.modify")
@patch("backend.routers.auth.stripe.Subscription.list")
@patch("backend.routers.auth.ensure_stripe_configured")
@patch("backend.routers.auth.ensure_plan_prices_configured")
@patch("backend.routers.auth.get_service_supabase")
async def test_plan_downgrade_calls_stripe_with_create_prorations(
    mock_db_factory,
    mock_prices,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """Downgrading from enterprise → growth also passes proration_behavior='create_prorations'."""
    from backend.routers.auth import billing_change_plan

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "enterprise",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain]
    mock_db_factory.return_value = db

    mock_prices.return_value = {"monthly": "price_growth"}
    mock_sub_list.return_value = MagicMock(data=[_make_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"plan": "growth"}

    request.json = json_body

    result = await billing_change_plan(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    mock_sub_modify.assert_called_once()
    call_kwargs = mock_sub_modify.call_args.kwargs
    assert call_kwargs.get("proration_behavior") == "create_prorations"
    assert result["status"] == "changed"
    assert result["old_plan"] == "enterprise"
    assert result["new_plan"] == "growth"


@pytest.mark.asyncio
@patch("backend.routers.auth.log_activity")
@patch("backend.routers.auth.stripe.Subscription.modify")
@patch("backend.routers.auth.stripe.Subscription.list")
@patch("backend.routers.auth.ensure_stripe_configured")
@patch("backend.routers.auth.ensure_plan_prices_configured")
@patch("backend.routers.auth.get_service_supabase")
async def test_plan_change_updates_tenant_db_immediately(
    mock_db_factory,
    mock_prices,
    _mock_ensure,
    mock_sub_list,
    mock_sub_modify,
    mock_log,
):
    """DB plan update fires immediately; webhook will also fire but that's OK.

    Contract: tenant.plan is set to new_plan right after stripe modify, NOT
    deferred to the webhook. This means a downgrade takes effect immediately
    in DB even before Stripe fires the subscription.updated event.
    """
    from backend.routers.auth import billing_change_plan

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "professional",
    }])
    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_chain, tenant_update_chain]
    mock_db_factory.return_value = db

    mock_prices.return_value = {"monthly": "price_autopilot"}
    mock_sub_list.return_value = MagicMock(data=[_make_sub()])
    mock_sub_modify.return_value = MagicMock()

    request = MagicMock()

    async def json_body():
        return {"plan": "autopilot"}

    request.json = json_body

    await billing_change_plan(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    # tenant update should have been called with the new plan
    assert tenant_update_chain.updated is not None, "tenants.update() was not called"
    assert tenant_update_chain.updated.get("plan") == "autopilot"


@pytest.mark.asyncio
@patch("backend.routers.auth.ensure_stripe_configured")
@patch("backend.routers.auth.ensure_plan_prices_configured")
@patch("backend.routers.auth.get_service_supabase")
async def test_plan_change_to_same_plan_rejected(
    mock_db_factory,
    mock_prices,
    _mock_ensure,
):
    """Trying to change to the same plan raises 400."""
    from fastapi import HTTPException
    from backend.routers.auth import billing_change_plan

    tenant_chain = Chain(data=[{
        "stripe_customer_id": "cus_test",
        "plan": "growth",
    }])
    db = MagicMock()
    db.table.side_effect = [tenant_chain]
    mock_db_factory.return_value = db
    mock_prices.return_value = {"monthly": "price_growth"}

    request = MagicMock()

    async def json_body():
        return {"plan": "growth"}

    request.json = json_body

    with pytest.raises(HTTPException) as exc_info:
        await billing_change_plan(
            request,
            claims={"tenant_id": "tenant-1", "role": "owner"},
        )
    assert exc_info.value.status_code == 400
    assert "already on this plan" in exc_info.value.detail.lower()
