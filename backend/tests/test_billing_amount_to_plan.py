"""Tests for AMOUNT_TO_PLAN mapping in billing.py.

Current pricing (CLAUDE.md "Plan names + prices") in Stripe cents:
  9900  -> growth       ($99 Starter)
  15000 -> autopilot    ($150 Growth)
  25000 -> professional ($250 Pro)
  89900 -> enterprise   ($899)

Legacy amounts (24900/29900/49900/19900/39900/79900 + setup-fee combos) stay
mapped for existing subscribers billed on old contracts.

Issue #181 supersedes the old issue #81: a checkout at the CURRENT advertised
$150/$250 price produced amount_total 15000/25000, which were absent from the
map, so _resolve_plan() fell through and the paid plan never provisioned. The
prior #81-era assertions ("15000/25000 must NOT be present") encoded the old
pricing and are inverted below.
"""

import pytest

from backend.routers.billing import AMOUNT_TO_PLAN, _resolve_plan


class TestAmountToPlanMapping:
    """Verify the AMOUNT_TO_PLAN dict has correct current and legacy pricing."""

    def test_current_growth_pricing(self):
        assert AMOUNT_TO_PLAN[9900] == "growth"

    def test_current_autopilot_pricing(self):
        """Issue #181: $150 autopilot checkout = amount_total 15000."""
        assert AMOUNT_TO_PLAN[15000] == "autopilot"

    def test_current_professional_pricing(self):
        """Issue #181: $250 professional checkout = amount_total 25000."""
        assert AMOUNT_TO_PLAN[25000] == "professional"

    def test_current_enterprise_pricing(self):
        assert AMOUNT_TO_PLAN[89900] == "enterprise"

    def test_enterprise_tier_is_present(self):
        """Issue #81 claimed enterprise was removed — verify it exists."""
        enterprise_amounts = [k for k, v in AMOUNT_TO_PLAN.items() if v == "enterprise"]
        assert len(enterprise_amounts) >= 1, "enterprise plan must have at least one amount mapping"

    def test_legacy_growth_pricing(self):
        """Legacy $199 growth tenants still resolve correctly."""
        assert AMOUNT_TO_PLAN[19900] == "growth"

    def test_legacy_professional_pricing(self):
        assert AMOUNT_TO_PLAN[39900] == "professional"

    def test_legacy_enterprise_pricing(self):
        assert AMOUNT_TO_PLAN[79900] == "enterprise"

    def test_all_four_current_tiers_present(self):
        # Current advertised prices (CLAUDE.md), in Stripe cents.
        current_prices = {9900: "growth", 15000: "autopilot", 25000: "professional", 89900: "enterprise"}
        for amount, plan in current_prices.items():
            assert AMOUNT_TO_PLAN.get(amount) == plan, f"{amount} should map to {plan}"


class TestResolvePlan:
    """Unit tests for _resolve_plan() helper."""

    def test_resolve_by_metadata_plan(self):
        session = {"metadata": {"plan": "growth"}}
        assert _resolve_plan(session) == "growth"

    def test_resolve_by_amount_growth(self):
        session = {"amount_total": 24900}
        assert _resolve_plan(session) == "growth"

    def test_resolve_by_amount_autopilot(self):
        session = {"amount_total": 15000}
        assert _resolve_plan(session) == "autopilot"

    def test_resolve_by_amount_professional(self):
        session = {"amount_total": 25000}
        assert _resolve_plan(session) == "professional"

    def test_resolve_legacy_autopilot_amount_still_works(self):
        session = {"amount_total": 29900}
        assert _resolve_plan(session) == "autopilot"

    def test_resolve_legacy_professional_amount_still_works(self):
        session = {"amount_total": 49900}
        assert _resolve_plan(session) == "professional"

    def test_resolve_by_amount_enterprise(self):
        session = {"amount_total": 89900}
        assert _resolve_plan(session) == "enterprise"

    def test_metadata_takes_precedence_over_amount(self):
        session = {"metadata": {"plan": "enterprise"}, "amount_total": 24900}
        assert _resolve_plan(session) == "enterprise"

    def test_unknown_amount_returns_none(self):
        session = {"amount_total": 99999}
        result = _resolve_plan(session)
        assert result is None

    def test_invalid_plan_in_metadata_falls_through_to_amount(self):
        session = {"metadata": {"plan": "invalid_plan"}, "amount_total": 24900}
        assert _resolve_plan(session) == "growth"
