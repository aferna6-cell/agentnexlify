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
  - internal/test tenants (matching is_internal_tenant()) are excluded from
    every count: total, paid, new_signups, activated, with_leads, new_leads,
    new_appointments

Contract change note (2026-06-23):
  The previous _make_db helper assumed compute_funnel() called the tenants table
  three times with count="exact" (total / paid / new_signups).  The updated
  compute_funnel() fetches tenant ROWS once (Step 0) and derives total, paid,
  and new_signups counts in Python after filtering out is_internal_tenant() rows.
  This is a legitimate contract change — exclusion of internal tenants requires
  row-level data (business_name) which count="exact" does not return.
  The test helper has been updated to reflect the new call order:
    1. "tenants"       — .select("id, business_name, plan, plan_status, created_at")
    2. "chat_messages" — .select("tenant_id").limit(50000)
    3. "leads"         — .select("client_id").limit(50000)         [with_leads]
    4. "leads"         — .select("client_id, created_at").gte(...) [new_leads_week]
    5. "appointments"  — .select("tenant_id, created_at").gte(...) [new_appts_week]
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

# ---------------------------------------------------------------------------
# Helpers for building tenant row dicts
# ---------------------------------------------------------------------------

# A far-future timestamp so "this week" filters always include it.
_THIS_WEEK = "2099-01-06T00:00:00+00:00"
# A far-past timestamp so "this week" filters always exclude it.
_LAST_YEAR = "2020-01-01T00:00:00+00:00"


def _real_tenant(
    tid: str,
    *,
    plan: str = "agent_os",
    plan_status: str = "active",
    created_at: str = _THIS_WEEK,
    business_name: str = "Acme Plumbing",
) -> dict:
    """Return a realistic real-customer tenant row dict."""
    return {
        "id": tid,
        "business_name": business_name,
        "plan": plan,
        "plan_status": plan_status,
        "created_at": created_at,
    }


