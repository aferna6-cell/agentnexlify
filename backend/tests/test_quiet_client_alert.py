"""Daily quiet-widget alert: paying tenants with no conversations in 7 days."""

from datetime import datetime, timezone
from types import SimpleNamespace

from backend.services import quiet_client_alert as alert
from backend.tests.fake_supabase import run


class _Query:
    def __init__(self, rows):
        self._rows = list(rows)
        self._ops = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._ops.append(("eq", column, value))
        return self

    def gte(self, column, value):
        self._ops.append(("gte", column, value))
        return self

    def in_(self, column, values):
        self._ops.append(("in", column, set(values)))
        return self

    def limit(self, count):
        self._ops.append(("limit", count))
        return self

    def execute(self):
        rows = list(self._rows)
        limit = None
        for op in self._ops:
            kind = op[0]
            if kind == "eq":
                rows = [row for row in rows if row.get(op[1]) == op[2]]
            elif kind == "gte":
                rows = [row for row in rows if (row.get(op[1]) or "") >= op[2]]
            elif kind == "in":
                rows = [row for row in rows if row.get(op[1]) in op[2]]
            elif kind == "limit":
                limit = op[1]
        if limit is not None:
            rows = rows[:limit]
        return SimpleNamespace(data=rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self.tables.get(name, []))


def _noon():
    return datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def _fixture():
    return {
        "widget_configs": [
            {"tenant_id": "paid-silent"},
            {"tenant_id": "paid-active"},
            {"tenant_id": "free-silent"},
            {"tenant_id": "demo-silent"},
            {"tenant_id": "internal-silent"},
        ],
        "tenants": [
            {
                "id": "paid-silent",
                "business_name": "Keys Koffee",
                "plan": "agent_os",
                "plan_status": "active",
                "business_slug": "keys-koffee",
            },
            {
                "id": "paid-active",
                "business_name": "Busy Shop",
                "plan": "chatbot",
                "plan_status": "active",
                "business_slug": "busy",
            },
            {
                "id": "free-silent",
                "business_name": "Lapsed",
                "plan": "free",
                "plan_status": "canceled",
                "business_slug": "lapsed",
            },
            {
                "id": "demo-silent",
                "business_name": "Demo Cafe",
                "plan": "agent_os",
                "plan_status": "active",
                "business_slug": "demo",
            },
            {
                "id": "internal-silent",
                "business_name": "AgentNexLiFy Smoke Test",
                "plan": "agent_os",
                "plan_status": "trialing",
                "business_slug": "staff",
            },
        ],
        "conversations": [
            {
                "id": "c-active",
                "client_id": "paid-active",
                "created_at": "2026-11-03T00:00:00+00:00",
            },
            {
                "id": "c-other",
                "client_id": "someone-else",
                "created_at": "2026-11-03T00:00:00+00:00",
            },
            {
                "id": "c-old",
                "client_id": "paid-silent",
                "created_at": "2026-10-01T00:00:00+00:00",
            },
        ],
    }


def setup_function():
    alert._last_alert_date = None


def test_before_morning_does_not_query(monkeypatch):
    def forbidden():
        raise AssertionError("database must stay idle before 09:00 UTC")

    monkeypatch.setattr(alert, "get_service_supabase", forbidden)
    count = run(
        alert.run_quiet_client_alert(datetime(2026, 11, 4, 8, 59, tzinfo=timezone.utc))
    )
    assert count == 0


def test_flags_only_the_silent_paying_widget(monkeypatch):
    sent = {}

    async def capture(subject, body_html, **_kwargs):
        sent["subject"] = subject
        sent["body"] = body_html
        return {"success": True}

    monkeypatch.setattr(alert, "get_service_supabase", lambda: _DB(_fixture()))
    monkeypatch.setattr(alert, "send_platform_email", capture)

    count = run(alert.run_quiet_client_alert(_noon()))

    assert count == 1
    assert "Keys Koffee" in sent["body"]
    assert "paid-silent" in sent["body"]
    assert "Busy Shop" not in sent["body"]
    assert "Lapsed" not in sent["body"]
    assert "Demo Cafe" not in sent["body"]
    assert "Smoke Test" not in sent["body"]
    assert "someone-else" not in sent["body"]


def test_same_day_second_call_does_not_send_again(monkeypatch):
    calls = {"n": 0}

    async def capture(*_args, **_kwargs):
        calls["n"] += 1
        return {"success": True}

    monkeypatch.setattr(alert, "get_service_supabase", lambda: _DB(_fixture()))
    monkeypatch.setattr(alert, "send_platform_email", capture)

    assert run(alert.run_quiet_client_alert(_noon())) == 1
    assert run(alert.run_quiet_client_alert(_noon())) == 0
    assert calls["n"] == 1
