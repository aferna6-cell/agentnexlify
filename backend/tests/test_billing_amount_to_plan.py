"""Tests for AMOUNT_TO_PLAN mapping and plan resolution in billing.py.

Two-plan repricing (2026-06-15):
  1999  -> chatbot   ($19.99/mo widget/chatbot features only)
  9999  -> agent_os  ($99.99/mo full platform)

"free" is NOT a purchasable plan — it is the internal lapsed/no-active-subscription
state set when a subscription is cancelled.
"""

import pytest

from backend.routers.billing import AMOUNT_TO_PLAN, _resolve_plan


class TestAmountToPlanMapping:
    """Verify the AMOUNT_TO_PLAN dict has the two-plan repricing amounts."""

    def test_chatbot_pricing(self):
        assert AMOUNT_TO_PLAN[1999] == "chatbot"

    def test_agent_os_pricing(self):
        assert AMOUNT_TO_PLAN[9999] == "agent_os"

    def test_only_two_purchasable_plans(self):
        """Exactly two purchasable plan values in the map."""
        plan_values = set(AMOUNT_TO_PLAN.values())
        assert plan_values == {"chatbot", "agent_os"}

    def test_free_not_in_amount_map(self):
        """free is an internal state, never sold via checkout."""
        assert "free" not in AMOUNT_TO_PLAN.values()

    def test_legacy_amounts_absent(self):
        """Old plan amounts (growth/autopilot/professional/enterprise) are gone."""
        legacy_amounts = {9900, 15000, 25000, 89900, 19900, 24900, 29900, 39900, 49900, 79900}
        for amount in legacy_amounts:
            assert amount not in AMOUNT_TO_PLAN, f"Legacy amount {amount} should not be in AMOUNT_TO_PLAN"


class TestResolvePlan:
    """Unit tests for _resolve_plan() helper."""

    def test_resolve_chatbot_by_metadata(self):
        session = {"metadata": {"plan": "chatbot"}}
        assert _resolve_plan(session) == "chatbot"

    def test_resolve_agent_os_by_metadata(self):
        session = {"metadata": {"plan": "agent_os"}}
        assert _resolve_plan(session) == "agent_os"

    def test_resolve_chatbot_by_amount(self):
        session = {"amount_total": 1999}
        assert _resolve_plan(session) == "chatbot"

    def test_resolve_agent_os_by_amount(self):
        session = {"amount_total": 9999}
        assert _resolve_plan(session) == "agent_os"

    def test_metadata_takes_precedence_over_amount(self):
        session = {"metadata": {"plan": "agent_os"}, "amount_total": 1999}
        assert _resolve_plan(session) == "agent_os"

    def test_unknown_amount_returns_none(self):
        session = {"amount_total": 99999}
        assert _resolve_plan(session) is None

    def test_invalid_plan_in_metadata_falls_through_to_amount(self):
        session = {"metadata": {"plan": "growth"}, "amount_total": 9999}
        assert _resolve_plan(session) == "agent_os"

    def test_no_metadata_no_amount_returns_none(self):
        session = {}
        assert _resolve_plan(session) is None

    def test_free_in_metadata_is_valid_lapsed_state(self):
        """free is allowed in metadata (e.g. internal system sets it) but resolves."""
        session = {"metadata": {"plan": "free"}}
        assert _resolve_plan(session) == "free"
