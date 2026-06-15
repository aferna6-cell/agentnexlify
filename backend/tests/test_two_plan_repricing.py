"""Tests for the two-plan repricing (2026-06-15).

Covers:
- plan->price mapping in stripe_service.py
- AMOUNT_TO_PLAN in billing.py
- marketing gate (chatbot blocked, agent_os allowed) in plan_gate.py
- baseline token caps per plan in ai_usage_guard.py
- customer-facing usage meter shape (no $/tokens) in get_ai_usage_status
- overage path: buy-usage creates checkout; webhook inserts a pack; effective cap rises
"""

import pytest
from unittest.mock import MagicMock, patch

# ---- stripe_service ----

class TestPlanPrices:
    def test_chatbot_plan_exists(self):
        from backend.services.stripe_service import PLAN_PRICES
        assert "chatbot" in PLAN_PRICES
        assert "monthly" in PLAN_PRICES["chatbot"]

    def test_agent_os_plan_exists(self):
        from backend.services.stripe_service import PLAN_PRICES
        assert "agent_os" in PLAN_PRICES
        assert "monthly" in PLAN_PRICES["agent_os"]

    def test_only_two_purchasable_plans(self):
        from backend.services.stripe_service import PLAN_PRICES
        assert set(PLAN_PRICES.keys()) == {"chatbot", "agent_os"}

    def test_usage_pack_price_id_exists(self):
        from backend.services.stripe_service import USAGE_PACK_PRICE_ID
        assert USAGE_PACK_PRICE_ID  # not empty string

    def test_placeholder_price_ids_match_new_names(self):
        from backend.services.stripe_service import _PLACEHOLDER_PRICE_IDS
        assert "price_chatbot_monthly" in _PLACEHOLDER_PRICE_IDS
        assert "price_agent_os_monthly" in _PLACEHOLDER_PRICE_IDS
        assert "price_usage_pack" in _PLACEHOLDER_PRICE_IDS

    def test_no_old_plan_placeholders(self):
        from backend.services.stripe_service import _PLACEHOLDER_PRICE_IDS
        old_placeholders = {
            "price_growth_monthly",
            "price_professional_monthly",
            "price_autopilot_monthly",
            "price_enterprise_monthly",
        }
        for placeholder in old_placeholders:
            assert placeholder not in _PLACEHOLDER_PRICE_IDS, (
                f"Old placeholder {placeholder!r} should not be in _PLACEHOLDER_PRICE_IDS"
            )


# ---- plan_gate ----

class TestMarketingGate:
    def test_agent_os_in_marketing_plans(self):
        from backend.services.plan_gate import MARKETING_PLANS
        assert "agent_os" in MARKETING_PLANS

    def test_chatbot_not_in_marketing_plans(self):
        from backend.services.plan_gate import MARKETING_PLANS
        assert "chatbot" not in MARKETING_PLANS

    def test_free_not_in_marketing_plans(self):
        from backend.services.plan_gate import MARKETING_PLANS
        assert "free" not in MARKETING_PLANS

    def test_chatbot_blocked_from_marketing(self):
        from backend.services.plan_gate import _tenant_plan, MARKETING_PLANS

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"plan": "chatbot"}]
        )
        with patch("backend.services.plan_gate.get_service_supabase", return_value=db):
            plan = _tenant_plan("test-tenant-id")
        assert plan not in MARKETING_PLANS

    def test_agent_os_allowed_for_marketing(self):
        from backend.services.plan_gate import _tenant_plan, MARKETING_PLANS

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"plan": "agent_os"}]
        )
        with patch("backend.services.plan_gate.get_service_supabase", return_value=db):
            plan = _tenant_plan("test-tenant-id")
        assert plan in MARKETING_PLANS


# ---- usage_meter ----

