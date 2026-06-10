"""Tests for backend/services/billing_reconciliation.py.

All tests use a fake in-memory DB — no Supabase network calls.
Covers:
  - within-cap tenant (no flags)
  - over-cap flagged for agent_runs
  - over-cap flagged for ai_tokens
  - over-cap flagged for conversations (when monthly_conversation_limit set)
  - missing os_tenant_usage row treated as zero (not an error)
  - missing tenant_ai_usage_monthly row treated as zero
  - tenant not found returns error row
  - DB failure on tenant load returns error row (does not raise)
  - reconcile_all iterates all tenants; db failure on list returns error row
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ── fake DB builder ──────────────────────────────────────────────────────────


class _FakeChain:
    """Chainable query mock that returns configurable data on execute()."""

    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        return MagicMock(data=self._data)


def _make_db(
    *,
    tenant: dict | None = None,
    os_usage_rows: list | None = None,
    ai_usage_rows: list | None = None,
    tenant_raise: bool = False,
    os_usage_raise: bool = False,
    ai_usage_raise: bool = False,
    all_tenants: list | None = None,
):
    """Build a MagicMock DB with table() side_effect routing.

    Call order when reconcile_tenant_usage is invoked:
        1. tenants (select)
        2. os_tenant_usage (select)
        3. tenant_ai_usage_monthly (select)

    When reconcile_all is invoked:
        0. tenants (select id — all tenants)
        then per-tenant calls as above.
    """
    tenants_data = [tenant] if tenant is not None else []
    os_rows = os_usage_rows if os_usage_rows is not None else []
    ai_rows = ai_usage_rows if ai_usage_rows is not None else []

    call_count = [0]

    def _table_router(name: str):
        call_count[0] += 1

        if name == "tenants":
            if all_tenants is not None and call_count[0] == 1:
                # first call is the list-all-tenants query in reconcile_all
                return _FakeChain(data=all_tenants)
            if tenant_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=tenants_data)

        if name == "os_tenant_usage":
            if os_usage_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=os_rows)

        if name == "tenant_ai_usage_monthly":
            if ai_usage_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=ai_rows)

        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _table_router
    return db


# ── happy-path: within cap ───────────────────────────────────────────────────


class TestWithinCap:
    def test_under_cap_no_flags(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-1",
                "plan": "growth",
                "conversations_used_this_month": 50,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            os_usage_rows=[{"agent_runs": 100}],
            ai_usage_rows=[{"total_tokens": 500_000}],
        )

        result = reconcile_tenant_usage(db, "t-1")

        assert result["error"] is None
        assert result["any_over_cap"] is False
        assert result["agent_runs"]["over_cap"] is False
        assert result["ai_tokens"]["over_cap"] is False
        assert result["conversations"]["over_cap"] is False

    def test_plan_resolves_to_growth_caps(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-1",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
        )

        result = reconcile_tenant_usage(db, "t-1")

        # growth: 200 agent runs, 1_000_000 * 5 = 5_000_000 AI tokens
        assert result["agent_runs"]["cap"] == 200
        assert result["ai_tokens"]["hard_limit"] == 5_000_000

    def test_conversations_unlimited_when_no_cap(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-1",
                "plan": "free",
                "conversations_used_this_month": 999,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
        )

        result = reconcile_tenant_usage(db, "t-1")

        assert result["conversations"]["cap"] is None
        assert result["conversations"]["over_cap"] is False
        assert result["conversations"]["drift_pct"] is None


# ── over-cap detection ───────────────────────────────────────────────────────


class TestOverCap:
    def test_agent_runs_over_cap_flagged(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-2",
                "plan": "free",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            os_usage_rows=[{"agent_runs": 26}],  # free cap = 25
        )

        result = reconcile_tenant_usage(db, "t-2")

        assert result["agent_runs"]["over_cap"] is True
        assert result["any_over_cap"] is True
        assert result["agent_runs"]["cap"] == 25
        assert result["agent_runs"]["used"] == 26

    def test_ai_tokens_over_cap_flagged(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        # free plan: baseline 150_000 * 5 = 750_000 hard limit
        db = _make_db(
            tenant={
                "id": "t-3",
                "plan": "free",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            ai_usage_rows=[{"total_tokens": 800_000}],  # over 750_000
        )

        result = reconcile_tenant_usage(db, "t-3")

        assert result["ai_tokens"]["over_cap"] is True
        assert result["ai_tokens"]["hard_limit"] == 750_000
        assert result["any_over_cap"] is True

    def test_conversations_over_cap_when_limit_set(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-4",
                "plan": "growth",
                "conversations_used_this_month": 501,
                "monthly_conversation_limit": 500,
                "ai_monthly_token_hard_limit": None,
            },
        )

        result = reconcile_tenant_usage(db, "t-4")

        assert result["conversations"]["over_cap"] is True
        assert result["conversations"]["cap"] == 500
        assert result["conversations"]["used"] == 501
        assert result["any_over_cap"] is True

    def test_tenant_override_ai_limit_respected(self):
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-5",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": 10_000,  # custom
            },
            ai_usage_rows=[{"total_tokens": 10_001}],
        )

        result = reconcile_tenant_usage(db, "t-5")

        assert result["ai_tokens"]["hard_limit"] == 10_000
        assert result["ai_tokens"]["over_cap"] is True


# ── missing rows treated as zero ─────────────────────────────────────────────


class TestMissingUsageRows:
    def test_missing_os_usage_row_treated_as_zero(self):
        """No os_tenant_usage row for this cycle → agent_runs = 0, no error."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-6",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            os_usage_rows=[],  # empty
        )

        result = reconcile_tenant_usage(db, "t-6")

        assert result["agent_runs"]["used"] == 0
        assert result["error"] is None

    def test_missing_ai_usage_row_treated_as_zero(self):
        """No tenant_ai_usage_monthly row → ai_tokens = 0, no error."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-7",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            ai_usage_rows=[],  # empty
        )

        result = reconcile_tenant_usage(db, "t-7")

        assert result["ai_tokens"]["used"] == 0
        assert result["error"] is None

    def test_conversations_none_in_db_treated_as_zero(self):
        """NULL conversations_used_this_month treated as 0."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-8",
                "plan": "free",
                "conversations_used_this_month": None,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
        )

        result = reconcile_tenant_usage(db, "t-8")

        assert result["conversations"]["used"] == 0
        assert result["error"] is None


