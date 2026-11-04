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


class _Idempotency:
    """Shared idempotency_keys table. Upsert with ignore_duplicates claims once."""

    def __init__(self, rows):
        self._rows = rows
        self._payload = None
        self._ignore_duplicates = False
        self._eq_key = None

    def upsert(self, payload, on_conflict="key", ignore_duplicates=False):
        self._payload = payload
        self._ignore_duplicates = ignore_duplicates
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        if column == "key":
            self._eq_key = value
        return self

    def limit(self, _count):
        return self

    def execute(self):
        if self._payload is not None:
            key = self._payload["key"]
            existing = [row for row in self._rows if row.get("key") == key]
            payload = self._payload
            self._payload = None
            if existing and self._ignore_duplicates:
                return SimpleNamespace(data=[])
            if not existing:
                row = dict(payload)
                self._rows.append(row)
                return SimpleNamespace(data=[row])
            return SimpleNamespace(data=existing)
        rows = self._rows
        if self._eq_key is not None:
            rows = [row for row in rows if row.get("key") == self._eq_key]
        return SimpleNamespace(data=list(rows))


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        if name == "idempotency_keys":
            return _Idempotency(self.tables.setdefault("idempotency_keys", []))
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


def _shared_db():
    tables = _fixture()
    tables["idempotency_keys"] = []
    return _DB(tables)


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

    shared = _shared_db()
    monkeypatch.setattr(alert, "get_service_supabase", lambda: shared)
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


def test_restart_or_second_replica_does_not_resend(monkeypatch):
    """The claim lives in idempotency_keys, not in process memory."""
    calls = {"n": 0}
    shared = _shared_db()

    async def capture(*_args, **_kwargs):
        calls["n"] += 1
        return {"success": True}

    monkeypatch.setattr(alert, "get_service_supabase", lambda: shared)
    monkeypatch.setattr(alert, "send_platform_email", capture)

    assert run(alert.run_quiet_client_alert(_noon())) == 1
    assert shared.tables["idempotency_keys"][0]["key"] == "quiet_client_alert:2026-11-04"

    # A restarted process or another replica has no in-memory date. It sees
    # the same claimed row and must not send again.
    assert not hasattr(alert, "_last_alert_date")
    replica = _DB(shared.tables)
    monkeypatch.setattr(alert, "get_service_supabase", lambda: replica)
    assert run(alert.run_quiet_client_alert(_noon())) == 0
    assert calls["n"] == 1
    assert len(shared.tables["idempotency_keys"]) == 1