class TestPlanAgentRunCaps:
    def test_free_cap(self):
        from backend.services.usage_meter import PLAN_AGENT_RUN_CAPS
        assert PLAN_AGENT_RUN_CAPS["free"] == 25

    def test_chatbot_cap(self):
        from backend.services.usage_meter import PLAN_AGENT_RUN_CAPS
        assert PLAN_AGENT_RUN_CAPS["chatbot"] == 100

    def test_agent_os_cap(self):
        from backend.services.usage_meter import PLAN_AGENT_RUN_CAPS
        assert PLAN_AGENT_RUN_CAPS["agent_os"] == 2000

    def test_no_legacy_plan_caps(self):
        from backend.services.usage_meter import PLAN_AGENT_RUN_CAPS
        for old_plan in ("growth", "autopilot", "professional", "enterprise"):
            assert old_plan not in PLAN_AGENT_RUN_CAPS, (
                f"Legacy plan {old_plan!r} should not be in PLAN_AGENT_RUN_CAPS"
            )

    def test_plan_cap_resolves_chatbot(self):
        from backend.services.usage_meter import plan_cap

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"plan": "chatbot"}]
        )
        assert plan_cap(db, "tenant-id") == 100

    def test_plan_cap_resolves_agent_os(self):
        from backend.services.usage_meter import plan_cap

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"plan": "agent_os"}]
        )
        assert plan_cap(db, "tenant-id") == 2000

    def test_plan_cap_unknown_plan_uses_default(self):
        from backend.services.usage_meter import plan_cap, DEFAULT_AGENT_RUN_CAP

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"plan": "nonexistent_plan"}]
        )
        assert plan_cap(db, "tenant-id") == DEFAULT_AGENT_RUN_CAP


# ---- ai_usage_guard — baseline tokens ----

