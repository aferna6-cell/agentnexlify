"""Unit tests for the stale pending-draft expiry sweep.

Contract:

  1. Drafts pending_approval and untouched for 14+ days get
     deliverable_status='expired'; the WHERE clause re-checks the status so
     an owner approving mid-sweep wins the race.
  2. No stale rows -> no updates, no digest.
  3. One row's update failure never blocks the rest of the tenant's rows.
  4. Digest email goes to the owner with count + titles; a tenant without
     an owner_email is skipped without error.
  5. Cross-tenant sweep sums per-tenant counts and only notifies tenants
     where something actually expired.
"""

from typing import Any

import pytest

from backend.services import os_draft_expiry


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Chain:
    """Fluent query stub covering both the select and update paths."""

    def __init__(self, parent):
        self.parent = parent
        self.mode = None
        self.payload = None
        self.filters = []

    def select(self, *a, **k):
        self.mode = "select"
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def lt(self, column, value):
        self.filters.append(("lt", column, value))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self.mode == "select":
            if self.parent.select_raises:
                raise RuntimeError("select boom")
            return _Result(self.parent.stale_rows)
        idx = len(self.parent.updates)
        self.parent.updates.append(
            {"payload": self.payload, "filters": self.filters}
        )
        if idx in self.parent.raise_on_update:
            raise RuntimeError("update boom")
        data = self.parent.update_datas[idx] if self.parent.update_datas else [
            {"id": "updated"}
        ]
        return _Result(data)


class _FakeTenantTable:
    """Callable standing in for tenant_scope.tenant_table."""

    def __init__(
        self,
        stale_rows,
        *,
        update_datas=None,
        raise_on_update=(),
        select_raises=False,
    ):
        self.stale_rows = stale_rows
        self.update_datas = update_datas
        self.raise_on_update = set(raise_on_update)
        self.select_raises = select_raises
        self.updates: list[dict[str, Any]] = []
        self.tables: list[str] = []

    def __call__(self, db, table, client_id):
        self.tables.append(table)
        return _Chain(self)


def _stale_row(run_id: str, title: str = "Old draft") -> dict[str, Any]:
    return {
        "id": run_id,
        "agent_name": "sales",
        "deliverable": {"title": title, "body": "hi", "channel": "email"},
        "updated_at": "2026-06-10T00:00:00+00:00",
    }


def test_expire_stale_drafts_marks_rows_expired(monkeypatch):
    fake = _FakeTenantTable([_stale_row("run-1"), _stale_row("run-2")])
    monkeypatch.setattr(os_draft_expiry, "tenant_table", fake)

    expired = os_draft_expiry.expire_stale_drafts(object(), "tenant-1")

    assert [r["id"] for r in expired] == ["run-1", "run-2"]
    assert fake.tables[0] == "os_agent_runs"
    assert len(fake.updates) == 2
    for update, run_id in zip(fake.updates, ["run-1", "run-2"]):
        assert update["payload"]["deliverable_status"] == "expired"
        assert "updated_at" in update["payload"]
        # Race guard: WHERE re-checks id AND pending status.
        assert ("eq", "id", run_id) in update["filters"]
        assert (
            "eq",
            "deliverable_status",
            "pending_approval",
        ) in update["filters"]


def test_expire_stale_drafts_no_stale_rows(monkeypatch):
    fake = _FakeTenantTable([])
    monkeypatch.setattr(os_draft_expiry, "tenant_table", fake)

    assert os_draft_expiry.expire_stale_drafts(object(), "tenant-1") == []
    assert fake.updates == []


def test_expire_stale_drafts_survives_single_update_failure(monkeypatch):
    fake = _FakeTenantTable(
        [_stale_row("run-1"), _stale_row("run-2"), _stale_row("run-3")],
        raise_on_update=[1],
    )
    monkeypatch.setattr(os_draft_expiry, "tenant_table", fake)

    expired = os_draft_expiry.expire_stale_drafts(object(), "tenant-1")

    # run-2's update blew up; run-1 and run-3 still expired.
    assert [r["id"] for r in expired] == ["run-1", "run-3"]
    assert len(fake.updates) == 3