def _internal_tenant(tid: str = "int-1") -> dict:
    """Return a row that is_internal_tenant() should flag as internal."""
    return {
        "id": tid,
        "business_name": "AgentNexLiFy Smoke Test",
        "plan": "agent_os",
        "plan_status": "active",
        "created_at": _THIS_WEEK,
    }


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
    # NEW: tenant rows (list of dicts — replaces three count-only params).
    # Rows must have: id, business_name, plan, plan_status, created_at.
    tenant_rows=None,
    # Secondary table data
    chat_messages_data=None,
    leads_data=None,
    new_leads_data=None,      # rows for new_leads_week (client_id + created_at)
    new_appts_data=None,      # rows for new_appointments_week (tenant_id + created_at)
    # Per-table failure flags
    raise_tenants=False,
    raise_chat_messages=False,
    raise_leads=False,
    raise_new_leads=False,
    raise_new_appts=False,
):
    """Build a MagicMock Supabase client routing table() calls.

    compute_funnel() calls table() in this order (new contract):
      1. "tenants"       — .select("id, business_name, plan, plan_status, created_at")
      2. "chat_messages" — .select("tenant_id").limit(50000)
      3. "leads"         — .select("client_id").limit(50000)          [with_leads]
      4. "leads"         — .select("client_id, created_at").gte(...)  [new_leads_week]
      5. "appointments"  — .select("tenant_id, created_at").gte(...)  [new_appts_week]

    Previously, tenants was called THREE times with count="exact".  Now it is
    called ONCE and returns full rows so is_internal_tenant() can filter them.
    This is a legitimate contract change — the old count approach could not
    support per-row name-based filtering.
    """
    if tenant_rows is None:
        tenant_rows = []

    leads_calls = [0]

    def _router(name: str):
        if name == "tenants":
            return _FakeChain(data=tenant_rows, raise_on_execute=raise_tenants)

        if name == "chat_messages":
            return _FakeChain(
                data=chat_messages_data or [],
                raise_on_execute=raise_chat_messages,
            )

        if name == "leads":
            leads_calls[0] += 1
            n = leads_calls[0]
            if n == 1:
                # with_leads — select client_id, limit 50000
                return _FakeChain(
                    data=leads_data or [],
                    raise_on_execute=raise_leads,
                )
            if n == 2:
                # new_leads_week — select client_id, created_at + gte filter
                return _FakeChain(
                    data=new_leads_data or [],
                    raise_on_execute=raise_new_leads,
                )
            return _FakeChain(data=[])

        if name == "appointments":
            return _FakeChain(
                data=new_appts_data or [],
                raise_on_execute=raise_new_appts,
            )

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
        rows = [_real_tenant("t1"), _real_tenant("t2"), _real_tenant("t3")]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["total_tenants"] == 3
        assert data["errors"] == []

    def test_activated_deduplicates_tenant_ids(self):
        rows = [_real_tenant("t1"), _real_tenant("t2")]
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}, {"tenant_id": "t1"}]
        data = self._call(_make_db(tenant_rows=rows, chat_messages_data=chat))
        # Three rows but only 2 distinct tenant_ids that are real tenants
        assert data["activated"] == 2

    def test_with_leads_uses_client_id_and_deduplicates(self):
        # leads must use client_id — not tenant_id
        rows = [_real_tenant("c1"), _real_tenant("c2")]
        leads = [
            {"client_id": "c1"},
            {"client_id": "c2"},
            {"client_id": "c1"},  # duplicate
        ]
        data = self._call(_make_db(tenant_rows=rows, leads_data=leads))
        assert data["with_leads"] == 2

    def test_paid_count_computed_from_rows(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active"),
            _real_tenant("t2", plan="chatbot", plan_status="trialing"),
            _real_tenant("t3", plan="free", plan_status="active"),       # not paid
            _real_tenant("t4", plan="agent_os", plan_status="canceled"), # not active
        ]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["paid"] == 2

    def test_new_signups_week_computed_from_rows(self):
        rows = [
            _real_tenant("t1", created_at=_THIS_WEEK),
            _real_tenant("t2", created_at=_THIS_WEEK),
            _real_tenant("t3", created_at=_LAST_YEAR),  # old — not this week
        ]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["new_signups_week"] == 2

    def test_new_leads_week_maps_correctly(self):
        rows = [_real_tenant("t1")]
        new_leads = [
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "t1", "created_at": _THIS_WEEK},
        ]
        data = self._call(_make_db(tenant_rows=rows, new_leads_data=new_leads))
        assert data["new_leads_week"] == 2

    def test_new_appointments_week_maps_correctly(self):
        rows = [_real_tenant("t1")]
        new_appts = [
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
        ]
        data = self._call(_make_db(tenant_rows=rows, new_appts_data=new_appts))
        assert data["new_appointments_week"] == 3

    def test_full_happy_path_all_metrics(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active", created_at=_THIS_WEEK),
            _real_tenant("t2", plan="chatbot", plan_status="active", created_at=_THIS_WEEK),
            _real_tenant("t3", plan="free", plan_status="active", created_at=_LAST_YEAR),
        ]
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        leads = [{"client_id": "t1"}, {"client_id": "t3"}]
        new_leads = [{"client_id": "t1", "created_at": _THIS_WEEK}]
        new_appts = [
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "t2", "created_at": _THIS_WEEK},
            {"tenant_id": "t2", "created_at": _THIS_WEEK},
            {"tenant_id": "t2", "created_at": _THIS_WEEK},
        ]
        data = self._call(
            _make_db(
                tenant_rows=rows,
                chat_messages_data=chat,
                leads_data=leads,
                new_leads_data=new_leads,
                new_appts_data=new_appts,
            )
        )
        assert data["total_tenants"] == 3
        assert data["activated"] == 2
        assert data["with_leads"] == 2
        assert data["paid"] == 2
        assert data["new_signups_week"] == 2
        assert data["new_leads_week"] == 1
        assert data["new_appointments_week"] == 4
        assert data["errors"] == []
        assert "computed_at" in data

    # --- Partial-failure / fault-tolerance ---

    def test_chat_messages_failure_populates_errors_list(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active"),
            _real_tenant("t2", plan="agent_os", plan_status="active"),
        ]
        data = self._call(
            _make_db(tenant_rows=rows, raise_chat_messages=True)
        )
        # total_tenants and paid still computed from the tenant rows
        assert data["total_tenants"] == 2
        assert data["paid"] == 2
        assert data["activated"] == 0           # zeroed on failure
        assert "activated" in data["errors"]    # failure surfaced

    def test_leads_failure_zeroes_with_leads_only(self):
        rows = [_real_tenant("t1"), _real_tenant("t2")]
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        data = self._call(
            _make_db(
                tenant_rows=rows,
                chat_messages_data=chat,
                raise_leads=True,
            )
        )
        assert data["total_tenants"] == 2
        assert data["activated"] == 2           # chat_messages succeeded
        assert data["with_leads"] == 0          # zeroed because leads query failed
        assert "with_leads" in data["errors"]

    def test_total_tenants_failure_still_returns_other_metrics(self):
        """When tenants table fails, total/paid/new_signups all error.
        Other metrics still attempt to run (return 0 since real_tenant_ids empty)."""
        data = self._call(_make_db(raise_tenants=True))
        assert data["total_tenants"] == 0
        assert "total_tenants" in data["errors"]
        assert "paid" in data["errors"]
        assert "new_signups_week" in data["errors"]

    def test_new_leads_failure_does_not_break_with_leads(self):
        rows = [_real_tenant("c1"), _real_tenant("c2")]
        leads = [{"client_id": "c1"}, {"client_id": "c2"}]
        data = self._call(
            _make_db(tenant_rows=rows, leads_data=leads, raise_new_leads=True)
        )
        # with_leads (call 1) should succeed
        assert data["with_leads"] == 2
        # new_leads_week (call 2) should be zeroed
        assert data["new_leads_week"] == 0
        assert "new_leads_week" in data["errors"]

    def test_appointments_failure_only_affects_new_appointments(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active"),
            _real_tenant("t2", plan="chatbot", plan_status="active"),
        ]
        data = self._call(
            _make_db(tenant_rows=rows, raise_new_appts=True)
        )
        assert data["total_tenants"] == 2
        assert data["paid"] == 2
        assert data["new_appointments_week"] == 0
        assert "new_appointments_week" in data["errors"]

    def test_multiple_simultaneous_failures(self):
        """chat_messages fails AND new_leads fails — two entries in errors, rest ok."""
        rows = [
            _real_tenant("t1", created_at=_THIS_WEEK),
            _real_tenant("t2", created_at=_THIS_WEEK),
        ]
        data = self._call(
            _make_db(
                tenant_rows=rows,
                raise_chat_messages=True,
                raise_new_leads=True,
            )
        )
        assert data["total_tenants"] == 2
        assert data["new_signups_week"] == 2
        assert "activated" in data["errors"]
        assert "new_leads_week" in data["errors"]
        assert len(data["errors"]) >= 2

    # --- Internal-tenant exclusion tests ---

    def test_internal_tenant_excluded_from_total(self):
        rows = [
            _real_tenant("t1"),
            _real_tenant("t2"),
            _internal_tenant("int-1"),
        ]
        data = self._call(_make_db(tenant_rows=rows))
        # 3 rows but 1 is internal — only 2 real
        assert data["total_tenants"] == 2

    def test_internal_tenant_excluded_from_paid(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active"),
            _internal_tenant("int-1"),  # plan=agent_os active but internal
        ]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["paid"] == 1  # only the real tenant counts

    def test_internal_tenant_excluded_from_new_signups(self):
        rows = [
            _real_tenant("t1", created_at=_THIS_WEEK),
            _internal_tenant("int-1"),  # created this week but internal
        ]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["new_signups_week"] == 1

    def test_internal_tenant_chat_messages_excluded_from_activated(self):
        rows = [_real_tenant("t1")]
        # int-1 has messages but is not in real_tenant_ids
        chat = [
            {"tenant_id": "t1"},
            {"tenant_id": "int-1"},
            {"tenant_id": "int-1"},
        ]
        data = self._call(_make_db(tenant_rows=rows, chat_messages_data=chat))
        # t1 is real and has a message; int-1 filtered by real_tenant_ids check
        assert data["activated"] == 1

    def test_internal_tenant_leads_excluded_from_with_leads(self):
        rows = [_real_tenant("t1")]
        leads = [
            {"client_id": "t1"},
            {"client_id": "int-1"},  # internal tenant not in real_tenant_ids
        ]
        data = self._call(_make_db(tenant_rows=rows, leads_data=leads))
        assert data["with_leads"] == 1

    def test_internal_tenant_new_leads_excluded(self):
        rows = [_real_tenant("t1")]
        new_leads = [
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "int-1", "created_at": _THIS_WEEK},  # internal
        ]
        data = self._call(_make_db(tenant_rows=rows, new_leads_data=new_leads))
        assert data["new_leads_week"] == 1

    def test_internal_tenant_new_appointments_excluded(self):
        rows = [_real_tenant("t1")]
        new_appts = [
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "int-1", "created_at": _THIS_WEEK},  # internal
        ]
        data = self._call(_make_db(tenant_rows=rows, new_appts_data=new_appts))
        assert data["new_appointments_week"] == 1

    def test_all_internal_tenants_returns_all_zeros(self):
        rows = [_internal_tenant("int-1"), _internal_tenant("int-2")]
        chat = [{"tenant_id": "int-1"}, {"tenant_id": "int-2"}]
        leads = [{"client_id": "int-1"}]
        new_leads = [{"client_id": "int-1", "created_at": _THIS_WEEK}]
        new_appts = [{"tenant_id": "int-1", "created_at": _THIS_WEEK}]
        data = self._call(
            _make_db(
                tenant_rows=rows,
                chat_messages_data=chat,
                leads_data=leads,
                new_leads_data=new_leads,
                new_appts_data=new_appts,
            )
        )
        assert data["total_tenants"] == 0
        assert data["paid"] == 0
        assert data["new_signups_week"] == 0
        assert data["activated"] == 0
        assert data["with_leads"] == 0
        assert data["new_leads_week"] == 0
        assert data["new_appointments_week"] == 0
        assert data["errors"] == []

    def test_smoke_test_tenant_name_matches_denylist(self):
        """'AgentNexLiFy Smoke Test' is the exact tenant causing inflation."""
        from backend.services.internal_tenants import is_internal_tenant
        row = {
            "id": "abc",
            "business_name": "AgentNexLiFy Smoke Test",
            "plan": "agent_os",
            "plan_status": "active",
            "created_at": _THIS_WEEK,
        }
        assert is_internal_tenant(row) is True

    def test_case_insensitive_match(self):
        """Matching is case-insensitive."""
        from backend.services.internal_tenants import is_internal_tenant
        assert is_internal_tenant({"business_name": "AGENTNEXLIFY DEMO"}) is True
        assert is_internal_tenant({"business_name": "agentnexlify"}) is True

    def test_real_customer_not_excluded(self):
        """A real customer name does not match the denylist."""
        from backend.services.internal_tenants import is_internal_tenant
        # "nexlify" alone is NOT in the denylist — only "agentnexlify" is
        assert is_internal_tenant({"business_name": "NexLify Tools"}) is False
        assert is_internal_tenant({"business_name": "Acme Plumbing"}) is False
        assert is_internal_tenant({"business_name": ""}) is False
        assert is_internal_tenant({}) is False


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
        rows = [_real_tenant("t1"), _real_tenant("t2"), _real_tenant("t3")]
        db = _make_db(tenant_rows=rows)
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 3
        assert "computed_at" in data

    # Count correctness via HTTP

    def test_http_counts_map_correctly(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active", created_at=_THIS_WEEK),
            _real_tenant("t2", plan="chatbot", plan_status="active", created_at=_THIS_WEEK),
        ]
        chat = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
        leads = [{"client_id": "t1"}]
        new_leads = [
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "t1", "created_at": _THIS_WEEK},
            {"client_id": "t1", "created_at": _THIS_WEEK},
        ]
        new_appts = [{"tenant_id": "t1", "created_at": _THIS_WEEK}]
        db = _make_db(
            tenant_rows=rows,
            chat_messages_data=chat,
            leads_data=leads,
            new_leads_data=new_leads,
            new_appts_data=new_appts,
        )
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 2
        assert data["activated"] == 2
        assert data["with_leads"] == 1
        assert data["paid"] == 2
        assert data["new_signups_week"] == 2
        assert data["new_leads_week"] == 5
        assert data["new_appointments_week"] == 1
        assert data["errors"] == []

    def test_http_partial_failure_still_returns_200(self):
        rows = [
            _real_tenant("t1", plan="agent_os", plan_status="active"),
            _real_tenant("t2", plan="chatbot", plan_status="trialing"),
        ]
        db = _make_db(tenant_rows=rows, raise_chat_messages=True)
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 2
        assert data["activated"] == 0
        assert "activated" in data["errors"]
        assert data["paid"] == 2

    def test_http_internal_tenants_excluded(self):
        """HTTP route: internal tenant does not appear in any count."""
        rows = [
            _real_tenant("t1"),
            _internal_tenant("int-1"),
        ]
        db = _make_db(tenant_rows=rows)
        with patch("backend.services.funnel_metrics.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/product-funnel",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 1  # only the real tenant
        assert data["errors"] == []


# ---------------------------------------------------------------------------
# New funnel stages (2026-07-13): with_appointments + retained_30d
# ---------------------------------------------------------------------------

_OLD_SIGNUP = "2020-01-01T00:00:00+00:00"  # far older than any 30-day cutoff


class TestWithAppointments:
    def _call(self, db):
        from backend.services.funnel_metrics import compute_funnel

        with patch(
            "backend.services.funnel_metrics.get_service_supabase", return_value=db
        ):
            return compute_funnel()

    def test_counts_distinct_real_tenants_with_appointments(self):
        rows = [_real_tenant("t1"), _real_tenant("t2"), _real_tenant("t3")]
        appts = [
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "t1", "created_at": _THIS_WEEK},  # duplicate tenant
            {"tenant_id": "t2", "created_at": _THIS_WEEK},
        ]
        data = self._call(_make_db(tenant_rows=rows, new_appts_data=appts))
        assert data["with_appointments"] == 2

    def test_excludes_non_real_tenants(self):
        rows = [_real_tenant("t1")]
        appts = [
            {"tenant_id": "t1", "created_at": _THIS_WEEK},
            {"tenant_id": "ghost-tenant", "created_at": _THIS_WEEK},
        ]
        data = self._call(_make_db(tenant_rows=rows, new_appts_data=appts))
        assert data["with_appointments"] == 1

    def test_zero_when_query_fails(self):
        rows = [_real_tenant("t1")]
        data = self._call(_make_db(tenant_rows=rows, raise_new_appts=True))
        assert data["with_appointments"] == 0
        assert "with_appointments" in data["errors"]


class TestRetained30d:
    def _call(self, db):
        from backend.services.funnel_metrics import compute_funnel

        with patch(
            "backend.services.funnel_metrics.get_service_supabase", return_value=db
        ):
            return compute_funnel()

    def test_counts_paid_tenants_older_than_30_days(self):
        rows = [
            _real_tenant("t1", created_at=_OLD_SIGNUP),                      # retained
            _real_tenant("t2", created_at=_THIS_WEEK),                       # too new
            _real_tenant("t3", plan="free", created_at=_OLD_SIGNUP),         # never paid
            _real_tenant("t4", plan_status="canceled", created_at=_OLD_SIGNUP),  # churned
        ]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["retained_30d"] == 1

    def test_zero_when_no_old_paid_tenants(self):
        rows = [_real_tenant("t1", created_at=_THIS_WEEK)]
        data = self._call(_make_db(tenant_rows=rows))
        assert data["retained_30d"] == 0
