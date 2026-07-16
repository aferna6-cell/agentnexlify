"""Tests for GET /api/v1/admin/loop-health.

Covers:
  - 401 when admin secret missing or wrong
  - deliverables aggregation: status counts, oldest pending age, expired_7d
  - suggestions aggregation: status counts, oldest pending, filed_24h,
    last_filed_at
  - os_activity + errors counts from count queries
  - bridges: enabled means row enabled AND some *_enabled flag true
  - fault tolerance: one failing section nulls only itself, endpoint 200
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.limiter import limiter

_ADMIN_SECRET = "test-admin-secret-loop-health"

_NOW = datetime.now(timezone.utc)


def _iso_days_ago(days: float) -> str:
    return (_NOW - timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture()
def admin_headers():
    return {"x-api-secret": _ADMIN_SECRET}


@pytest.fixture(autouse=True)
def _patch_admin_secret(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.admin_health._admin_secret",
        lambda: _ADMIN_SECRET,
    )


class _FakeChain:
    def __init__(self, data=None, count=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._count = count
        self._raise = raise_on_execute

    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def gte(self, *_):
        return self

    def filter(self, *_):
        return self

    def limit(self, *_):
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
    runs=None,
    backlog=None,
    threads_count=0,
    runs_7d_count=0,
    bridges=None,
    errors_count=0,
    fail_tables=(),
):
    """Route table() calls to fake chains.

    os_agent_runs is queried twice: first for deliverables (row data),
    then for the 7-day runs count.
    """
    runs_calls = [0]

    def _table_router(name: str):
        if name in fail_tables:
            return _FakeChain(raise_on_execute=True)
        if name == "os_agent_runs":
            runs_calls[0] += 1
            if runs_calls[0] == 1:
                return _FakeChain(data=runs or [])
            return _FakeChain(data=[], count=runs_7d_count)
        if name == "os_backlog_requests":
            return _FakeChain(data=backlog or [])
        if name == "os_threads":
            return _FakeChain(data=[], count=threads_count)
        if name == "tenant_integrations":
            return _FakeChain(data=bridges or [])
        if name == "error_events":
            return _FakeChain(data=[], count=errors_count)
        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _table_router
    return db


class TestLoopHealthAuth:
    def test_no_secret_returns_401(self, client):
        resp = client.get("/api/v1/admin/loop-health")
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        resp = client.get(
            "/api/v1/admin/loop-health",
            headers={"x-api-secret": "wrong-secret"},
        )
        assert resp.status_code == 401


class TestLoopHealthAggregation:
    def test_deliverables_counts_ages_and_expiries(
        self, client, mock_supabase, admin_headers
    ):
        db = _make_db(
            runs=[
                {"deliverable_status": "pending_approval", "updated_at": _iso_days_ago(30)},
                {"deliverable_status": "pending_approval", "updated_at": _iso_days_ago(2)},
                {"deliverable_status": "expired", "updated_at": _iso_days_ago(1)},
                {"deliverable_status": "expired", "updated_at": _iso_days_ago(20)},
                {"deliverable_status": "approved", "updated_at": _iso_days_ago(5)},
            ],
        )
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/loop-health", headers=admin_headers)
        assert resp.status_code == 200
        d = resp.json()["deliverables"]
        assert d["by_status"] == {
            "pending_approval": 2,
            "expired": 2,
            "approved": 1,
        }
        # Oldest pending is ~30 days old.
        assert 29 <= d["pending_oldest_age_days"] <= 31
        # Only the 1-day-old expiry falls inside the 7-day window.
        assert d["expired_7d"] == 1

    def test_suggestions_freshness_and_counts(
        self, client, mock_supabase, admin_headers
    ):
        db = _make_db(
            backlog=[
                {"status": "pending", "created_at": _iso_days_ago(35)},
                {"status": "pending", "created_at": _iso_days_ago(0.5)},
                {"status": "superseded", "created_at": _iso_days_ago(10)},
                {"status": "accepted", "created_at": _iso_days_ago(3)},
            ],
        )
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/loop-health", headers=admin_headers)
        assert resp.status_code == 200
        s = resp.json()["suggestions"]
        assert s["by_status"] == {"pending": 2, "superseded": 1, "accepted": 1}
        assert 34 <= s["pending_oldest_age_days"] <= 36
        assert s["filed_24h"] == 1
        assert s["last_filed_at"] is not None

    def test_activity_bridges_and_errors(
        self, client, mock_supabase, admin_headers
    ):
        db = _make_db(
            threads_count=4,
            runs_7d_count=9,
            errors_count=2,
            bridges=[
                # Enabled row with widget bridge on -> counts.
                {
                    "client_id": "t1",
                    "enabled": True,
                    "config_jsonb": {"widget_enabled": True, "email_enabled": False},
                },
                # All toggles off -> configured but not enabled.
                {
                    "client_id": "t2",
                    "enabled": True,
                    "config_jsonb": {"widget_enabled": False},
                },
                # Integration row disabled entirely -> not enabled.
                {
                    "client_id": "t3",
                    "enabled": False,
                    "config_jsonb": {"sms_enabled": True},
                },
            ],
        )
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/loop-health", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["os_activity"] == {"threads_7d": 4, "runs_7d": 9}
        assert body["bridges"] == {"tenants_configured": 3, "tenants_enabled": 1}
        assert body["errors_7d"] == 2
        assert body["generated_at"]

    def test_empty_prod_state_returns_zeroes(
        self, client, mock_supabase, admin_headers
    ):
        db = _make_db()
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/loop-health", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deliverables"] == {
            "by_status": {},
            "pending_oldest_age_days": None,
            "expired_7d": 0,
        }
        assert body["suggestions"]["by_status"] == {}
        assert body["suggestions"]["last_filed_at"] is None


class TestLoopHealthFaultTolerance:
    def test_failing_section_nulls_only_itself(
        self, client, mock_supabase, admin_headers
    ):
        db = _make_db(
            backlog=[{"status": "pending", "created_at": _iso_days_ago(1)}],
            errors_count=5,
            fail_tables=("os_agent_runs",),
        )
        mock_supabase.table.side_effect = db.table.side_effect

        resp = client.get("/api/v1/admin/loop-health", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        # os_agent_runs feeds deliverables AND os_activity - both null.
        assert body["deliverables"] is None
        assert body["os_activity"] is None
        # The rest still computed.
        assert body["suggestions"]["by_status"] == {"pending": 1}
        assert body["errors_7d"] == 5