def test_expire_stale_drafts_loses_race_gracefully(monkeypatch):
    # Owner approved run-1 between our read and write: update matches 0 rows.
    fake = _FakeTenantTable(
        [_stale_row("run-1"), _stale_row("run-2")],
        update_datas=[[], [{"id": "run-2"}]],
    )
    monkeypatch.setattr(os_draft_expiry, "tenant_table", fake)

    expired = os_draft_expiry.expire_stale_drafts(object(), "tenant-1")

    assert [r["id"] for r in expired] == ["run-2"]


def test_expire_stale_drafts_select_failure_returns_empty(monkeypatch):
    fake = _FakeTenantTable([], select_raises=True)
    monkeypatch.setattr(os_draft_expiry, "tenant_table", fake)

    assert os_draft_expiry.expire_stale_drafts(object(), "tenant-1") == []
    assert fake.updates == []


class _TenantsDB:
    """db.table('tenants') stub returning preset rows."""

    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Result(self.rows)


@pytest.mark.asyncio
async def test_notify_owner_digest_sends_count_and_titles(monkeypatch):
    sent = []

    async def fake_send_email(*, to, subject, body_html, tenant_id=None):
        sent.append({"to": to, "subject": subject, "body_html": body_html})

    monkeypatch.setattr(os_draft_expiry, "send_email", fake_send_email)
    db = _TenantsDB([{"owner_email": "owner@example.com", "owner_name": "Sam"}])

    expired = [
        _stale_row("run-1", title="Check in with Alice"),
        _stale_row("run-2", title="Payment reminder <b>INV-9</b>"),
    ]
    ok = await os_draft_expiry._notify_owner_digest(db, "tenant-1", expired)

    assert ok is True
    assert len(sent) == 1
    assert sent[0]["to"] == "owner@example.com"
    assert "2 old drafts expired" in sent[0]["subject"]
    assert "nothing was sent" in sent[0]["subject"]
    assert "Check in with Alice" in sent[0]["body_html"]
    # Titles echo draft content -> must be HTML-escaped in the owner's inbox.
    assert "<b>INV-9</b>" not in sent[0]["body_html"]
    assert "&lt;b&gt;INV-9&lt;/b&gt;" in sent[0]["body_html"]


@pytest.mark.asyncio
async def test_notify_owner_digest_skips_missing_owner_email(monkeypatch):
    sent = []

    async def fake_send_email(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(os_draft_expiry, "send_email", fake_send_email)
    db = _TenantsDB([{"owner_email": None, "owner_name": "Sam"}])

    ok = await os_draft_expiry._notify_owner_digest(
        db, "tenant-1", [_stale_row("run-1")]
    )

    assert ok is False
    assert sent == []


@pytest.mark.asyncio
async def test_sweep_expires_across_tenants_and_notifies_selectively(monkeypatch):
    db = _TenantsDB([{"id": "tenant-a"}, {"id": "tenant-b"}])
    monkeypatch.setattr(os_draft_expiry, "get_service_supabase", lambda: db)

    per_tenant = {
        "tenant-a": [_stale_row("run-1"), _stale_row("run-2")],
        "tenant-b": [],
    }
    monkeypatch.setattr(
        os_draft_expiry,
        "expire_stale_drafts",
        lambda db_, client_id: per_tenant[client_id],
    )

    notified = []

    async def fake_digest(db_, client_id, expired):
        notified.append((client_id, len(expired)))
        return True

    monkeypatch.setattr(os_draft_expiry, "_notify_owner_digest", fake_digest)

    total = await os_draft_expiry.run_draft_expiry_sweep()

    assert total == 2
    # Only the tenant that had something expire gets a digest.
    assert notified == [("tenant-a", 2)]


@pytest.mark.asyncio
async def test_sweep_tenant_query_failure_returns_zero(monkeypatch):
    class _Boom:
        def table(self, name):
            raise RuntimeError("db down")

    monkeypatch.setattr(os_draft_expiry, "get_service_supabase", lambda: _Boom())

    assert await os_draft_expiry.run_draft_expiry_sweep() == 0
