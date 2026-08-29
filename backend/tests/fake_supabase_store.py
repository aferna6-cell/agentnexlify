"""A stateful fake Supabase client for tests that need real query semantics.

``backend/tests/fake_supabase.py`` returns preloaded rows whatever the filters
are, which is right for mapper tests. The action layer's guarantees are about
*conditional* writes — "move this row out of pending_approval only if it is
still pending" is what makes approval at-most-once — so testing them needs a
fake that actually stores rows and honours ``.eq()`` on updates.

Supports the subset the code under test uses: ``select``/``insert``/``update``
with ``eq``, ``limit``, ``order`` and ``execute``.
"""

import copy


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store, table, op, payload=None):
        self._store = store
        self._table = table
        self._op = op
        self._payload = payload
        self._filters = []
        self._limit = None
        self._order = None
        self._desc = False

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, column, desc=False):
        self._order = column
        self._desc = desc
        return self

    def _matches(self, row):
        return all(row.get(col) == value for col, value in self._filters)

    def execute(self):
        rows = self._store.setdefault(self._table, [])

        if self._op == "insert":
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            added = [copy.deepcopy(r) for r in payload]
            rows.extend(added)
            return _Result([copy.deepcopy(r) for r in added])

        if self._op == "update":
            touched = []
            for row in rows:
                if self._matches(row):
                    row.update(copy.deepcopy(self._payload))
                    touched.append(copy.deepcopy(row))
            return _Result(touched)

        selected = [copy.deepcopy(r) for r in rows if self._matches(r)]
        if self._order:
            selected.sort(key=lambda r: r.get(self._order) or "", reverse=self._desc)
        if self._limit is not None:
            selected = selected[: self._limit]
        return _Result(selected)


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def select(self, _columns="*", **_kwargs):
        return _Query(self._store, self._name, "select")

    def insert(self, rows):
        return _Query(self._store, self._name, "insert", rows)

    def update(self, values):
        return _Query(self._store, self._name, "update", values)


class FakeSupabase:
    """``db.table(name)`` over an in-memory ``{table: [rows]}`` store."""

    def __init__(self, rows_by_table=None):
        self.store = {k: [copy.deepcopy(r) for r in v] for k, v in (rows_by_table or {}).items()}

    def table(self, name):
        return _Table(self.store, name)

    def rows(self, name):
        """The current rows of one table (a copy)."""
        return [copy.deepcopy(r) for r in self.store.get(name, [])]
