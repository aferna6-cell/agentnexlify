"""Tests for compute_tenant_health() and GET /api/v1/admin/tenant-health.

Mirrors the structure of test_funnel_metrics.py:
  - Fake Supabase chain builder (_FakeChain / _make_db)
  - Unit tests against the service function directly (mocked DB)
  - HTTP route tests via a minimal FastAPI test app

Running without conftest is supported (--noconftest flag).

Coverage:
  - 401 when admin secret missing or wrong
  - 200 with correct per-tenant breakdown when all DB calls succeed
  - leads use client_id (not tenant_id)
  - chat_messages and appointments use tenant_id
  - is_paid = plan != 'free' AND plan_status in ('active', 'trialing')
  - status derivation: active / at_risk / dormant
  - last_activity_at is the max created_at across messages, leads, appointments
  - per-table DB failure degrades gracefully (tenants list still populated for successful ones)
  - tenants with zero activity are included as dormant
  - internal/test tenants (AgentNexLiFy, Smoke Test) are excluded from the report
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Fake Supabase chain builder
# ---------------------------------------------------------------------------


class _FakeChain:
    """Chainable Supabase-style query mock — same pattern as test_funnel_metrics.py."""

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
    tenant_rows=None,
    chat_messages_data=None,
    leads_data=None,
    appointments_data=None,
    raise_tenants=False,
    raise_chat_messages=False,
    raise_leads=False,
    raise_appointments=False,
):
    """Build a MagicMock Supabase client routing table() calls.

    compute_tenant_health() calls table() in this order:
      1. "tenants"       — select id, business_name, plan, plan_status
      2. "chat_messages" — select tenant_id, created_at
      3. "leads"         — select client_id, created_at
      4. "appointments"  — select tenant_id, created_at
    """
    def _router(name: str):
        if name == "tenants":
            return _FakeChain(
                data=tenant_rows if tenant_rows is not None else [],
                raise_on_execute=raise_tenants,
            )
        if name == "chat_messages":
            return _FakeChain(
                data=chat_messages_data if chat_messages_data is not None else [],
                raise_on_execute=raise_chat_messages,
            )
        if name == "leads":
            return _FakeChain(
                data=leads_data if leads_data is not None else [],
                raise_on_execute=raise_leads,
            )
        if name == "appointments":
            return _FakeChain(
                data=appointments_data if appointments_data is not None else [],
                raise_on_execute=raise_appointments,
            )
        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _router
    return db


# ---------------------------------------------------------------------------
# Helpers for building timestamps relative to now
# ---------------------------------------------------------------------------


def _ts(days_ago: float) -> str:
    """Return ISO UTC timestamp for N days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Unit tests for compute_tenant_health()
# ---------------------------------------------------------------------------


