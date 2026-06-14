"""Tests for GET /api/v1/admin/mrr-metrics.

Covers:
  - correct MRR math across all paid plans
  - mrr_by_plan breakdown per plan
  - churn rate calculation
  - divide-by-zero guard (zero active + zero cancellations)
  - 401 when admin secret is missing or wrong
  - fault tolerance: cancellation table query error → 200 with nulls
  - fault tolerance: dunning query error → 200 with null dunning_paused_count
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.limiter import limiter
from backend.routers.admin_analytics import PLAN_PRICE_CENTS

# Admin secret used in all authenticated requests
_ADMIN_SECRET = "test-admin-secret-mrr"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The 10/minute limit on /mrr-metrics is now actually enforced (decorator
    order fixed 2026-06-10 — limiter above @router.get never applied). The
    shared in-memory limiter must be reset between tests or the suite itself
    trips the limit after 10 requests from the test client's single IP."""
    limiter.reset()
    yield

# ── fake DB helpers ──────────────────────────────────────────────────────────


class _FakeChain:
    """Chainable Supabase-style mock returning configurable data on execute()."""

    def __init__(self, data=None, count=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._count = count
        self._raise = raise_on_execute

    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def neq(self, *_):
        return self

    def gt(self, *_):
        return self

    def gte(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        result.count = self._count if self._count is not None else len(self._data)
        return result


def _make_db(
    *,
    active_tenants=None,
    paused_tenants=None,
    cancellations_count=0,
    cancel_raise=False,
    dunning_raise=False,
):
    """Build a MagicMock DB routing table() calls to fake chains.

    Call order inside get_mrr_metrics:
      1. tenants  — active paying (plan_status=active, plan!=free)
      2. tenants  — dunning paused (plan_status=paused, dunning_attempt_count>0)
      3. tenant_cancellation_events — last 30 days count
    """
    active = active_tenants if active_tenants is not None else []
    paused = paused_tenants if paused_tenants is not None else []

    call_count = [0]

    def _table_router(name: str):
        call_count[0] += 1

        if name == "tenants":
            if call_count[0] == 1:
                # First call: active paying tenants
                return _FakeChain(data=active)
            # Second call: dunning paused
            if dunning_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=paused)

        if name == "tenant_cancellation_events":
            if cancel_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=[], count=cancellations_count)

        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _table_router
    return db


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def admin_headers():
    return {"x-api-secret": _ADMIN_SECRET}


@pytest.fixture(autouse=True)
def _patch_admin_secret(monkeypatch):
    """Make _admin_secret() return our test value for all tests in this module."""
    monkeypatch.setattr(
        "backend.routers.admin_analytics._admin_secret",
        lambda: _ADMIN_SECRET,
    )


# ── auth tests ───────────────────────────────────────────────────────────────


