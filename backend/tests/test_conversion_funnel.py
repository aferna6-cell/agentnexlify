"""Tests for GET /api/v1/admin/conversion-funnel.

Covers:
  - funnel math for signups / trialing / active_paid / past_due_or_paused / cancelled
  - trial_to_paid_rate calculation: active_paid / (active_paid + trialing)
  - divide-by-zero guard: 0 active_paid + 0 trialing => 0.0
  - days query param: clamped to ge=1, le=365 (422 outside range)
  - 401 when admin secret is missing or wrong
  - 200 with correct shape when data is present
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.limiter import limiter

_ADMIN_SECRET = "test-admin-secret-funnel"

_ENDPOINT = "/api/v1/admin/conversion-funnel"


# ── rate-limiter reset ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


# ── fake DB helpers ───────────────────────────────────────────────────────────


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

    def gte(self, *_):
        return self

    def lte(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        result.count = self._count if self._count is not None else len(self._data)
        return result


def _make_db(*, signups_count=0, all_tenants=None):
    """Build a MagicMock DB routing table() calls to fake chains.

    Call order inside get_conversion_funnel:
      1. tenants  — signups in window (count query with gte created_at)
      2. tenants  — all tenants for funnel bucketing (plan_status + stripe_customer_id)
    """
    tenants = all_tenants if all_tenants is not None else []
    call_count = [0]

    def _table_router(name: str):
        call_count[0] += 1
        if name == "tenants":
            if call_count[0] == 1:
                # First call: signups count
                return _FakeChain(data=[], count=signups_count)
            # Second call: all tenants for funnel
            return _FakeChain(data=tenants)
        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _table_router
    return db


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def admin_headers():
    return {"x-api-secret": _ADMIN_SECRET}


@pytest.fixture(autouse=True)
def _patch_admin_secret(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.admin_analytics._admin_secret",
        lambda: _ADMIN_SECRET,
    )


# ── auth tests ────────────────────────────────────────────────────────────────


class TestConversionFunnelAuth:
    def test_no_secret_returns_401(self, client):
        resp = client.get(_ENDPOINT)
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        resp = client.get(_ENDPOINT, headers={"x-api-secret": "bad-secret"})
        assert resp.status_code == 401

    def test_valid_secret_reaches_handler(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code not in (401, 404)


# ── funnel math ───────────────────────────────────────────────────────────────


class TestFunnelMath:
    def test_all_zero_when_no_tenants(self, client, mock_supabase, admin_headers):
        db = _make_db(signups_count=0, all_tenants=[])
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["signups"] == 0
        assert data["trialing"] == 0
        assert data["active_paid"] == 0
        assert data["past_due_or_paused"] == 0
        assert data["cancelled"] == 0

    def test_trialing_count(self, client, mock_supabase, admin_headers):
        tenants = [
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=2, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["trialing"] == 2
        assert data["active_paid"] == 0

    def test_active_paid_requires_stripe_customer_id(
        self, client, mock_supabase, admin_headers
    ):
        """active + stripe_customer_id => active_paid; active without stripe => not counted."""
        tenants = [
            {"plan_status": "active", "stripe_customer_id": "cus_abc"},
            {"plan_status": "active", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=2, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["active_paid"] == 1

    def test_past_due_or_paused_both_statuses(
        self, client, mock_supabase, admin_headers
    ):
        tenants = [
            {"plan_status": "past_due", "stripe_customer_id": "cus_1"},
            {"plan_status": "paused", "stripe_customer_id": "cus_2"},
        ]
        db = _make_db(signups_count=0, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["past_due_or_paused"] == 2

    def test_cancelled_accepts_both_spellings(
        self, client, mock_supabase, admin_headers
    ):
        """Both 'cancelled' and 'canceled' (US/UK spelling) map to the cancelled bucket."""
        tenants = [
            {"plan_status": "cancelled", "stripe_customer_id": None},
            {"plan_status": "canceled", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=0, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["cancelled"] == 2

    def test_mixed_funnel_counts(self, client, mock_supabase, admin_headers):
        tenants = [
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "active", "stripe_customer_id": "cus_1"},
            {"plan_status": "active", "stripe_customer_id": "cus_2"},
            {"plan_status": "past_due", "stripe_customer_id": "cus_3"},
            {"plan_status": "cancelled", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=5, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["signups"] == 5
        assert data["trialing"] == 3
        assert data["active_paid"] == 2
        assert data["past_due_or_paused"] == 1
        assert data["cancelled"] == 1


# ── trial_to_paid_rate ────────────────────────────────────────────────────────


class TestTrialToPaidRate:
    def test_rate_is_zero_when_no_trialing_and_no_paid(
        self, client, mock_supabase, admin_headers
    ):
        """Divide-by-zero guard: denominator = 0 => rate = 0.0."""
        db = _make_db(signups_count=0, all_tenants=[])
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["trial_to_paid_rate"] == 0.0

    def test_rate_is_zero_when_all_trialing_none_paid(
        self, client, mock_supabase, admin_headers
    ):
        tenants = [
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=2, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["trial_to_paid_rate"] == 0.0

    def test_rate_is_one_when_all_paid_none_trialing(
        self, client, mock_supabase, admin_headers
    ):
        tenants = [
            {"plan_status": "active", "stripe_customer_id": "cus_1"},
            {"plan_status": "active", "stripe_customer_id": "cus_2"},
        ]
        db = _make_db(signups_count=2, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["trial_to_paid_rate"] == 1.0

    def test_rate_calculation_two_paid_two_trialing(
        self, client, mock_supabase, admin_headers
    ):
        """2 paid / (2 paid + 2 trialing) = 0.5."""
        tenants = [
            {"plan_status": "active", "stripe_customer_id": "cus_1"},
            {"plan_status": "active", "stripe_customer_id": "cus_2"},
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=4, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["trial_to_paid_rate"] == 0.5

    def test_rate_calculation_one_paid_three_trialing(
        self, client, mock_supabase, admin_headers
    ):
        """1 paid / (1 paid + 3 trialing) = 0.25."""
        tenants = [
            {"plan_status": "active", "stripe_customer_id": "cus_1"},
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
            {"plan_status": "trialing", "stripe_customer_id": None},
        ]
        db = _make_db(signups_count=4, all_tenants=tenants)
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["trial_to_paid_rate"] == 0.25


# ── query param validation ────────────────────────────────────────────────────


class TestDaysParam:
    def test_default_days_is_30(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["window_days"] == 30

    def test_custom_days_is_reflected(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get(f"{_ENDPOINT}?days=90", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["window_days"] == 90

    def test_days_below_minimum_returns_422(self, client, admin_headers):
        resp = client.get(f"{_ENDPOINT}?days=0", headers=admin_headers)
        assert resp.status_code == 422

    def test_days_above_maximum_returns_422(self, client, admin_headers):
        resp = client.get(f"{_ENDPOINT}?days=366", headers=admin_headers)
        assert resp.status_code == 422

    def test_days_at_boundary_365_is_valid(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get(f"{_ENDPOINT}?days=365", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["window_days"] == 365

    def test_days_at_boundary_1_is_valid(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect
        resp = client.get(f"{_ENDPOINT}?days=1", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["window_days"] == 1


# ── response shape ────────────────────────────────────────────────────────────


class TestResponseShape:
    def test_all_expected_keys_present(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        expected_keys = {
            "window_days",
            "signups",
            "trialing",
            "active_paid",
            "past_due_or_paused",
            "cancelled",
            "trial_to_paid_rate",
        }
        assert expected_keys.issubset(data.keys())

    def test_trial_to_paid_rate_is_float(self, client, mock_supabase, admin_headers):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["trial_to_paid_rate"], float)

    def test_db_failure_returns_500(self, client, mock_supabase, admin_headers):
        """A query failure is caught and surfaced as 500 (not an opaque crash)."""
        mock_supabase.table.side_effect = lambda *_: _FakeChain(raise_on_execute=True)
        resp = client.get(_ENDPOINT, headers=admin_headers)
        assert resp.status_code == 500
        assert "funnel" in resp.json()["detail"].lower()