class TestPlanBaselineTokens:
    def test_free_baseline(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        assert PLAN_BASELINE_TOKENS["free"] == 100_000

    def test_chatbot_baseline(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        assert PLAN_BASELINE_TOKENS["chatbot"] == 800_000

    def test_agent_os_baseline(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        assert PLAN_BASELINE_TOKENS["agent_os"] == 5_000_000

    def test_no_legacy_plans_in_baseline(self):
        from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
        for old in ("growth", "autopilot", "professional", "enterprise"):
            assert old not in PLAN_BASELINE_TOKENS

    def test_resolve_policy_chatbot(self):
        from backend.services.ai_usage_guard import resolve_ai_usage_policy, ALERT_MULTIPLIER, HARD_LIMIT_MULTIPLIER

        tenant = {"plan": "chatbot", "id": None}
        # patch _sum_usage_packs to return 0
        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            policy = resolve_ai_usage_policy(tenant)
        assert policy.alert_threshold_tokens == 800_000 * ALERT_MULTIPLIER
        assert policy.hard_limit_tokens == 800_000 * HARD_LIMIT_MULTIPLIER

    def test_resolve_policy_agent_os(self):
        from backend.services.ai_usage_guard import resolve_ai_usage_policy, HARD_LIMIT_MULTIPLIER

        tenant = {"plan": "agent_os", "id": None}
        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            policy = resolve_ai_usage_policy(tenant)
        assert policy.hard_limit_tokens == 5_000_000 * HARD_LIMIT_MULTIPLIER


# ---- ai_usage_guard — customer-facing meter shape ----

class TestAIUsageMeterShape:
    def _db_with_tenant_and_usage(self, plan="chatbot", total_tokens=200_000):
        """Build a mock DB that returns a tenant row + usage row."""
        db = MagicMock()

        tenant_row = {
            "plan": plan,
            "ai_monthly_token_alert_threshold": None,
            "ai_monthly_token_hard_limit": None,
        }
        usage_row = {
            "input_tokens": total_tokens,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

        # First call returns tenant row, second returns usage row
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            m = MagicMock()
            if call_count[0] == 1:
                m.data = [tenant_row]
            else:
                m.data = [usage_row]
            return m

        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = side_effect
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[tenant_row])
        return db

    def test_meter_has_required_public_fields(self):
        from backend.services.ai_usage_guard import get_ai_usage_status

        db = MagicMock()
        # Setup for two sequential .execute() calls
        results = [
            MagicMock(data=[{"plan": "chatbot", "ai_monthly_token_alert_threshold": None, "ai_monthly_token_hard_limit": None}]),
            MagicMock(data=[{"input_tokens": 100_000, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}]),
        ]
        execute_mock = MagicMock(side_effect=results)
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute = execute_mock
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute = execute_mock

        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            with patch("backend.services.ai_usage_guard.get_service_supabase", return_value=db):
                status = get_ai_usage_status(db, "test-tenant")

        # Must have the customer-facing meter fields
        assert "limit_units" in status
        assert "used_units" in status
        assert "remaining_units" in status
        assert "pct_used" in status

    def test_meter_does_not_expose_raw_tokens(self):
        from backend.services.ai_usage_guard import get_ai_usage_status

        db = MagicMock()
        results = [
            MagicMock(data=[{"plan": "chatbot", "ai_monthly_token_alert_threshold": None, "ai_monthly_token_hard_limit": None}]),
            MagicMock(data=[{"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}]),
        ]
        execute_mock = MagicMock(side_effect=results)
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute = execute_mock
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute = execute_mock

        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            with patch("backend.services.ai_usage_guard.get_service_supabase", return_value=db):
                status = get_ai_usage_status(db, "test-tenant")

        # Must NOT expose raw token counts or dollar references
        assert "total_tokens" not in status
        assert "alert_threshold" not in status
        assert "hard_limit" not in status

    def test_pct_used_is_float(self):
        from backend.services.ai_usage_guard import get_ai_usage_status

        db = MagicMock()
        results = [
            MagicMock(data=[{"plan": "chatbot", "ai_monthly_token_alert_threshold": None, "ai_monthly_token_hard_limit": None}]),
            MagicMock(data=[{"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}]),
        ]
        execute_mock = MagicMock(side_effect=results)
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute = execute_mock
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute = execute_mock

        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            with patch("backend.services.ai_usage_guard.get_service_supabase", return_value=db):
                status = get_ai_usage_status(db, "test-tenant")

        assert isinstance(status["pct_used"], (int, float))
        assert 0.0 <= status["pct_used"] <= 100.0

    def test_remaining_units_never_negative(self):
        from backend.services.ai_usage_guard import get_ai_usage_status

        db = MagicMock()
        # Usage exceeds limit
        results = [
            MagicMock(data=[{"plan": "free", "ai_monthly_token_alert_threshold": None, "ai_monthly_token_hard_limit": None}]),
            MagicMock(data=[{"input_tokens": 999_999_999, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}]),
        ]
        execute_mock = MagicMock(side_effect=results)
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute = execute_mock
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute = execute_mock

        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            with patch("backend.services.ai_usage_guard.get_service_supabase", return_value=db):
                status = get_ai_usage_status(db, "test-tenant")

        assert status["remaining_units"] >= 0

    def test_fallback_shape_on_error(self):
        from backend.services.ai_usage_guard import get_ai_usage_status

        db = MagicMock()
        db.table.side_effect = Exception("DB down")

        with patch("backend.services.ai_usage_guard.get_service_supabase", return_value=db):
            status = get_ai_usage_status(db, "test-tenant")

        assert "limit_units" in status
        assert "used_units" in status
        assert "remaining_units" in status
        assert "pct_used" in status
        # fallback values should be safe (0s, False)
        assert status["used_units"] == 0
        assert status["pct_used"] == 0.0


# ---- overage / usage packs ----

class TestUsagePackEffectiveCap:
    def test_pack_bonus_added_to_hard_limit(self):
        from backend.services.ai_usage_guard import resolve_ai_usage_policy, HARD_LIMIT_MULTIPLIER

        tenant = {"plan": "chatbot", "id": "tenant-123"}
        pack_bonus = 500_000
        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=pack_bonus):
            policy = resolve_ai_usage_policy(tenant)

        expected_base = 800_000 * HARD_LIMIT_MULTIPLIER
        assert policy.hard_limit_tokens == expected_base + pack_bonus

    def test_no_packs_leaves_limit_unchanged(self):
        from backend.services.ai_usage_guard import resolve_ai_usage_policy, HARD_LIMIT_MULTIPLIER

        tenant = {"plan": "chatbot", "id": "tenant-123"}
        with patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0):
            policy = resolve_ai_usage_policy(tenant)

        assert policy.hard_limit_tokens == 800_000 * HARD_LIMIT_MULTIPLIER

    def test_sum_usage_packs_db_failure_returns_zero(self):
        from backend.services.ai_usage_guard import _sum_usage_packs

        with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
            mock_supa.return_value.table.side_effect = Exception("DB error")
            result = _sum_usage_packs("tenant-id", "2026-06-01")

        assert result == 0


class TestUsagePackWebhook:
    def test_handle_usage_pack_completed_inserts_row(self):
        from backend.routers.billing import _handle_usage_pack_completed

        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "pack-1"}])

        session = {
            "id": "cs_test_abc",
            "metadata": {"tenant_id": "t-1", "kind": "usage_pack"},
        }

        with patch("backend.services.ai_usage_guard.current_period_month", return_value="2026-06-01"):
            _handle_usage_pack_completed(db, session)

        db.table.assert_called_with("tenant_usage_packs")
        insert_call_args = db.table.return_value.insert.call_args[0][0]
        assert insert_call_args["tenant_id"] == "t-1"
        assert insert_call_args["stripe_session_id"] == "cs_test_abc"
        assert insert_call_args["tokens"] > 0

    def test_handle_usage_pack_no_tenant_id_skips(self):
        from backend.routers.billing import _handle_usage_pack_completed

        db = MagicMock()
        session = {"id": "cs_test_abc", "metadata": {}}

        _handle_usage_pack_completed(db, session)
        db.table.assert_not_called()

    def test_handle_usage_pack_idempotent_on_duplicate(self):
        """Second delivery of same session should NOT raise."""
        from backend.routers.billing import _handle_usage_pack_completed

        db = MagicMock()
        # First insert raises (e.g. unique constraint)
        db.table.return_value.insert.return_value.execute.side_effect = Exception("unique violation")
        # idempotency check finds existing row
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-pack"}]
        )

        session = {
            "id": "cs_test_abc",
            "metadata": {"tenant_id": "t-1", "kind": "usage_pack"},
        }

        with patch("backend.services.ai_usage_guard.current_period_month", return_value="2026-06-01"):
            # Should not raise
            _handle_usage_pack_completed(db, session)


class TestBuyUsageEndpoint:
    def test_buy_usage_requires_auth(self, client):
        resp = client.post("/api/v1/billing/buy-usage")
        assert resp.status_code in (401, 403, 422)

    def test_buy_usage_creates_checkout_session(self, client, auth_headers, mock_supabase):
        """Happy-path: authenticated request gets a checkout_url back."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "tenant-1",
                "owner_email": "test@example.com",
                "stripe_customer_id": None,
                "business_name": "Test Biz",
            }]
        )

        with patch("backend.routers.billing_usage.ensure_stripe_configured"):
            with patch("backend.routers.billing_usage.USAGE_PACK_PRICE_ID", "price_real_pack"):
                with patch("stripe.checkout.Session.create") as mock_create:
                    mock_create.return_value = MagicMock(url="https://checkout.stripe.com/test")
                    resp = client.post("/api/v1/billing/buy-usage", headers=auth_headers)

        assert resp.status_code == 200
        assert "checkout_url" in resp.json()

    def test_buy_usage_503_when_price_not_configured(self, client, auth_headers, mock_supabase):
        """Returns 503 when usage pack price is still a placeholder."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "tenant-1",
                "owner_email": "test@example.com",
                "stripe_customer_id": None,
                "business_name": "Test Biz",
            }]
        )

        # USAGE_PACK_PRICE_ID is "price_usage_pack" (placeholder) by default in test env
        resp = client.post("/api/v1/billing/buy-usage", headers=auth_headers)
        assert resp.status_code == 503
