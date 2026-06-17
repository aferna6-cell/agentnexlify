"""Contract tests for GET /api/v1/os/usage.

The endpoint reports the current billing cycle's agent-run/message counters
plus the plan tier and percent-of-cap consumed. The percent + plan fields power
the in-app upgrade nudge, so this locks their shape and the tenant scoping
(usage is read for the caller's client_id only).
"""

import asyncio

import pytest

from backend.routers import os_usage
from backend.services import usage_meter


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Chainable supabase stub returning canned rows; records the client_id
    each query is scoped to so a test can prove tenant isolation."""

    def __init__(self, rows, scope_sink):
        self._rows = rows
        self._scope_sink = scope_sink

    def select(self, *_a, **_k):
        return self

    def insert(self, payload):
        return _Query([{**payload, "id": "new-row"}], self._scope_sink)

    def update(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if col == "id":
            self._scope_sink.append(val)
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return _Result(self._rows)


class _FakeDB:
    def __init__(self, rows_by_table, scope_sink):
        self.rows_by_table = rows_by_table
        self.scope_sink = scope_sink

    def table(self, name):
        return _Query(self.rows_by_table.get(name, []), self.scope_sink)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _call(monkeypatch, plan, agent_runs, cap_rows_plan=None):
    """Invoke the endpoint with a fake DB scoped to client 'tenant-xyz'.

    Returns (response_dict, scoped_client_ids).
    """
    scope_sink: list = []
    rows = {
        "tenants": [{"plan": plan}],
        "os_tenant_usage": [
            {
                "cycle_start": "2026-06-01",
                "agent_runs": agent_runs,
                "messages": 3,
                "input_tokens": 10,
                "output_tokens": 20,
            }
        ],
    }
    db = _FakeDB(rows, scope_sink)
    monkeypatch.setattr(os_usage, "get_service_supabase", lambda: db)
    monkeypatch.setattr(os_usage, "get_ai_usage_status", lambda *_a, **_k: {"ok": True})

    claims = {"tenant_id": "tenant-xyz"}
    resp = _run(os_usage.get_usage(claims=claims))
    return resp, scope_sink


def test_response_shape_includes_plan_and_percent(monkeypatch):
    resp, _ = _call(monkeypatch, plan="chatbot", agent_runs=80)
    # cap for chatbot is 100 -> 80/100 = 80%
    assert resp["plan"] == "chatbot"
    assert resp["cap"] == 100
    assert resp["agent_runs"] == 80
    assert resp["percent"] == 80
    assert resp["cap_reached"] is False
    assert "ai_usage" in resp


def test_percent_clamps_and_flags_cap_reached(monkeypatch):
    resp, _ = _call(monkeypatch, plan="free", agent_runs=30)
    # free cap is 25; 30 runs -> clamped to 100% and cap_reached True
    assert resp["plan"] == "free"
    assert resp["cap"] == 25
    assert resp["percent"] == 100
    assert resp["cap_reached"] is True


def test_percent_zero_when_no_runs(monkeypatch):
    resp, _ = _call(monkeypatch, plan="agent_os", agent_runs=0)
    assert resp["plan"] == "agent_os"
    assert resp["percent"] == 0
    assert resp["cap_reached"] is False


def test_usage_is_scoped_to_caller_client_id(monkeypatch):
    _, scoped = _call(monkeypatch, plan="chatbot", agent_runs=10)
    # Every tenants/os_tenant_usage query filtered by the caller's id only.
    assert scoped, "expected at least one id-scoped query"
    assert set(scoped) == {"tenant-xyz"}


def test_tenant_plan_defaults_free_on_missing_row(monkeypatch):
    # Sanity on the helper the endpoint reuses: no tenant row -> free.
    db = _FakeDB({"tenants": []}, [])
    assert usage_meter.tenant_plan(db, "t1") == "free"