class TestMrrMetricsAuth:
    def test_no_secret_returns_401(self, client):
        resp = client.get("/api/v1/admin/mrr-metrics")
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        resp = client.get(
            "/api/v1/admin/mrr-metrics",
            headers={"x-api-secret": "wrong-secret"},
        )
        assert resp.status_code == 401

    def test_valid_secret_reaches_handler(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        # 401/404 would mean auth/routing broke — any other status means handler ran
        assert resp.status_code not in (401, 404)


# ── MRR math ─────────────────────────────────────────────────────────────────


class TestMrrCalculation:
    def test_single_growth_tenant(self, client, mock_supabase, admin_headers):
        db = _make_db(
            active_tenants=[{"id": "t1", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0}],
            cancellations_count=0,
        )
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mrr_cents"] == PLAN_PRICE_CENTS["growth"]  # 9900
        assert data["mrr_dollars"] == 99.0
        assert data["active_paying_count"] == 1

    def test_mixed_plan_mrr(self, client, mock_supabase, admin_headers):
        """Two growth + one professional + one enterprise = correct sum."""
        active = [
            {"id": "t1", "plan": "growth",       "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t2", "plan": "growth",       "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t3", "plan": "professional", "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t4", "plan": "enterprise",   "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        expected = (
            2 * PLAN_PRICE_CENTS["growth"]
            + PLAN_PRICE_CENTS["professional"]
            + PLAN_PRICE_CENTS["enterprise"]
        )
        db = _make_db(active_tenants=active, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mrr_cents"] == expected
        assert data["active_paying_count"] == 4

    def test_mrr_by_plan_breakdown(self, client, mock_supabase, admin_headers):
        active = [
            {"id": "t1", "plan": "autopilot", "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t2", "plan": "autopilot", "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t3", "plan": "professional", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        db = _make_db(active_tenants=active, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        breakdown = data["mrr_by_plan"]

        assert breakdown["autopilot"]["count"] == 2
        assert breakdown["autopilot"]["mrr_cents"] == 2 * PLAN_PRICE_CENTS["autopilot"]
        assert breakdown["professional"]["count"] == 1
        assert breakdown["professional"]["mrr_cents"] == PLAN_PRICE_CENTS["professional"]

    def test_zero_active_tenants_returns_zero_mrr(self, client, mock_supabase, admin_headers):
        db = _make_db(active_tenants=[], cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mrr_cents"] == 0
        assert data["active_paying_count"] == 0

    def test_unknown_plan_contributes_zero_mrr(self, client, mock_supabase, admin_headers):
        """A tenant with an unrecognised plan name should not crash and adds $0."""
        active = [
            {"id": "t1", "plan": "legacy_unknown", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        db = _make_db(active_tenants=active, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["mrr_cents"] == 0


# ── churn rate ────────────────────────────────────────────────────────────────


class TestChurnRate:
    def test_churn_rate_with_cancellations(self, client, mock_supabase, admin_headers):
        """churn = cancellations / (active + cancellations) × 100."""
        active = [
            {"id": "t1", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t2", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0},
            {"id": "t3", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        # 3 active + 1 cancellation → 1/4 = 25%
        db = _make_db(active_tenants=active, cancellations_count=1)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["cancellations_30d"] == 1
        assert data["churn_rate_30d_pct"] == 25.0

    def test_churn_rate_divide_by_zero_guard(self, client, mock_supabase, admin_headers):
        """Zero active + zero cancellations must not raise ZeroDivisionError."""
        db = _make_db(active_tenants=[], cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["churn_rate_30d_pct"] == 0.0
        assert data["cancellations_30d"] == 0

    def test_no_cancellations_zero_churn(self, client, mock_supabase, admin_headers):
        active = [
            {"id": "t1", "plan": "professional", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        db = _make_db(active_tenants=active, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["churn_rate_30d_pct"] == 0.0


# ── dunning ───────────────────────────────────────────────────────────────────


class TestDunningPaused:
    def test_dunning_paused_count(self, client, mock_supabase, admin_headers):
        paused = [
            {"id": "p1", "billing_dunning_attempt_count": 2},
            {"id": "p2", "billing_dunning_attempt_count": 1},
        ]
        db = _make_db(active_tenants=[], paused_tenants=paused, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["dunning_paused_count"] == 2


# ── fault tolerance ───────────────────────────────────────────────────────────


class TestFaultTolerance:
    def test_cancel_table_error_returns_200_with_null_churn(
        self, client, mock_supabase, admin_headers
    ):
        """If tenant_cancellation_events is unavailable, endpoint still returns 200."""
        active = [
            {"id": "t1", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        db = _make_db(active_tenants=active, cancel_raise=True)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # MRR still computes correctly
        assert data["mrr_cents"] == PLAN_PRICE_CENTS["growth"]
        # Churn fields are null because the table query failed
        assert data["cancellations_30d"] is None
        assert data["churn_rate_30d_pct"] is None

    def test_dunning_query_error_returns_200_with_null_dunning(
        self, client, mock_supabase, admin_headers
    ):
        """If dunning query fails, dunning_paused_count is None but 200 is returned."""
        active = [
            {"id": "t1", "plan": "growth", "plan_status": "active", "billing_dunning_attempt_count": 0},
        ]
        db = _make_db(active_tenants=active, dunning_raise=True, cancellations_count=0)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/mrr-metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mrr_cents"] == PLAN_PRICE_CENTS["growth"]
        assert data["dunning_paused_count"] is None
