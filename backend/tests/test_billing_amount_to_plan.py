"""Tests for AMOUNT_TO_PLAN mapping in billing.py.

Verifies issue #81 (claimed broken in commit 821f660).
Current state inspection shows the mapping is CORRECT:
  24900 -> growth    ($249)
  29900 -> autopilot ($299)
  49900 -> professional ($499)
  89900 -> enterprise ($899)

Issue #81 can be closed — the bug is not present.
"""

import pytest

from backend.routers.billing import AMOUNT_TO_PLAN, _resolve_plan


class TestAmountToPlanMapping:
    """Verify the AMOUNT_TO_PLAN dict has correct current and legacy pricing."""

    def test_current_growth_pricing(self):
        assert AMOUNT_TO_PLAN[24900] == "growth"

    def test_current_autopilot_pricing(self):
        assert AMOUNT_TO_PLAN[29900] == "autopilot"

    def test_current_professional_pricing(self):
        assert AMOUNT_TO_PLAN[49900] == "professional"

    def test_current_enterprise_pricing(self):
        assert AMOUNT_TO_PLAN[89900] == "enterprise"

    def test_enterprise_tier_is_present(self):
        """Issue #81 claimed enterprise was removed — verify it exists."""
        enterprise_amounts = [k for k, v in AMOUNT_TO_PLAN.items() if v == "enterprise"]
        assert len(enterprise_amounts) >= 1, "enterprise plan must have at least one amount mapping"

    def test_no_wrong_15000_mapping(self):
        """Issue #81 claimed 15000->professional was present; verify it is NOT."""
        assert 15000 not in AMOUNT_TO_PLAN, "15000 should not be in AMOUNT_TO_PLAN"

    def test_no_wrong_25000_mapping(self):
        """Issue #81 claimed 25000->enterprise was present; verify it is NOT."""
        assert 25000 not in AMOUNT_TO_PLAN, "25000 should not be in AMOUNT_TO_PLAN"

    def test_legacy_growth_pricing(self):
        """Legacy $199 growth tenants still resolve correctly."""
        assert AMOUNT_TO_PLAN[19900] == "growth"

    def test_legacy_professional_pricing(self):
        assert AMOUNT_TO_PLAN[39900] == "professional"

    def test_legacy_enterprise_pricing(self):
        assert AMOUNT_TO_PLAN[79900] == "enterprise"

    def test_all_four_current_tiers_present(self):
        current_prices = {24900, 29900, 49900, 89900}
        for amount in current_prices:
            assert amount in AMOUNT_TO_PLAN, f"{amount} missing from AMOUNT_TO_PLAN"


class TestResolvePlan:
    """Unit tests for _resolve_plan() helper."""

    def test_resolve_by_metadata_plan(self):
        session = {"metadata": {"plan": "growth"}}
        assert _resolve_plan(session) == "growth"

    def test_resolve_by_amount_growth(self):
        session = {"amount_total": 24900}
        assert _resolve_plan(session) == "growth"

    def test_resolve_by_amount_autopilot(self):
        session = {"amount_total": 29900}
        assert _resolve_plan(session) == "autopilot"

    def test_resolve_by_amount_professional(self):
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