class TestComputeTenantHealthUnit:
    """Direct unit tests against compute_tenant_health(); HTTP layer tested separately."""

    def _call(self, db):
        from backend.services.tenant_health import compute_tenant_health
        with patch("backend.services.tenant_health.get_service_supabase", return_value=db):
            return compute_tenant_health()

    # --- Happy path ---

    def test_returns_correct_keys_in_response(self):
        db = _make_db(tenant_rows=[{"id": "t1", "business_name": "Acme", "plan": "free", "plan_status": ""}])
        result = self._call(db)
        assert "tenants" in result
        assert "computed_at" in result
        assert len(result["tenants"]) == 1

    def test_tenant_entry_has_all_required_fields(self):
        db = _make_db(tenant_rows=[{"id": "t1", "business_name": "Acme", "plan": "free", "plan_status": ""}])
        entry = self._call(db)["tenants"][0]
        required_keys = {
            "tenant_id", "business_name", "plan", "plan_status", "is_paid",
            "total_messages", "total_leads", "total_appointments",
            "messages_last_7d", "leads_last_7d", "last_activity_at", "status",
        }
        assert required_keys.issubset(set(entry.keys()))

    def test_total_messages_counted_per_tenant(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        msgs = [
            {"tenant_id": "t1", "created_at": _ts(10)},
            {"tenant_id": "t1", "created_at": _ts(20)},
            {"tenant_id": "t2", "created_at": _ts(5)},  # different tenant, should not count
        ]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs))
        entry = result["tenants"][0]
        assert entry["total_messages"] == 2

    def test_total_leads_uses_client_id(self):
        """Leads MUST be counted by client_id, not tenant_id."""
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        leads = [
            {"client_id": "t1", "created_at": _ts(5)},
            {"client_id": "t1", "created_at": _ts(15)},
            {"client_id": "t2", "created_at": _ts(3)},  # different client
        ]
        result = self._call(_make_db(tenant_rows=tenants, leads_data=leads))
        entry = result["tenants"][0]
        assert entry["total_leads"] == 2

    def test_total_appointments_per_tenant(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        appts = [
            {"tenant_id": "t1", "created_at": _ts(2)},
            {"tenant_id": "t1", "created_at": _ts(8)},
        ]
        result = self._call(_make_db(tenant_rows=tenants, appointments_data=appts))
        assert result["tenants"][0]["total_appointments"] == 2

    def test_messages_last_7d_only_counts_recent(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        msgs = [
            {"tenant_id": "t1", "created_at": _ts(3)},   # in 7d window
            {"tenant_id": "t1", "created_at": _ts(5)},   # in 7d window
            {"tenant_id": "t1", "created_at": _ts(10)},  # outside window
        ]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs))
        assert result["tenants"][0]["messages_last_7d"] == 2

    def test_leads_last_7d_only_counts_recent(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        leads = [
            {"client_id": "t1", "created_at": _ts(2)},   # in window
            {"client_id": "t1", "created_at": _ts(20)},  # outside window
        ]
        result = self._call(_make_db(tenant_rows=tenants, leads_data=leads))
        assert result["tenants"][0]["leads_last_7d"] == 1

    def test_last_activity_at_is_max_across_all_sources(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        # Most recent is an appointment at 1 day ago
        recent = _ts(1)
        msgs = [{"tenant_id": "t1", "created_at": _ts(5)}]
        leads = [{"client_id": "t1", "created_at": _ts(10)}]
        appts = [{"tenant_id": "t1", "created_at": recent}]
        result = self._call(_make_db(
            tenant_rows=tenants,
            chat_messages_data=msgs,
            leads_data=leads,
            appointments_data=appts,
        ))
        entry = result["tenants"][0]
        # last_activity_at should be the appointment (most recent)
        assert entry["last_activity_at"] is not None
        assert entry["last_activity_at"] >= _ts(2)  # at least within last 2 days

    def test_last_activity_at_none_when_no_activity(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["last_activity_at"] is None

    # --- Status derivation ---

    def test_status_active_when_activity_within_7_days(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        msgs = [{"tenant_id": "t1", "created_at": _ts(3)}]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs))
        assert result["tenants"][0]["status"] == "active"

    def test_status_at_risk_when_activity_in_8_to_30_days(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        msgs = [{"tenant_id": "t1", "created_at": _ts(15)}]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs))
        assert result["tenants"][0]["status"] == "at_risk"

    def test_status_dormant_when_no_activity_in_30_days(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        msgs = [{"tenant_id": "t1", "created_at": _ts(45)}]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs))
        assert result["tenants"][0]["status"] == "dormant"

    def test_status_dormant_when_no_activity_at_all(self):
        tenants = [{"id": "t1", "business_name": "B1", "plan": "free", "plan_status": ""}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["status"] == "dormant"

    # --- is_paid ---

    def test_is_paid_true_for_chatbot_active(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "chatbot", "plan_status": "active"}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["is_paid"] is True

    def test_is_paid_true_for_agent_os_trialing(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "agent_os", "plan_status": "trialing"}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["is_paid"] is True

    def test_is_paid_false_for_free_plan(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "free", "plan_status": "active"}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["is_paid"] is False

    def test_is_paid_false_for_canceled_paid_plan(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "chatbot", "plan_status": "canceled"}]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"][0]["is_paid"] is False

    def test_is_paid_true_for_legacy_grandfathered_plans(self):
        """Legacy plans (growth, professional, enterprise) are still paid."""
        for plan in ("growth", "professional", "enterprise", "autopilot"):
            tenants = [{"id": "t1", "business_name": "B", "plan": plan, "plan_status": "active"}]
            result = self._call(_make_db(tenant_rows=tenants))
            assert result["tenants"][0]["is_paid"] is True, f"expected is_paid for plan={plan}"

    # --- Multiple tenants ---

    def test_multiple_tenants_each_get_their_own_counts(self):
        tenants = [
            {"id": "t1", "business_name": "Alpha", "plan": "chatbot", "plan_status": "active"},
            {"id": "t2", "business_name": "Beta", "plan": "free", "plan_status": ""},
        ]
        msgs = [
            {"tenant_id": "t1", "created_at": _ts(1)},
            {"tenant_id": "t1", "created_at": _ts(2)},
            {"tenant_id": "t2", "created_at": _ts(20)},
        ]
        leads = [
            {"client_id": "t2", "created_at": _ts(25)},
        ]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs, leads_data=leads))
        by_id = {e["tenant_id"]: e for e in result["tenants"]}

        t1 = by_id["t1"]
        assert t1["total_messages"] == 2
        assert t1["total_leads"] == 0
        assert t1["status"] == "active"
        assert t1["is_paid"] is True

        t2 = by_id["t2"]
        assert t2["total_messages"] == 1
        assert t2["total_leads"] == 1
        assert t2["status"] == "at_risk"  # msg at 20d ago, lead at 25d ago — both within 30d
        assert t2["is_paid"] is False

    # --- Fault tolerance ---

    def test_tenants_fetch_failure_returns_empty_list(self):
        result = self._call(_make_db(raise_tenants=True))
        assert result["tenants"] == []
        assert "computed_at" in result

    def test_chat_messages_failure_leaves_tenants_with_zero_messages(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "free", "plan_status": ""}]
        result = self._call(_make_db(tenant_rows=tenants, raise_chat_messages=True))
        # tenants list should still be populated
        assert len(result["tenants"]) == 1
        entry = result["tenants"][0]
        assert entry["total_messages"] == 0
        assert entry["messages_last_7d"] == 0

    def test_leads_failure_leaves_tenants_with_zero_leads(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "free", "plan_status": ""}]
        msgs = [{"tenant_id": "t1", "created_at": _ts(2)}]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs, raise_leads=True))
        assert len(result["tenants"]) == 1
        entry = result["tenants"][0]
        assert entry["total_leads"] == 0
        assert entry["leads_last_7d"] == 0
        # chat_messages still contributed to last_activity_at + status
        assert entry["status"] == "active"

    def test_appointments_failure_leaves_tenants_with_zero_appointments(self):
        tenants = [{"id": "t1", "business_name": "B", "plan": "free", "plan_status": ""}]
        result = self._call(_make_db(tenant_rows=tenants, raise_appointments=True))
        assert len(result["tenants"]) == 1
        assert result["tenants"][0]["total_appointments"] == 0

    # --- Internal-tenant exclusion ---

    def test_internal_tenant_excluded_from_report(self):
        """Internal/test tenants must not appear in the health report at all."""
        tenants = [
            {"id": "t1", "business_name": "Acme Corp", "plan": "chatbot", "plan_status": "active"},
            {"id": "int-1", "business_name": "AgentNexLiFy Smoke Test", "plan": "agent_os", "plan_status": "active"},
        ]
        result = self._call(_make_db(tenant_rows=tenants))
        tenant_ids = {e["tenant_id"] for e in result["tenants"]}
        assert "t1" in tenant_ids
        assert "int-1" not in tenant_ids
        assert len(result["tenants"]) == 1

    def test_agentnexlify_main_tenant_excluded(self):
        """The primary 'AgentNexLiFy' tenant is excluded."""
        tenants = [
            {"id": "int-0", "business_name": "AgentNexLiFy", "plan": "agent_os", "plan_status": "active"},
            {"id": "t1", "business_name": "Sunrise Salon", "plan": "free", "plan_status": ""},
        ]
        result = self._call(_make_db(tenant_rows=tenants))
        assert len(result["tenants"]) == 1
        assert result["tenants"][0]["tenant_id"] == "t1"

    def test_internal_tenant_activity_does_not_pollute_real_tenant_counts(self):
        """Chat messages and leads belonging to the internal tenant must not
        count toward any real tenant's metrics."""
        tenants = [
            {"id": "t1", "business_name": "Real Biz", "plan": "free", "plan_status": ""},
        ]
        msgs = [
            {"tenant_id": "t1", "created_at": _ts(2)},
            {"tenant_id": "int-smoke", "created_at": _ts(1)},  # internal (not in tenant_rows)
        ]
        leads = [
            {"client_id": "t1", "created_at": _ts(5)},
            {"client_id": "int-smoke", "created_at": _ts(1)},
        ]
        result = self._call(_make_db(tenant_rows=tenants, chat_messages_data=msgs, leads_data=leads))
        assert len(result["tenants"]) == 1
        entry = result["tenants"][0]
        # Only t1's messages and leads count
        assert entry["total_messages"] == 1
        assert entry["total_leads"] == 1

    def test_all_internal_tenants_returns_empty_list(self):
        """If the platform only has internal tenants, the report is empty."""
        tenants = [
            {"id": "i1", "business_name": "AgentNexLiFy", "plan": "agent_os", "plan_status": "active"},
            {"id": "i2", "business_name": "AgentNexLiFy Smoke Test", "plan": "agent_os", "plan_status": "active"},
        ]
        result = self._call(_make_db(tenant_rows=tenants))
        assert result["tenants"] == []

    def test_real_customers_with_non_internal_names_included(self):
        """Tenants whose business_name doesn't match the denylist are always included."""
        tenants = [
            {"id": "t1", "business_name": "Acme Plumbing", "plan": "chatbot", "plan_status": "active"},
            {"id": "t2", "business_name": "Downtown Dental", "plan": "free", "plan_status": ""},
            {"id": "t3", "business_name": "Sunrise Salon", "plan": "agent_os", "plan_status": "trialing"},
        ]
        result = self._call(_make_db(tenant_rows=tenants))
        assert len(result["tenants"]) == 3


