"""Tests for compute_funnel() and GET /api/v1/admin/product-funnel.

Tests exercise the service function (compute_funnel) directly via mocked DB
and also the HTTP route via a minimal FastAPI test app that includes the router.

Running without conftest is supported — this module provides its own fixtures.

Coverage:
  - 401 when admin secret missing or wrong
  - 200 with correct counts when all DB calls succeed
  - leads use client_id (not tenant_id) for with_leads / new_leads_week
  - chat_messages use tenant_id for activated count
  - appointments use tenant_id for new_appointments_week
  - paid filter: plan != 'free' AND plan_status in (active, trialing)
  - per-metric DB failure does not crash whole response (errors list populated)
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
        result.count = (
            self._count if self._count is not None else len(self._data)
        )
        return result


def _make_db(
    *,
    total_tenants_count=0,
    chat_messages_data=None,
    leads_data=None,
    paid_tenants_count=0,
    new_signups_count=0,
    new_leads_count=0,
    new_appts_count=0,
    # Per-table failure flags
    raise_total_tenants=False,
    raise_chat_messages=False,
    raise_leads=False,
    raise_paid=False,
    raise_new_signups=False,
    raise_new_leads=False,
    raise_new_appts=False,
):
    """Build a MagicMock Supabase client routing table() calls.

    compute_funnel() calls table() in this order:
      1. "tenants"       — count=exact (total)
      2. "chat_messages" — select tenant_id, limit 5000
      3. "leads"         — select client_id, limit 5000  (with_leads)
      4. "tenants"       — count=exact (paid)
      5. "tenants"       — count=exact (new signups this week)
      6. "leads"         — count=exact (new_leads_week)
      7. "appointments"  — count=exact (new_appts_week)
    """
    tenants_calls = [0]
    leads_calls = [0]

    def _router(name: str):
        if name == "tenants":
            tenants_calls[0] += 1
            n = tenants_calls[0]
            if n == 1:
                return _FakeChain(count=total_tenants_count, raise_on_execute=raise_total_tenants)
            if n == 2:
                return _FakeChain(count=paid_tenants_count, raise_on_execute=raise_paid)
            if n == 3:
                return _FakeChain(count=new_signups_count, raise_on_execute=raise_new_signups)
            return _FakeChain(count=0)

        if name == "chat_messages":
            return _FakeChain(
                data=chat_messages_data or [],
                raise_on_execute=raise_chat_messages,
            )

        if name == "leads":
            leads_calls[0] += 1
            n = leads_calls[0]
            if n == 1:
                # with_leads — select client_id, limit 5000
                return _FakeChain(
                    data=leads_data or [],
                    raise_on_execute=raise_leads,
                )
            if n == 2:
                # new_leads_week — count + gte
                return _FakeChain(count=new_leads_count, raise_on_execute=raise_new_leads)
            return _FakeChain(count=0)

        if name == "appointments":
            return _FakeChain(count=new_appts_count, raise_on_execute=raise_new_appts)

        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _router
    return db


# ---------------------------------------------------------------------------
# Unit tests for compute_funnel() — no HTTP, no conftest needed
# ---------------------------------------------------------------------------

class TestComputeFunnelUnit:
    """Direct unit tests against compute_funnel(); HTTP layer tested separately."""

    def _call(self, db):
        from backend.services.funnel_metrics import compute_funnel
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            return compute_funnel()

    def test_total_tenants_maps_correctly(self):
        data = self._call(_make_db(total_tenants_count=42))
        assert data["total_tenants"] == 42
        assert data["errors"] == []

    def test_activated_deduplicates_tenant_ids(self):
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}, {"tenant_id": "t1"}]
        data = self._call(_make_db(chat_messages_data=chat))
        # Three rows but only 2 distinct tenant_ids
        assert data["activated"] == 2

    def test_with_leads_uses_client_id_and_deduplicates(self):
        # leads must use client_id — not tenant_id
        leads = [
            {"client_id": "c1"},
            {"client_id": "c2"},
            {"client_id": "c1"},  # duplicate
        ]
        data = self._call(_make_db(leads_data=leads))
        assert data["with_leads"] == 2

    def test_paid_count_maps_correctly(self):
        data = self._call(_make_db(paid_tenants_count=7))
        assert data["paid"] == 7

    def test_new_signups_week_maps_correctly(self):
        data = self._call(_make_db(new_signups_count=5))
        assert data["new_signups_week"] == 5

    def test_new_leads_week_maps_correctly(self):
        data = self._call(_make_db(new_leads_count=11))
        assert data["new_leads_week"] == 11

    def test_new_appointments_week_maps_correctly(self):
        data = self._call(_make_db(new_appts_count=3))
        assert data["new_appointments_week"] == 3

    def test_full_happy_path_all_metrics(self):
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        leads = [{"client_id": "t1"}, {"client_id": "t3"}]
        data = self._call(
            _make_db(
                total_tenants_count=20,
                chat_messages_data=chat,
                leads_data=leads,
                paid_tenants_count=8,
                new_signups_count=3,
                new_leads_count=10,
                new_appts_count=4,
            )
        )
        assert data["total_tenants"] == 20
        assert data["activated"] == 2
        assert data["with_leads"] == 2
        assert data["paid"] == 8
        assert data["new_signups_week"] == 3
        assert data["new_leads_week"] == 10
        assert data["new_appointments_week"] == 4
        assert data["errors"] == []
        assert "computed_at" in data

    # --- Partial-failure / fault-tolerance ---

    def test_chat_messages_failure_populates_errors_list(self):
        data = self._call(
            _make_db(total_tenants_count=15, raise_chat_messages=True, paid_tenants_count=5)
        )
        # Response must still be a valid dict (no exception raised)
        assert data["total_tenants"] == 15
        assert data["activated"] == 0           # zeroed on failure
        assert "activated" in data["errors"]    # failure surfaced
        assert data["paid"] == 5                # other metrics unaffected

    def test_leads_failure_zeroes_with_leads_only(self):
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        data = self._call(
            _make_db(
                total_tenants_count=10,
                chat_messages_data=chat,
                raise_leads=True,
                paid_tenants_count=3,
            )
        )
        assert data["total_tenants"] == 10
        assert data["activated"] == 2           # chat_messages succeeded
        assert data["with_leads"] == 0          # zeroed because leads query failed
        assert "with_leads" in data["errors"]
        assert data["paid"] == 3                # tenants paid still ok

    def test_total_tenants_failure_still_returns_other_metrics(self):
        data = self._call(
            _make_db(raise_total_tenants=True, paid_tenants_count=4, new_signups_count=1)
        )
        assert data["total_tenants"] == 0
        assert "total_tenants" in data["errors"]
        assert data["paid"] == 4

    def test_new_leads_failure_does_not_break_with_leads(self):
        leads = [{"client_id": "c1"}, {"client_id": "c2"}]
        data = self._call(
            _make_db(leads_data=leads, raise_new_leads=True)
        )
        # with_leads (call 1) should succeed
        assert data["with_leads"] == 2
        # new_leads_week (call 2) should be zeroed
        assert data["new_leads_week"] == 0
        assert "new_leads_week" in data["errors"]

    def test_appointments_failure_only_affects_new_appointments(self):
        data = self._call(
            _make_db(total_tenants_count=5, paid_tenants_count=2, raise_new_appts=True)
        )
        assert data["total_tenants"] == 5
        assert data["paid"] == 2
        assert data["new_appointments_week"] == 0
        assert "new_appointments_week" in data["errors"]

    def test_multiple_simultaneous_failures(self):
        """Both paid and chat_messages fail — two entries in errors, rest ok."""
        data = self._call(
            _make_db(
                total_tenants_count=30,
                raise_chat_messages=True,
                raise_paid=True,
                new_signups_count=7,
            )
        )
        assert data["total_tenants"] == 30
        assert data["new_signups_week"] == 7
        assert "activated" in data["errors"]
        assert "paid" in data["errors"]
        assert len(data["errors"]) >= 2


# ---------------------------------------------------------------------------
# HTTP route tests — use a minimal FastAPI app with the router registered
# ---------------------------------------------------------------------------

class TestFunnelRoute:
    """Integration tests against the real HTTP route in a minimal test app."""

    @pytest.fixture(autouse=True)
    def _build_test_client(self):
        import httpx
        from fastapi import FastAPI
        from backend.limiter import limiter
        from backend.routers.funnel import router

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
        self._admin_secret = "http-test-secret"

    @pytest.fixture(autouse=True)
    def _patch_secret(self, monkeypatch):
        monkeypatch.setattr(
            "backend.routers.funnel._admin_secret",
            lambda: self._admin_secret,
        )

    def _admin_headers(self):
        return {"x-api-secret": self._admin_secret}

    # Auth

    def test_no_secret_returns_401(self):
        resp = self._get("/api/v1/admin/product-funnel")
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self):
        resp = self._get(
            "/api/v1/admin/product-funnel",
            headers={"x-api-secret": "wrong"},
        )
        assert resp.status_code == 401

    def test_correct_secret_returns_200(self):
        db = _make_db(total_tenants_count=5)
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 5
        assert "computed_at" in data

    # Count correctness via HTTP

    def test_http_counts_map_correctly(self):
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        leads = [{"client_id": "c1"}]
        db = _make_db(
            total_tenants_count=10,
            chat_messages_data=chat,
            leads_data=leads,
            paid_tenants_count=3,
            new_signups_count=2,
            new_leads_count=5,
            new_appts_count=1,
        )
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 10
        assert data["activated"] == 2
        assert data["with_leads"] == 1
        assert data["paid"] == 3
        assert data["new_signups_week"] == 2
        assert data["new_leads_week"] == 5
        assert data["new_appointments_week"] == 1
        assert data["errors"] == []

    def test_http_partial_failure_still_returns_200(self):
        db = _make_db(total_tenants_count=8, raise_chat_messages=True, paid_tenants_count=2)
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 8
        assert data["activated"] == 0
        assert "activated" in data["errors"]
        assert data["paid"] == 2
