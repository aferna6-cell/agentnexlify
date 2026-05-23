"""Chainable fake Supabase client for service-level tests.

Service modules accept ``db: Any`` and use the Supabase fluent builder
(``db.table("X").select(...).eq(...).execute()``). Tests pass a
``FakeSupabase`` so the real Supabase singleton isn't touched and the
extracted service code is exercised directly — that lifts changed-lines
coverage that's bypassed by router-scope mocks.

Supports the chain methods used across the extracted services:
``select, insert, update, delete, eq, neq, in_, gt, gte, lt, lte,
order, limit, range, or_``, plus ``not_.is_``. ``execute()`` returns a
``FakeResult`` carrying ``.data`` and ``.count``.

Configure responses per table via ``configure(table, data=..., count=...)``
or per (table, op) via ``configure_op``.
"""

from typing import Any


class FakeResult:
    def __init__(self, data: list[dict] | None = None, count: int | None = None):
        self.data = data or []
        self.count = count


class _NotChain:
    def __init__(self, parent: "FakeQuery"):
        self._parent = parent

    def is_(self, *_args, **_kwargs) -> "FakeQuery":
        return self._parent


class FakeQuery:
    def __init__(self, parent: "FakeSupabase", table: str, op: str = "select"):
        self._parent = parent
        self._table = table
        self._op = op
        self._payload: Any = None
        self.not_ = _NotChain(self)

    def select(self, *_args, **_kwargs) -> "FakeQuery":
        self._op = "select"
        return self

    def insert(self, payload: Any) -> "FakeQuery":
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: Any) -> "FakeQuery":
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeQuery":
        self._op = "delete"
        return self

    def eq(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def neq(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def in_(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def gt(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def gte(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def lt(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def lte(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def order(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def limit(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def range(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def or_(self, *_args, **_kwargs) -> "FakeQuery":
        return self

    def execute(self) -> FakeResult:
        key = (self._table, self._op)
        if key in self._parent._raises:
            raise self._parent._raises[key]
        if self._table in self._parent._raises_table:
            raise self._parent._raises_table[self._table]
        if key in self._parent._responses_op:
            cfg = self._parent._responses_op[key]
            if self._op == "insert" and cfg.get("echo_payload"):
                payload = self._payload if isinstance(self._payload, list) else [self._payload]
                return FakeResult(data=payload, count=len(payload))
            return FakeResult(data=cfg.get("data"), count=cfg.get("count"))
        if self._table in self._parent._responses:
            cfg = self._parent._responses[self._table]
            if self._op == "insert" and cfg.get("echo_payload"):
                payload = self._payload if isinstance(self._payload, list) else [self._payload]
                return FakeResult(data=payload, count=len(payload))
            return FakeResult(data=cfg.get("data"), count=cfg.get("count"))
        return FakeResult(data=[], count=0)


class FakeSupabase:
    def __init__(self):
        self._responses: dict[str, dict] = {}
        self._responses_op: dict[tuple[str, str], dict] = {}
        self._raises: dict[tuple[str, str], Exception] = {}
        self._raises_table: dict[str, Exception] = {}

    def configure(self, table: str, *, data: list | None = None, count: int | None = None, echo_payload: bool = False) -> "FakeSupabase":
        self._responses[table] = {"data": data, "count": count, "echo_payload": echo_payload}
        return self

    def configure_op(self, table: str, op: str, *, data: list | None = None, count: int | None = None, echo_payload: bool = False) -> "FakeSupabase":
        self._responses_op[(table, op)] = {"data": data, "count": count, "echo_payload": echo_payload}
        return self

    def raise_on(self, table: str, op: str | None = None, exc: Exception | None = None) -> "FakeSupabase":
        exc = exc or RuntimeError(f"forced failure on {table}/{op or 'any'}")
        if op:
            self._raises[(table, op)] = exc
        else:
            self._raises_table[table] = exc
        return self

    def table(self, table: str) -> FakeQuery:
        return FakeQuery(self, table)
