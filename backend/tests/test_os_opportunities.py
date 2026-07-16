"""Unit tests for the proactive opportunity scan + owner notification.

Contract under test:

  1. ``_suggestion_kind`` classifies our own scanner wording (cold leads /
     overdue invoices) and returns None for anything else.
  2. ``_file_suggestion`` inserts a new pending card, supersedes stale
     pending cards of the same kind (drifting counts), and short-circuits
     on an identical pending summary — so the owner always sees exactly
     one current card per kind.
  3. ``run_opportunity_scan`` emails the owner only for tenants where
     something was actually filed.
  4. ``notify_new_suggestions`` sends one email listing the filed
     summaries (HTML-escaped) and skips tenants without an owner_email.
"""

from typing import Any

import pytest

from backend.services import os_opportunities, os_opportunity_notify


class _Result:
    def __init__(self, data):
        self.data = data


class _BacklogTable:
    """Fluent stub for db.table('os_backlog_requests')."""

    def __init__(self, parent):
        self.parent = parent
        self.mode = None
        self.payload = None
        self.filters = []

    def select(self, *a, **k):
        self.mode = "select"
        return self

    def insert(self, payload):
        self.mode = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, list(values)))
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self.mode == "select":
            return _Result(list(self.parent.pending_rows))
        if self.mode == "insert":
            self.parent.inserts.append(self.payload)
            return _Result([self.payload])
        if self.mode == "update":
            self.parent.updates.append(
                {"payload": self.payload, "filters": self.filters}
            )
            return _Result([])
        raise AssertionError("execute() before select/insert/update")


class _FakeDB:
    def __init__(self, pending_rows=None):
        self.pending_rows = pending_rows or []
        self.inserts: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []

    def table(self, name):
        assert name == "os_backlog_requests"
        return _BacklogTable(self)


def test_suggestion_kind_classifies_scanner_wording():
    assert (
        os_opportunities._suggestion_kind(
            "5 leads went cold this week — want me to follow up?"
        )
        == "cold_leads"
    )
    assert (
        os_opportunities._suggestion_kind(
            "2 unpaid invoices ($900) past due — want me to send reminders?"
        )
        == "overdue_invoices"
    )
    assert os_opportunities._suggestion_kind("book more appointments") is None
    assert os_opportunities._suggestion_kind("") is None
    assert os_opportunities._suggestion_kind(None) is None


def _cold_card(count: int, row_id: str) -> dict[str, Any]:
    return {
        "id": row_id,
        "summary": f"{count} leads went cold this week — want me to follow up?",
    }


def test_file_suggestion_inserts_when_nothing_pending():
    db = _FakeDB(pending_rows=[])
    ok = os_opportunities._file_suggestion(
        db, "tenant-1", {"summary": _cold_card(5, "x")["summary"], "detail": "d"}
    )
    assert ok is True
    assert len(db.inserts) == 1
    assert db.inserts[0]["status"] == "pending"
    assert db.inserts[0]["reason"] == "opportunity"
    assert db.updates == []


def test_file_suggestion_supersedes_stale_same_kind_cards():
    """MTOptions in prod had 4 pending cold-lead cards with drifting counts.
    Filing a new one must retire the old ones so exactly one current card
    remains."""
    db = _FakeDB(pending_rows=[_cold_card(3, "old-1"), _cold_card(4, "old-2")])
    ok = os_opportunities._file_suggestion(
        db, "tenant-1", {"summary": _cold_card(6, "x")["summary"], "detail": "d"}
    )
    assert ok is True
    assert len(db.inserts) == 1
    assert len(db.updates) == 1
    update = db.updates[0]
    assert update["payload"]["status"] == "superseded"
    assert update["payload"]["decided_by"] == "system"
    assert ("in", "id", ["old-1", "old-2"]) in update["filters"]
    assert ("eq", "client_id", "tenant-1") in update["filters"]


def test_file_suggestion_identical_summary_skips_insert_but_supersedes_others():
    db = _FakeDB(pending_rows=[_cold_card(3, "old-1"), _cold_card(6, "current")])
    ok = os_opportunities._file_suggestion(
        db, "tenant-1", {"summary": _cold_card(6, "x")["summary"], "detail": "d"}
    )
    assert ok is False
    assert db.inserts == []
    # The stale 3-lead card still gets retired even though nothing new files.
    assert len(db.updates) == 1
    assert ("in", "id", ["old-1"]) in db.updates[0]["filters"]


