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


def test_table_list_covers_all_client_id_data_tables():
    """Every data-bearing client_id table from tenant_scope must be purged.

    'tenants' is deleted separately; 'os_graph_edges' rides FK cascade but is
    listed anyway. If this fails you added a tenant table without adding it
    to TENANT_DATA_TABLES — GDPR deletion would silently miss it.
    """
    expected = set(_TENANT_COLUMN_OVERRIDES) - {"tenants"}
    missing = expected - set(TENANT_DATA_TABLES)
    assert not missing, f"client_id tables missing from GDPR purge list: {missing}"
