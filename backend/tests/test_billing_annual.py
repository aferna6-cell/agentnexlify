"""Annual prepay billing (2026-08-25).

Contract:
  - Two billing intervals: "monthly" (default) and "annual" (2 months free —
    chatbot $199.90/yr, agent_os $999.90/yr).
  - ensure_plan_prices_configured validates ONLY the requested interval, so an
    unconfigured annual price never blocks monthly checkout (and vice versa).
  - Checkout endpoints accept billing_interval, pick the matching price, and
    stamp billing_interval into session + subscription metadata.
  - Annual amounts resolve to the same plan names in AMOUNT_TO_PLAN, so the
    webhook amount fallback activates annual tenants correctly.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.routers.billing import AMOUNT_TO_PLAN, _resolve_plan
from backend.services import stripe_service
from backend.services.stripe_service import (
    BILLING_INTERVALS,
    ensure_plan_prices_configured,
)
from backend.tests.fake_supabase import db as _db, run as _run


class _FakeRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


# --- price configuration -----------------------------------------------------


class TestEnsurePlanPricesConfigured:
    def test_intervals_are_monthly_and_annual(self):
        assert BILLING_INTERVALS == ("monthly", "annual")

    def test_monthly_ok_when_annual_is_placeholder(self):
        """An unconfigured annual price must not block monthly checkout."""
        prices = {
            "chatbot": {
                "monthly": "price_live_chatbot_m",
                "annual": "price_chatbot_annual",  # placeholder
            }
        }
        with patch.object(stripe_service, "PLAN_PRICES", prices):
            out = ensure_plan_prices_configured("chatbot", "monthly")
        assert out["monthly"] == "price_live_chatbot_m"

    def test_annual_placeholder_raises_for_annual(self):
        prices = {
            "agent_os": {
                "monthly": "price_live_agent_os_m",
                "annual": "price_agent_os_annual",  # placeholder
            }
        }
        with patch.object(stripe_service, "PLAN_PRICES", prices):
            with pytest.raises(RuntimeError, match="annual"):
                ensure_plan_prices_configured("agent_os", "annual")

    def test_annual_ok_when_configured(self):
        prices = {
            "agent_os": {
                "monthly": "price_agent_os_monthly",  # placeholder — irrelevant
                "annual": "price_live_agent_os_a",
            }
        }
        with patch.object(stripe_service, "PLAN_PRICES", prices):
            out = ensure_plan_prices_configured("agent_os", "annual")
        assert out["annual"] == "price_live_agent_os_a"

    def test_unknown_interval_raises(self):
        with pytest.raises(RuntimeError, match="interval"):
            ensure_plan_prices_configured("chatbot", "weekly")

    def test_malformed_price_raises(self):
        prices = {"chatbot": {"monthly": "not_a_price_id"}}
        with patch.object(stripe_service, "PLAN_PRICES", prices):
            with pytest.raises(RuntimeError, match="price_"):
                ensure_plan_prices_configured("chatbot", "monthly")

    def test_setup_price_still_validated(self):
        prices = {
            "chatbot": {
                "monthly": "price_live_chatbot_m",
                "setup": "bad_setup_id",
            }
        }
        with patch.object(stripe_service, "PLAN_PRICES", prices):
            with pytest.raises(RuntimeError, match="setup"):
                ensure_plan_prices_configured("chatbot", "monthly")

    def test_plan_prices_carry_both_intervals(self):
        for plan in ("chatbot", "agent_os"):
            assert set(stripe_service.PLAN_PRICES[plan]) >= {"monthly", "annual"}


# --- webhook amount fallback -------------------------------------------------


class TestAnnualAmounts:
    def test_chatbot_annual_amount(self):
        assert AMOUNT_TO_PLAN[19990] == "chatbot"  # $199.90/yr

    def test_agent_os_annual_amount(self):
        assert AMOUNT_TO_PLAN[99990] == "agent_os"  # $999.90/yr

    def test_resolve_plan_from_annual_amount(self):
        assert _resolve_plan({"amount_total": 99990}) == "agent_os"
        assert _resolve_plan({"amount_total": 19990}) == "chatbot"


# --- JWT checkout endpoint ---------------------------------------------------


class TestAuthBillingCheckoutAnnual:
    def _tenant_db(self):
        return _db(
            {
                "tenants": [
                    {
                        "id": "t1",
                        "owner_email": "owner@example.com",
                        "business_name": "Biz",
                    }
                ]
            }
        )

    def _checkout(self, body):
        from backend.routers import auth_billing

        session = MagicMock()
        session.url = "https://stripe.example/session"
        stripe_mock = MagicMock()
        stripe_mock.checkout.Session.create.return_value = session
        customer = MagicMock()
        customer.id = "cus_1"
        with patch.object(auth_billing, "stripe", stripe_mock), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={
                "monthly": "price_live_m",
                "annual": "price_live_a",
            },
        ) as ensure_mock, patch.object(
            auth_billing, "ensure_stripe_configured"
        ), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ), patch.object(
            auth_billing, "get_or_create_customer", return_value=customer
        ):
            out = _run(
                auth_billing.billing_checkout(
                    request=_FakeRequest(body),
                    claims={"tenant_id": "t1"},
                )
            )
        return out, stripe_mock, ensure_mock

    def test_annual_interval_uses_annual_price(self):
        out, stripe_mock, ensure_mock = self._checkout(
            {"plan": "agent_os", "billing_interval": "annual"}
        )
        assert out["checkout_url"] == "https://stripe.example/session"
        ensure_mock.assert_called_once_with("agent_os", "annual")
        params = stripe_mock.checkout.Session.create.call_args.kwargs
        assert params["line_items"] == [{"price": "price_live_a", "quantity": 1}]
        assert params["metadata"]["billing_interval"] == "annual"
        assert params["subscription_data"]["metadata"]["billing_interval"] == "annual"
        assert params["metadata"]["plan"] == "agent_os"

    def test_default_interval_is_monthly(self):
        out, stripe_mock, ensure_mock = self._checkout({"plan": "chatbot"})
        ensure_mock.assert_called_once_with("chatbot", "monthly")
        params = stripe_mock.checkout.Session.create.call_args.kwargs
        assert params["line_items"] == [{"price": "price_live_m", "quantity": 1}]
        assert params["metadata"]["billing_interval"] == "monthly"

    def test_invalid_interval_400s(self):
        from fastapi import HTTPException

        from backend.routers import auth_billing

        with patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            with pytest.raises(HTTPException) as err:
                _run(
                    auth_billing.billing_checkout(
                        request=_FakeRequest(
                            {"plan": "chatbot", "billing_interval": "weekly"}
                        ),
                        claims={"tenant_id": "t1"},
                    )
                )
        assert err.value.status_code == 400
        assert "billing_interval" in str(err.value.detail)

    def test_unconfigured_annual_503s(self):
        """Annual requested but env price not set → 503 with actionable detail."""
        from fastapi import HTTPException

        from backend.routers import auth_billing

        with patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            side_effect=RuntimeError(
                "Stripe price IDs for agent_os are not configured: annual"
            ),
        ), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            with pytest.raises(HTTPException) as err:
                _run(
                    auth_billing.billing_checkout(
                        request=_FakeRequest(
                            {"plan": "agent_os", "billing_interval": "annual"}
                        ),
                        claims={"tenant_id": "t1"},
                    )
                )
        assert err.value.status_code == 503
        assert "annual" in str(err.value.detail)


# --- API-secret checkout endpoint --------------------------------------------


class TestCreateCheckoutAnnual:
    def _tenant_db(self):
        return _db(
            {
                "tenants": [
                    {
                        "id": "t1",
                        "owner_email": "owner@example.com",
                        "business_name": "Biz",
                    }
                ]
            }
        )

    def test_annual_interval_on_create_checkout(self):
        from backend.models.schemas import CreateCheckoutRequest
        from backend.routers import billing

        session = MagicMock()
        session.url = "https://stripe.example/session2"
        session.id = "cs_1"
        stripe_mock = MagicMock()
        stripe_mock.checkout.Session.create.return_value = session
        customer = MagicMock()
        customer.id = "cus_1"
        req = CreateCheckoutRequest(
            tenant_id="t1", plan="agent_os", billing_interval="annual"
        )
        with patch.object(billing, "stripe", stripe_mock), patch.object(
            billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_m", "annual": "price_live_a"},
        ) as ensure_mock, patch.object(
            billing, "ensure_stripe_configured"
        ), patch.object(
            billing, "get_service_supabase", return_value=self._tenant_db()
        ), patch.object(
            billing, "get_or_create_customer", return_value=customer
        ):
            out = _run(billing.create_checkout(req, _=None))
        assert out.checkout_url == "https://stripe.example/session2"
        ensure_mock.assert_called_once_with("agent_os", "annual")
        params = stripe_mock.checkout.Session.create.call_args.kwargs
        assert params["line_items"] == [{"price": "price_live_a", "quantity": 1}]
        assert params["metadata"]["billing_interval"] == "annual"

    def test_schema_defaults_to_monthly(self):
        from backend.models.schemas import CreateCheckoutRequest

        req = CreateCheckoutRequest(tenant_id="t1", plan="chatbot")
        assert req.billing_interval == "monthly"


# --- change-plan interval switching ------------------------------------------


class TestChangePlanAnnual:
    def _tenant_db(self, plan="agent_os"):
        return _db(
            {"tenants": [{"stripe_customer_id": "cus_1", "plan": plan}]}
        )

    def _sub_mock(self, current_price_id="price_live_m"):
        sub_item = {"id": "si_1", "price": {"id": current_price_id}}
        sub = MagicMock()
        sub.__getitem__ = lambda self, key: {"items": {"data": [sub_item]}}[key]
        sub.id = "sub_1"
        subs = MagicMock()
        subs.data = [sub]
        return subs

    def test_same_plan_annual_switch_allowed(self):
        """agent_os monthly -> agent_os annual is a real change, not a 400."""
        from backend.routers import auth_billing

        stripe_mock = MagicMock()
        stripe_mock.Subscription.list.return_value = self._sub_mock("price_live_m")
        with patch.object(auth_billing, "stripe", stripe_mock), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_m", "annual": "price_live_a"},
        ) as ensure_mock, patch.object(
            auth_billing, "ensure_stripe_configured"
        ), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            out = _run(
                auth_billing.billing_change_plan(
                    request=_FakeRequest(
                        {"plan": "agent_os", "billing_interval": "annual"}
                    ),
                    claims={"tenant_id": "t1"},
                )
            )
        assert out["new_plan"] == "agent_os"
        ensure_mock.assert_called_once_with("agent_os", "annual")
        modify_kwargs = stripe_mock.Subscription.modify.call_args.kwargs
        assert modify_kwargs["items"] == [{"id": "si_1", "price": "price_live_a"}]
        assert modify_kwargs["metadata"]["billing_interval"] == "annual"

    def test_same_plan_monthly_still_400s(self):
        from fastapi import HTTPException

        from backend.routers import auth_billing

        with patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_m", "annual": "price_live_a"},
        ), patch.object(auth_billing, "ensure_stripe_configured"):
            with pytest.raises(HTTPException) as err:
                _run(
                    auth_billing.billing_change_plan(
                        request=_FakeRequest({"plan": "agent_os"}),
                        claims={"tenant_id": "t1"},
                    )
                )
        assert err.value.status_code == 400
        assert "Already" in str(err.value.detail)

    def test_already_on_annual_price_400s(self):
        """Same plan + annual when the sub already sits on the annual price."""
        from fastapi import HTTPException

        from backend.routers import auth_billing

        stripe_mock = MagicMock()
        stripe_mock.Subscription.list.return_value = self._sub_mock("price_live_a")
        with patch.object(auth_billing, "stripe", stripe_mock), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_m", "annual": "price_live_a"},
        ), patch.object(auth_billing, "ensure_stripe_configured"), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            with pytest.raises(HTTPException) as err:
                _run(
                    auth_billing.billing_change_plan(
                        request=_FakeRequest(
                            {"plan": "agent_os", "billing_interval": "annual"}
                        ),
                        claims={"tenant_id": "t1"},
                    )
                )
        assert err.value.status_code == 400
        assert "Already" in str(err.value.detail)
        stripe_mock.Subscription.modify.assert_not_called()
