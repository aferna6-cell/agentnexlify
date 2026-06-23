"""Tests for compute_referral_overview() and GET /api/v1/referral/admin/overview.

Tests exercise:
  - Service function compute_referral_overview() directly via mocked DB
  - HTTP route via a minimal FastAPI test app with the router registered

Coverage:
  - 401 when admin secret missing or wrong
  - 200 with correct secret
  - Ranking: sorted referred_signups desc, then total_clicks desc
  - Per-tenant click count correctness
  - Per-tenant referred_signups count correctness
  - Totals block accuracy
  - Tenants with no widget config get ref_code="" and zero counts
  - referral_clicks DB failure zeroes all total_clicks but does not crash
  - referred_signups DB failure zeroes all referred_signups but does not crash
  - Tenant fetch failure raises (500 from the route)

Running without conftest is supported — this module provides its own fixtures.

Schema conventions (verified against migrations 157 and 159):
  - referral_clicks.ref_tenant_id = widget api_key of the referrer tenant
  - tenants.referred_by_widget_key = api_key of whoever referred this tenant
  - widget_configs.api_key = a tenant's referral identity (ref_code)
  - widget_configs uses tenant_id (not client_id)
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Fake Supabase chain builder
# ---------------------------------------------------------------------------

class _FakeChain:
    """Chainable Supabase-style query mock."""

    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def neq(self, *_):
        return self

    def in_(self, *_):
        return self

    def gte(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        result.count = len(self._data)
        return result


def _make_db(
    *,
    tenant_rows=None,
    widget_config_rows=None,
    referral_click_rows=None,
    referred_signup_rows=None,   # rows in tenants with referred_by_widget_key set
    raise_tenants=False,
    raise_widget_configs=False,
    raise_referral_clicks=False,
    raise_referred_signups=False,
):
    """Build a MagicMock Supabase client routing table() calls.

    compute_referral_overview() calls table() in this order:
      1. "tenants"         — .select("id, business_name")
      2. "widget_configs"  — .select("tenant_id, api_key")
      3. "referral_clicks" — .select("ref_tenant_id")
      4. "tenants"         — .select("referred_by_widget_key")   [signups]

    NOTE: tenants is queried TWICE (steps 1 and 4).  We sequence these
    via a call counter so each gets independent data/raise flags.
    """
    tenants_call = [0]

    def _router(name: str):
        if name == "tenants":
            tenants_call[0] += 1
            n = tenants_call[0]
            if n == 1:
                return _FakeChain(
                    data=tenant_rows or [],
                    raise_on_execute=raise_tenants,
                )
            # Second call: referred_by_widget_key fetch
            return _FakeChain(
                data=referred_signup_rows or [],
                raise_on_execute=raise_referred_signups,
            )

        if name == "widget_configs":
            return _FakeChain(
                data=widget_config_rows or [],
                raise_on_execute=raise_widget_configs,
            )

        if name == "referral_clicks":
            return _FakeChain(
                data=referral_click_rows or [],
                raise_on_execute=raise_referral_clicks,
            )

        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _router
    return db


# ---------------------------------------------------------------------------
# Fixtures — sample data
# ---------------------------------------------------------------------------

# Tenant rows (id, business_name)
_T1 = {"id": "t1", "business_name": "Acme Plumbing"}
_T2 = {"id": "t2", "business_name": "Bright Dental"}
_T3 = {"id": "t3", "business_name": "Green Lawn Care"}

# Widget config rows (tenant_id, api_key)
_WC1 = {"tenant_id": "t1", "api_key": "anx_t1_key"}
_WC2 = {"tenant_id": "t2", "api_key": "anx_t2_key"}
_WC3 = {"tenant_id": "t3", "api_key": "anx_t3_key"}

# referral_clicks rows — ref_tenant_id is the referrer's api_key
_CLICK_T1 = {"ref_tenant_id": "anx_t1_key"}
_CLICK_T2 = {"ref_tenant_id": "anx_t2_key"}


# ---------------------------------------------------------------------------
# Unit tests for compute_referral_overview()
# ---------------------------------------------------------------------------

class TestComputeReferralOverviewUnit:
    """Direct unit tests; no HTTP layer involved."""

    def _call(self, db):
        from backend.services.referral_overview import compute_referral_overview
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            return compute_referral_overview()

    # --- Basic correctness ---

    def test_empty_db_returns_empty_list(self):
        data = self._call(_make_db())
        assert data["tenants"] == []
        assert data["totals"]["total_clicks"] == 0
        assert data["totals"]["total_referred_signups"] == 0
        assert "computed_at" in data

    def test_single_tenant_no_activity(self):
        db = _make_db(
            tenant_rows=[_T1],
            widget_config_rows=[_WC1],
        )
        data = self._call(db)
        assert len(data["tenants"]) == 1
        row = data["tenants"][0]
        assert row["tenant_id"] == "t1"
        assert row["business_name"] == "Acme Plumbing"
        assert row["ref_code"] == "anx_t1_key"
        assert row["total_clicks"] == 0
        assert row["referred_signups"] == 0

    def test_total_clicks_counted_per_tenant(self):
        # t1 gets 3 clicks, t2 gets 1 click
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referral_click_rows=[
                _CLICK_T1,
                _CLICK_T1,
                _CLICK_T1,
                _CLICK_T2,
            ],
        )
        data = self._call(db)
        rows_by_tid = {r["tenant_id"]: r for r in data["tenants"]}
        assert rows_by_tid["t1"]["total_clicks"] == 3
        assert rows_by_tid["t2"]["total_clicks"] == 1

    def test_referred_signups_counted_correctly(self):
        # 2 tenants signed up via t1's widget key; 0 via t2's
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t1_key"},
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referred_signup_rows=signup_rows,
        )
        data = self._call(db)
        rows_by_tid = {r["tenant_id"]: r for r in data["tenants"]}
        assert rows_by_tid["t1"]["referred_signups"] == 2
        assert rows_by_tid["t2"]["referred_signups"] == 0

    def test_totals_sum_correctly(self):
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referral_click_rows=[_CLICK_T1, _CLICK_T1, _CLICK_T2],
            referred_signup_rows=signup_rows,
        )
        data = self._call(db)
        assert data["totals"]["total_clicks"] == 3
        assert data["totals"]["total_referred_signups"] == 3

    # --- Ranking ---

    def test_ranking_referred_signups_desc(self):
        # t2: 3 signups, t1: 1 signup — t2 should be first
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referred_signup_rows=signup_rows,
        )
        data = self._call(db)
        assert data["tenants"][0]["tenant_id"] == "t2"
        assert data["tenants"][1]["tenant_id"] == "t1"

    def test_ranking_tiebreak_total_clicks_desc(self):
        # t1 and t2 both have 1 signup; t1 has 5 clicks, t2 has 2 — t1 first
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        click_rows = [
            _CLICK_T1, _CLICK_T1, _CLICK_T1, _CLICK_T1, _CLICK_T1,  # 5 for t1
            _CLICK_T2, _CLICK_T2,                                      # 2 for t2
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referral_click_rows=click_rows,
            referred_signup_rows=signup_rows,
        )
        data = self._call(db)
        assert data["tenants"][0]["tenant_id"] == "t1"
        assert data["tenants"][1]["tenant_id"] == "t2"

    def test_ranking_three_tenants_mixed(self):
        # t2: 3 signups + 5 clicks, t1: 1 signup + 10 clicks, t3: 0 signups
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        click_rows = (
            [{"ref_tenant_id": "anx_t1_key"}] * 10
            + [{"ref_tenant_id": "anx_t2_key"}] * 5
        )
        db = _make_db(
            tenant_rows=[_T1, _T2, _T3],
            widget_config_rows=[_WC1, _WC2, _WC3],
            referral_click_rows=click_rows,
            referred_signup_rows=signup_rows,
        )
        data = self._call(db)
        tenant_ids = [r["tenant_id"] for r in data["tenants"]]
        assert tenant_ids[0] == "t2"  # 3 signups
        assert tenant_ids[1] == "t1"  # 1 signup
        assert tenant_ids[2] == "t3"  # 0 signups

    # --- No widget config edge case ---

    def test_tenant_with_no_widget_config_gets_empty_ref_code(self):
        # t1 has widget config; t2 does not
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1],  # no WC2
        )
        data = self._call(db)
        rows_by_tid = {r["tenant_id"]: r for r in data["tenants"]}
        assert rows_by_tid["t2"]["ref_code"] == ""
        assert rows_by_tid["t2"]["total_clicks"] == 0
        assert rows_by_tid["t2"]["referred_signups"] == 0

    # --- Partial failures (non-fatal) ---

    def test_referral_clicks_failure_zeroes_clicks_does_not_crash(self):
        db = _make_db(
            tenant_rows=[_T1],
            widget_config_rows=[_WC1],
            raise_referral_clicks=True,
        )
        data = self._call(db)
        assert len(data["tenants"]) == 1
        assert data["tenants"][0]["total_clicks"] == 0
        assert data["totals"]["total_clicks"] == 0

    def test_referred_signups_failure_zeroes_signups_does_not_crash(self):
        db = _make_db(
            tenant_rows=[_T1],
            widget_config_rows=[_WC1],
            referral_click_rows=[_CLICK_T1, _CLICK_T1],
            raise_referred_signups=True,
        )
        data = self._call(db)
        assert len(data["tenants"]) == 1
        # clicks still counted; signups zeroed
        assert data["tenants"][0]["total_clicks"] == 2
        assert data["tenants"][0]["referred_signups"] == 0

    # --- Fatal failures (raise) ---

    def test_tenants_failure_raises(self):
        db = _make_db(raise_tenants=True)
        with pytest.raises(Exception):
            self._call(db)

    def test_widget_configs_failure_raises(self):
        db = _make_db(
            tenant_rows=[_T1],
            raise_widget_configs=True,
        )
        with pytest.raises(Exception):
            self._call(db)


# ---------------------------------------------------------------------------
# HTTP route tests — minimal FastAPI app
# ---------------------------------------------------------------------------

class TestReferralOverviewRoute:
    """Integration tests against the real HTTP route via a test FastAPI app."""

    @pytest.fixture(autouse=True)
    def _build_test_client(self):
        import httpx
        from fastapi import FastAPI
        from backend.limiter import limiter
        from backend.routers.referral import router

        _app = FastAPI()
        _app.include_router(router)

        # Wire slowapi into the test app
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        _app.state.limiter = limiter
        _app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        limiter.reset()

        transport = httpx.ASGITransport(app=_app, raise_app_exceptions=False)

        def _sync_get(url, **kwargs):
            async def _do():
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://testserver"
                ) as c:
                    return await c.get(url, **kwargs)
            return asyncio.run(_do())

        self._get = _sync_get
        self._admin_secret = "test-admin-secret-overview"
        self._url = "/api/v1/referral/admin/overview"

    @pytest.fixture(autouse=True)
    def _patch_secret(self, monkeypatch):
        monkeypatch.setattr(
            "backend.routers.referral._admin_secret",
            lambda: self._admin_secret,
        )

    def _admin_headers(self):
        return {"x-api-secret": self._admin_secret}

    # --- Auth ---

    def test_no_secret_returns_401(self):
        resp = self._get(self._url)
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self):
        resp = self._get(self._url, headers={"x-api-secret": "wrong-secret"})
        assert resp.status_code == 401

    def test_correct_secret_returns_200(self):
        db = _make_db(tenant_rows=[_T1], widget_config_rows=[_WC1])
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200

    # --- Response shape ---

    def test_response_has_correct_keys(self):
        db = _make_db()
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "tenants" in data
        assert "totals" in data
        assert "computed_at" in data
        assert "total_clicks" in data["totals"]
        assert "total_referred_signups" in data["totals"]

    def test_tenant_row_has_correct_fields(self):
        db = _make_db(tenant_rows=[_T1], widget_config_rows=[_WC1])
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        row = resp.json()["tenants"][0]
        assert set(row.keys()) == {
            "tenant_id", "business_name", "ref_code",
            "total_clicks", "referred_signups",
        }

    # --- Count correctness via HTTP ---

    def test_http_click_counts_correct(self):
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referral_click_rows=[_CLICK_T1, _CLICK_T1, _CLICK_T2],
        )
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        rows_by_tid = {r["tenant_id"]: r for r in data["tenants"]}
        assert rows_by_tid["t1"]["total_clicks"] == 2
        assert rows_by_tid["t2"]["total_clicks"] == 1
        assert data["totals"]["total_clicks"] == 3

    def test_http_referred_signups_correct(self):
        signup_rows = [
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t1_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referred_signup_rows=signup_rows,
        )
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        rows_by_tid = {r["tenant_id"]: r for r in data["tenants"]}
        assert rows_by_tid["t1"]["referred_signups"] == 2
        assert rows_by_tid["t2"]["referred_signups"] == 1
        assert data["totals"]["total_referred_signups"] == 3

    def test_http_ranking_respected(self):
        # t2: 2 signups, t1: 0 — t2 must be first in list
        signup_rows = [
            {"referred_by_widget_key": "anx_t2_key"},
            {"referred_by_widget_key": "anx_t2_key"},
        ]
        db = _make_db(
            tenant_rows=[_T1, _T2],
            widget_config_rows=[_WC1, _WC2],
            referred_signup_rows=signup_rows,
        )
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        tenant_ids = [r["tenant_id"] for r in resp.json()["tenants"]]
        assert tenant_ids[0] == "t2"

    # --- DB failure propagation ---

    def test_referral_clicks_failure_still_returns_200(self):
        db = _make_db(
            tenant_rows=[_T1],
            widget_config_rows=[_WC1],
            raise_referral_clicks=True,
        )
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenants"][0]["total_clicks"] == 0
        assert data["totals"]["total_clicks"] == 0

    def test_referred_signups_failure_still_returns_200(self):
        db = _make_db(
            tenant_rows=[_T1],
            widget_config_rows=[_WC1],
            referral_click_rows=[_CLICK_T1, _CLICK_T1, _CLICK_T1],
            raise_referred_signups=True,
        )
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenants"][0]["total_clicks"] == 3
        assert data["tenants"][0]["referred_signups"] == 0

    def test_tenant_fetch_failure_returns_500(self):
        db = _make_db(raise_tenants=True)
        with patch(
            "backend.services.referral_overview.get_service_supabase",
            return_value=db,
        ):
            resp = self._get(self._url, headers=self._admin_headers())
        assert resp.status_code == 500
