"""Checkout charges immediately for both paid plans (no trial).

Contract (changed 2026-06-17 by product decision — charge on signup, no
free trial): billing_checkout calls stripe.checkout.Session.create WITHOUT
subscription_data.trial_period_days, so the first charge happens at checkout.
The subscription is "active" once payment succeeds, which is_pay_gated()
treats as paid -> dashboard unlocks immediately. Existing "trialing"
subscriptions created before this change are unaffected.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _Chain:
    def __init__(self, data=None):
        self.data = data or []

    def select(self, *a, **kw):
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        return MagicMock(data=self.data)


def _db():
    db = MagicMock()
    db.table.return_value = _Chain(
        data=[{"id": "tenant-1", "owner_email": "o@test.com", "business_name": "Acme"}]
    )
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("plan", ["chatbot", "agent_os"])
@patch("backend.routers.auth_billing.stripe.checkout.Session.create")
@patch("backend.routers.auth_billing.get_or_create_customer")
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.ensure_plan_prices_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_checkout_charges_immediately_no_trial(
    mock_db, mock_prices, _mock_ensure, mock_customer, mock_session_create, plan
):
    from backend.routers.auth_billing import billing_checkout

    mock_db.return_value = _db()
    mock_prices.return_value = {"monthly": f"price_{plan}"}
    mock_customer.return_value = MagicMock(id="cus_test")
    mock_session_create.return_value = MagicMock(url="https://checkout.stripe.com/c/test")

    request = MagicMock()

    async def json_body():
        return {"plan": plan}

    request.json = json_body

    result = await billing_checkout(
        request, claims={"tenant_id": "tenant-1", "role": "owner"}
    )

    mock_session_create.assert_called_once()
    kwargs = mock_session_create.call_args.kwargs
    assert kwargs["mode"] == "subscription"
    assert "trial_period_days" not in kwargs["subscription_data"], (
        f"{plan}: expected no trial (immediate charge), got "
        f"{kwargs['subscription_data'].get('trial_period_days')!r}"
    )
    assert result["checkout_url"].startswith("https://checkout.stripe.com")
