"""Shared fake-supabase test helpers (audit 2026-07-22 M1).

test_suite_round3/4/5/6.py and test_workforce_round2.py each carried an
identical copy of these four helpers; a behavior tweak meant five edits.
One module, imported everywhere. The recording sink keeps the same shape
tests already assert on: (table, method, args) tuples.
"""

import asyncio
from unittest.mock import MagicMock


def run(coro):
    """Run a coroutine on a fresh event loop (sync test entrypoint)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Result:
    """Mimics postgrest's APIResponse: .data rows plus optional .count."""

    def __init__(self, data, count=0):
        self.data = data
        self.count = count


class Query:
    """Chainable query recorder - every method call lands in the sink as
    (table, method, args); .execute() returns the preloaded rows."""

    def __init__(self, rows, sink, table):
        self._rows = rows
        self._sink = sink
        self._table = table

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((self._table, name, args))
            if name == "execute":
                return Result(self._rows)
            return self

        return _method


def db(rows_by_table, sink=None):
    """Fake supabase client: db.table(name) yields a Query over the fixture
    rows for that table. Inspect db._sink for the recorded call log."""
    sink = sink if sink is not None else []
    client = MagicMock()
    client.table.side_effect = lambda name: Query(
        rows_by_table.get(name, []), sink, name
    )
    client._sink = sink
    return client