# ---------------------------------------------------------------------------
# HTTP route tests — minimal FastAPI test app
# ---------------------------------------------------------------------------


class TestTenantHealthRoute:
    """Integration tests against the real HTTP route in a minimal test app."""

    @pytest.fixture(autouse=True)
    def _build_test_client(self):
        import httpx
        from fastapi import FastAPI
        from backend.limiter import limiter
        from backend.routers.admin_tenant_health import router

        _app = FastAPI()
        _app.include_router(router)

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
        self._admin_secret = "test-admin-secret-xyz"

    @pytest.fixture(autouse=True)
    def _patch_secret(self, monkeypatch):
        monkeypatch.setattr(
            "backend.routers.admin_tenant_health._admin_secret",
            lambda: self._admin_secret,
        )

    def _admin_headers(self):
        return {"x-api-secret": self._admin_secret}

    # --- Auth ---

    def test_no_secret_returns_401(self):
        resp = self._get("/api/v1/admin/tenant-health")
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self):
        resp = self._get(
            "/api/v1/admin/tenant-health",
            headers={"x-api-secret": "wrong-secret"},
        )
        assert resp.status_code == 401

    def test_correct_secret_returns_200(self):
        tenants = [{"id": "t1", "business_name": "Acme", "plan": "free", "plan_status": ""}]
        db = _make_db(tenant_rows=tenants)
        with patch("backend.services.tenant_health.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/tenant-health",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenants" in data
        assert "computed_at" in data

    # --- Response shape ---

    def test_response_shape_matches_contract(self):
        tenants = [{"id": "t1", "business_name": "Acme", "plan": "chatbot", "plan_status": "active"}]
        msgs = [{"tenant_id": "t1", "created_at": _ts(2)}]
        leads = [{"client_id": "t1", "created_at": _ts(5)}]
        appts = [{"tenant_id": "t1", "created_at": _ts(3)}]
        db = _make_db(tenant_rows=tenants, chat_messages_data=msgs, leads_data=leads, appointments_data=appts)
        with patch("backend.services.tenant_health.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/tenant-health",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tenants"]) == 1
        entry = data["tenants"][0]
        # All required response fields
        assert entry["tenant_id"] == "t1"
        assert entry["business_name"] == "Acme"
        assert entry["plan"] == "chatbot"
        assert entry["plan_status"] == "active"
        assert entry["is_paid"] is True
        assert entry["total_messages"] == 1
        assert entry["total_leads"] == 1
        assert entry["total_appointments"] == 1
        assert entry["messages_last_7d"] == 1
        assert entry["leads_last_7d"] == 1
        assert entry["last_activity_at"] is not None
        assert entry["status"] == "active"

    def test_http_status_values_are_valid_enum(self):
        valid_statuses = {"active", "at_risk", "dormant"}
        tenants = [
            {"id": "t1", "business_name": "A", "plan": "free", "plan_status": ""},
            {"id": "t2", "business_name": "B", "plan": "free", "plan_status": ""},
        ]
        msgs = [{"tenant_id": "t1", "created_at": _ts(2)}]
        db = _make_db(tenant_rows=tenants, chat_messages_data=msgs)
        with patch("backend.services.tenant_health.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/tenant-health",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        for entry in resp.json()["tenants"]:
            assert entry["status"] in valid_statuses

    def test_http_empty_platform_returns_empty_tenants(self):
        db = _make_db(tenant_rows=[])
        with patch("backend.services.tenant_health.get_service_supabase", return_value=db):
            resp = self._get(
                "/api/v1/admin/tenant-health",
                headers=self._admin_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenants"] == []
        assert "computed_at" in data
