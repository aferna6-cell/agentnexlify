"""GDPR account deletion contracts (launch rubric 1.3).

1. A full purge deletes every listed table's rows AND the tenants row,
   reporting counts.
2. A failing table is skipped and recorded — never fatal, re-runnable.
3. Stripe close is best-effort: a failure doesn't stop the purge.
4. The table list stays in sync with tenant_scope's client_id overrides so
   new os_* tables can't be forgotten silently.
"""

import pytest

from backend.services import account_deletion
from backend.services.account_deletion import (
    TENANT_DATA_TABLES,
    delete_tenant_account,
)
from backend.services.tenant_scope import _TENANT_COLUMN_OVERRIDES


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._deleting = False

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def delete(self):
        self._deleting = True
        return self

    def execute(self):
        if self._name in self._db.fail_tables:
            raise RuntimeError(f"boom on {self._name}")
        if self._deleting:
            rows = self._db.rows.pop(self._name, [])
            self._db.deleted[self._name] = len(rows)
            return _Result(rows)
        return _Result(self._db.rows.get(self._name, []))


class _FakeDB:
    def __init__(self, rows=None, fail_tables=()):
        self.rows = rows or {}
        self.fail_tables = set(fail_tables)
        self.deleted = {}

    def table(self, name):
        return _Query(self, name)


def test_full_purge_deletes_data_and_tenant_row():
    db = _FakeDB(
        rows={
            "tenants": [{"id": "t1", "stripe_customer_id": None}],
            "leads": [{"id": 1}, {"id": 2}],
            "chat_messages": [{"id": 3}],
        }
    )
    report = delete_tenant_account(db, "t1")
    assert report.rows_deleted == 3
    assert report.tenant_row_deleted is True
    assert report.tables_skipped == []
    assert report.tables_purged == len(TENANT_DATA_TABLES)
    assert "tenants" not in db.rows  # the row itself is gone


def test_failing_table_is_skipped_not_fatal():
    db = _FakeDB(
        rows={"tenants": [{"id": "t1"}], "leads": [{"id": 1}]},
        fail_tables={"appointments"},
    )
    report = delete_tenant_account(db, "t1")
    assert report.tables_skipped == ["appointments"]
    assert report.rows_deleted == 1
    assert report.tenant_row_deleted is True


def test_stripe_failure_does_not_block_purge(monkeypatch):
    def boom(_customer_id):
        raise RuntimeError("stripe down")

    monkeypatch.setattr(account_deletion, "_close_stripe_customer", lambda c: False)
    db = _FakeDB(rows={"tenants": [{"id": "t1", "stripe_customer_id": "cus_x"}]})
    report = delete_tenant_account(db, "t1")
    assert report.stripe_closed is False
    assert report.tenant_row_deleted is True


def test_os_workflow_tables_are_purged_child_before_parent():
    steps_at = TENANT_DATA_TABLES.index("os_workflow_steps")
    workflows_at = TENANT_DATA_TABLES.index("os_workflows")
    assert steps_at < workflows_at


class _ScopedQuery:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._filters = []
        self._deleting = False

    def select(self, *_a, **_k):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def limit(self, *_a, **_k):
        return self

    def delete(self):
        self._deleting = True
        return self

    def execute(self):
        if self._name in self._db.fail_tables:
            raise RuntimeError(f"boom on {self._name}")
        rows = self._db.rows.setdefault(self._name, [])
        if not self._deleting:
            return _Result(list(rows))

        def matches(row):
            return all(row.get(column) == value for column, value in self._filters)

        kept = []
        removed = []
        for row in rows:
            if matches(row):
                removed.append(row)
            else:
                kept.append(row)
        self._db.rows[self._name] = kept
        self._db.deleted.setdefault(self._name, []).extend(removed)
        return _Result(removed)


class _ScopedDB:
    def __init__(self, rows, fail_tables=()):
        self.rows = {name: list(table_rows) for name, table_rows in rows.items()}
        self.fail_tables = set(fail_tables)
        self.deleted = {}

    def table(self, name):
        return _ScopedQuery(self, name)


def test_workflow_purge_removes_target_tenant_only():
    db = _ScopedDB(
        rows={
            "tenants": [
                {"id": "t1", "stripe_customer_id": None},
                {"id": "t2", "stripe_customer_id": None},
            ],
            "os_workflow_steps": [
                {"id": "s1", "client_id": "t1", "workflow_id": "w1"},
                {"id": "s2", "client_id": "t2", "workflow_id": "w2"},
            ],
            "os_workflows": [
                {"id": "w1", "client_id": "t1"},
                {"id": "w2", "client_id": "t2"},
            ],
        }
    )
    report = delete_tenant_account(db, "t1")
    assert "os_workflow_steps" not in report.tables_skipped
    assert "os_workflows" not in report.tables_skipped
    assert db.rows["os_workflow_steps"] == [
        {"id": "s2", "client_id": "t2", "workflow_id": "w2"}
    ]
    assert db.rows["os_workflows"] == [{"id": "w2", "client_id": "t2"}]
    assert db.rows["tenants"] == [{"id": "t2", "stripe_customer_id": None}]
    removed_steps = [row["id"] for row in db.deleted["os_workflow_steps"]]
    removed_workflows = [row["id"] for row in db.deleted["os_workflows"]]
    assert removed_steps == ["s1"]
    assert removed_workflows == ["w1"]
    assert db.deleted["os_workflow_steps"]
    # Child delete is recorded before the parent delete.
    assert list(db.deleted).index("os_workflow_steps") < list(db.deleted).index(
        "os_workflows"
    )


def test_workflow_table_failure_is_reported_and_rerun_is_safe():
    db = _ScopedDB(
        rows={
            "tenants": [{"id": "t1", "stripe_customer_id": None}],
            "os_workflow_steps": [{"id": "s1", "client_id": "t1"}],
            "os_workflows": [{"id": "w1", "client_id": "t1"}],
        },
        fail_tables={"os_workflows"},
    )
    first = delete_tenant_account(db, "t1")
    assert "os_workflows" in first.tables_skipped
    assert "os_workflow_steps" not in first.tables_skipped
    assert db.rows["os_workflow_steps"] == []
    assert db.rows["os_workflows"] == [{"id": "w1", "client_id": "t1"}]
    assert first.tenant_row_deleted is True

    db.fail_tables.clear()
    second = delete_tenant_account(db, "t1")
    assert "os_workflows" not in second.tables_skipped
    assert db.rows["os_workflows"] == []
    assert second.tenant_row_deleted is False


def test_table_list_covers_all_client_id_data_tables():
    """Every data-bearing client_id table from tenant_scope must be purged.

    'tenants' is deleted separately; 'os_graph_edges' rides FK cascade but is
    listed anyway. If this fails you added a tenant table without adding it
    to TENANT_DATA_TABLES — GDPR deletion would silently miss it.
    """
    expected = set(_TENANT_COLUMN_OVERRIDES) - {"tenants"}
    missing = expected - set(TENANT_DATA_TABLES)
    assert not missing, f"client_id tables missing from GDPR purge list: {missing}"
