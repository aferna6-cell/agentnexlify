from pathlib import Path

import pytest

from backend.services.tenant_scope import (
    TenantScopeError,
    tenant_delete,
    tenant_insert,
    tenant_scope_column,
    tenant_select,
    tenant_update,
    tenant_upsert,
)


class FakeQuery:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.filters = []
        self.selected = None
        self.select_kwargs = None
        self.insert_payload = None
        self.update_payload = None
        self.upsert_payload = None
        self.upsert_kwargs = None
        self.deleted = False

    def select(self, columns="*", **kwargs):
        self.selected = columns
        self.select_kwargs = kwargs
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def upsert(self, payload, **kwargs):
        self.upsert_payload = payload
        self.upsert_kwargs = kwargs
        return self

    def delete(self):
        self.deleted = True
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self


class FakeDB:
    def __init__(self):
        self.queries = []

    def table(self, table_name: str):
        query = FakeQuery(table_name)
        self.queries.append(query)
        return query


def test_tenant_scope_column_handles_live_schema_overrides():
    assert tenant_scope_column("leads") == "client_id"
    assert tenant_scope_column("conversations") == "client_id"
    assert tenant_scope_column("activity_log") == "tenant_id"


def test_tenant_select_starts_with_required_scope_filter():
    db = FakeDB()

    query = tenant_select(db, "leads", "tenant-1", "id, email", count="exact")

    assert query.table_name == "leads"
    assert query.selected == "id, email"
    assert query.select_kwargs == {"count": "exact"}
    assert query.filters == [("client_id", "tenant-1")]


def test_tenant_update_and_delete_use_default_tenant_column():
    db = FakeDB()

    update_query = tenant_update(db, "activity_log", "tenant-1", {"lead_id": "lead-2"})
    delete_query = tenant_delete(db, "activity_log", "tenant-1")

    assert update_query.update_payload == {"lead_id": "lead-2"}
    assert update_query.filters == [("tenant_id", "tenant-1")]
    assert delete_query.deleted is True
    assert delete_query.filters == [("tenant_id", "tenant-1")]


def test_tenant_insert_injects_scope_without_mutating_caller_payload():
    db = FakeDB()
    row = {"email": "a@example.com"}

    query = tenant_insert(db, "leads", "tenant-1", row)

    assert query.insert_payload == {"email": "a@example.com", "client_id": "tenant-1"}
    assert row == {"email": "a@example.com"}


def test_tenant_insert_rejects_cross_tenant_payloads():
    db = FakeDB()

    with pytest.raises(TenantScopeError):
        tenant_insert(db, "leads", "tenant-1", {"client_id": "tenant-2", "email": "a@example.com"})


def test_tenant_upsert_injects_scope_and_preserves_options():
    db = FakeDB()

    query = tenant_upsert(
        db,
        "conversations",
        "tenant-1",
        {"session_id": "sess-1"},
        on_conflict="client_id,session_id",
    )

    assert query.upsert_payload == {"session_id": "sess-1", "client_id": "tenant-1"}
    assert query.upsert_kwargs == {"on_conflict": "client_id,session_id"}


def test_high_risk_routes_do_not_bypass_tenant_scope_helpers():
    repo_root = Path(__file__).resolve().parent.parent
    high_risk_files = [
        repo_root / "backend" / "routers" / "conversation_inbox.py",
        repo_root / "backend" / "routers" / "leads.py",
        repo_root / "backend" / "routers" / "widget_helpers.py",
    ]
    direct_table_patterns = [
        'db.table("action_items"',
        'db.table("activity_log"',
        'db.table("appointments"',
        'db.table("chat_messages"',
        'db.table("conversation_notes"',
        'db.table("conversations"',
        'db.table("email_events"',
        'db.table("leads"',
        'db.table("response_metrics"',
        'db.table("team_members"',
        'db.table("tenant_tag_definitions"',
    ]

    for path in high_risk_files:
        source = path.read_text(encoding="utf-8")
        bypasses = [pattern for pattern in direct_table_patterns if pattern in source]
        assert bypasses == [], f"{path} bypasses tenant_scope helpers: {bypasses}"