# ── DB failure handling ───────────────────────────────────────────────────────


class TestDbFailures:
    def test_tenant_not_found_returns_error_row(self):
        """Empty tenants result → error field set, no exception."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(tenant=None)  # no tenant row

        result = reconcile_tenant_usage(db, "nonexistent-id")

        assert result["error"] == "tenant_not_found"
        assert result["any_over_cap"] is False  # should not raise

    def test_db_error_on_tenant_load_returns_error_row(self):
        """RuntimeError from DB on tenant select → error row, no exception raised."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(tenant_raise=True)

        result = reconcile_tenant_usage(db, "t-error")

        assert result["error"] == "db_error_tenant"

    def test_os_usage_db_error_treated_as_zero(self):
        """DB error on os_tenant_usage → agent_runs = 0, no overall error."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-9",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            os_usage_raise=True,
        )

        result = reconcile_tenant_usage(db, "t-9")

        assert result["agent_runs"]["used"] == 0
        assert result["error"] is None  # not a fatal error

    def test_ai_usage_db_error_treated_as_zero(self):
        """DB error on tenant_ai_usage_monthly → ai_tokens = 0, no overall error."""
        from backend.services.billing_reconciliation import reconcile_tenant_usage

        db = _make_db(
            tenant={
                "id": "t-10",
                "plan": "growth",
                "conversations_used_this_month": 0,
                "monthly_conversation_limit": None,
                "ai_monthly_token_hard_limit": None,
            },
            ai_usage_raise=True,
        )

        result = reconcile_tenant_usage(db, "t-10")

        assert result["ai_tokens"]["used"] == 0
        assert result["error"] is None


# ── reconcile_all ─────────────────────────────────────────────────────────────


class TestReconcileAll:
    def test_reconcile_all_iterates_tenants(self):
        from backend.services.billing_reconciliation import reconcile_all

        # Build a DB that returns 2 tenant IDs on first call,
        # then per-tenant data on subsequent calls.
        tenants_resp = [{"id": "ta-1"}, {"id": "ta-2"}]
        tenant_row = {
            "id": "PLACEHOLDER",
            "plan": "free",
            "conversations_used_this_month": 0,
            "monthly_conversation_limit": None,
            "ai_monthly_token_hard_limit": None,
        }

        call_seq = [0]

        def _table(name: str):
            call_seq[0] += 1
            if name == "tenants" and call_seq[0] == 1:
                return _FakeChain(data=tenants_resp)
            if name == "tenants":
                # individual tenant fetches; use generic row
                return _FakeChain(data=[{**tenant_row}])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _table

        results = reconcile_all(db)

        assert len(results) == 2
        for r in results:
            assert r.get("error") is None

    def test_reconcile_all_db_failure_on_list_returns_error(self):
        """DB failure on the initial list-tenants query → error result, no raise."""
        from backend.services.billing_reconciliation import reconcile_all

        db = MagicMock()
        db.table.return_value = _FakeChain(raise_on_execute=True)

        results = reconcile_all(db)

        assert len(results) == 1
        assert results[0].get("error") == "db_error_list_tenants"
