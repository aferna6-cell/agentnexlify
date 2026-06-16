"""Checkout creates a 7-day trial subscription for both paid plans.

Contract: billing_checkout calls stripe.checkout.Session.create with
subscription_data.trial_period_days == 7 so a new customer's card is captured
but not charged until day 7. The subscription is "trialing" during the window,
which is_pay_gated() treats as paid -> dashboard unlocks immediately.
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
async def test_checkout_includes_7_day_trial(
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
    assert kwargs["subscription_data"]["trial_period_days"] == 7, (
        f"{plan}: expected a 7-day trial, got "
        f"{kwargs['subscription_data'].get('trial_period_days')!r}"
    )
    assert result["checkout_url"].startswith("https://checkout.stripe.com")