def test_file_suggestion_does_not_supersede_other_kinds():
    invoice_card = {
        "id": "inv-1",
        "summary": "1 unpaid invoice ($800) past due — want me to send reminders?",
    }
    db = _FakeDB(pending_rows=[invoice_card])
    ok = os_opportunities._file_suggestion(
        db, "tenant-1", {"summary": _cold_card(2, "x")["summary"], "detail": "d"}
    )
    assert ok is True
    assert db.updates == []  # the invoice card is a different kind — untouched


class _TenantsDB:
    """db.table('tenants') stub for the scan + notify paths."""

    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "tenants"
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Result(self.rows)


class _GateTable:
    """Daily-gate query stub: no recent opportunity rows."""

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Result([])


class _ScanDB:
    """Dispatches by table: tenants -> tenant rows, backlog -> empty gate."""

    def __init__(self, tenant_rows):
        self.tenant_rows = tenant_rows

    def table(self, name):
        if name == "tenants":
            return _TenantsDB(self.tenant_rows)
        return _GateTable()


@pytest.mark.asyncio
async def test_scan_notifies_only_tenants_with_new_filings(monkeypatch):
    db = _ScanDB([{"id": "tenant-a"}, {"id": "tenant-b"}])
    monkeypatch.setattr(os_opportunities, "get_service_supabase", lambda: db)

    def fake_compute(db_, client_id):
        if client_id == "tenant-a":
            return [{"summary": "s1", "detail": "d1"}, {"summary": "s2", "detail": "d2"}]
        return [{"summary": "s3", "detail": "d3"}]

    monkeypatch.setattr(os_opportunities, "compute_suggestions", fake_compute)
    # tenant-a files both; tenant-b's one suggestion dedups away.
    monkeypatch.setattr(
        os_opportunities,
        "_file_suggestion",
        lambda db_, client_id, s: client_id == "tenant-a",
    )

    notified = []

    async def fake_notify(db_, client_id, suggestions):
        notified.append((client_id, [s["summary"] for s in suggestions]))
        return True

    monkeypatch.setattr(
        os_opportunities.os_opportunity_notify, "notify_new_suggestions", fake_notify
    )

    filed = await os_opportunities.run_opportunity_scan()

    assert filed == 2
    assert notified == [("tenant-a", ["s1", "s2"])]


@pytest.mark.asyncio
async def test_notify_new_suggestions_sends_escaped_summaries(monkeypatch):
    sent = []

    async def fake_send_email(*, to, subject, body_html, tenant_id=None):
        sent.append({"to": to, "subject": subject, "body_html": body_html})

    monkeypatch.setattr(os_opportunity_notify, "send_email", fake_send_email)
    db = _TenantsDB([{"owner_email": "owner@example.com", "owner_name": "Sam"}])

    ok = await os_opportunity_notify.notify_new_suggestions(
        db,
        "tenant-1",
        [
            {"summary": "5 leads went cold this week — want me to follow up?"},
            {"summary": "<b>2 invoices</b> past due"},
        ],
    )

    assert ok is True
    assert len(sent) == 1
    assert sent[0]["to"] == "owner@example.com"
    assert "2 opportunities" in sent[0]["subject"]
    assert "5 leads went cold" in sent[0]["body_html"]
    assert "<b>2 invoices</b>" not in sent[0]["body_html"]
    assert "&lt;b&gt;2 invoices&lt;/b&gt;" in sent[0]["body_html"]
    assert "/dashboard/agent-os" in sent[0]["body_html"]


@pytest.mark.asyncio
async def test_notify_new_suggestions_skips_without_owner_email(monkeypatch):
    sent = []

    async def fake_send_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(os_opportunity_notify, "send_email", fake_send_email)
    db = _TenantsDB([{"owner_email": None, "owner_name": "Sam"}])

    ok = await os_opportunity_notify.notify_new_suggestions(
        db, "tenant-1", [{"summary": "s"}]
    )
    assert ok is False
    assert sent == []


@pytest.mark.asyncio
async def test_notify_new_suggestions_empty_list_is_noop(monkeypatch):
    called = []
    monkeypatch.setattr(
        os_opportunity_notify, "send_email", lambda **k: called.append(k)
    )
    assert (
        await os_opportunity_notify.notify_new_suggestions(_TenantsDB([]), "t", [])
        is False
    )
    assert called == []
