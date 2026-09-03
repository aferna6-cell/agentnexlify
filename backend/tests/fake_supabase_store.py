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


class _Rpc:
    def __init__(self, db, name, params):
        self._db = db
        self._name = name
        self._params = params

    def execute(self):
        if self._name != "create_os_workflow":
            raise RuntimeError(f"unsupported rpc {self._name!r}")
        return _Result([self._db._create_os_workflow(self._params)])


class FakeSupabase:
    """``db.table(name)`` over an in-memory ``{table: [rows]}`` store."""

    def __init__(self, rows_by_table=None):
        self.store = {k: [copy.deepcopy(r) for r in v] for k, v in (rows_by_table or {}).items()}
        # When set, create_os_workflow raises after validating inputs but
        # before committing — proves the Python caller sees atomic failure.
        self.fail_create_os_workflow = False

    def table(self, name):
        return _Table(self.store, name)

    def rpc(self, name, params):
        return _Rpc(self, name, params)

    def rows(self, name):
        """The current rows of one table (a copy)."""
        return [copy.deepcopy(r) for r in self.store.get(name, [])]

    def _create_os_workflow(self, params):
        """Atomic fake of Postgres create_os_workflow (no partial rows)."""
        import uuid
        from datetime import datetime, timezone

        client_id = params.get("p_client_id")
        owner_goal = params.get("p_owner_goal")
        steps = params.get("p_steps")
        workflow_id = params.get("p_workflow_id") or str(uuid.uuid4())
        if not client_id:
            raise RuntimeError("client_id required")
        if not owner_goal or not str(owner_goal).strip():
            raise RuntimeError("owner_goal required")
        if not isinstance(steps, list):
            raise RuntimeError("steps must be a json array")

        now = datetime.now(timezone.utc).isoformat()
        workflows = self.store.setdefault("os_workflows", [])
        step_rows = self.store.setdefault("os_workflow_steps", [])
        if any(w.get("id") == workflow_id for w in workflows):
            raise RuntimeError(f"workflow {workflow_id} already exists")

        prepared = []
        seen = set()
        for index, raw in enumerate(steps):
            step_id = str(raw.get("id") or uuid.uuid4())
            if step_id in seen or any(s.get("id") == step_id for s in step_rows):
                raise RuntimeError(f"step {step_id} already exists")
            if not raw.get("description"):
                raise RuntimeError("description required")
            seen.add(step_id)
            prepared.append(
                {
                    "id": step_id,
                    "workflow_id": workflow_id,
                    "client_id": client_id,
                    "ordinal": int(raw.get("ordinal", index)),
                    "description": str(raw["description"]),
                    "dependencies": list(raw.get("dependencies") or []),
                    "department": raw.get("department"),
                    "tool_intent": copy.deepcopy(raw.get("tool_intent")),
                    "state": str(raw.get("state") or "planned"),
                    "risk_level": int(raw.get("risk_level", 1)),
                    "execution_id": raw.get("execution_id"),
                    "verification_state": raw.get("verification_state"),
                    "error": raw.get("error"),
                    "retry_count": int(raw.get("retry_count", 0)),
                    "max_retries": int(raw.get("max_retries", 2)),
                    "row_version": 1,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        if self.fail_create_os_workflow:
            raise RuntimeError("simulated step insert failure")

        workflow = {
            "id": workflow_id,
            "client_id": client_id,
            "owner_goal": owner_goal,
            "status": "planned",
            "row_version": 1,
            "created_at": now,
            "updated_at": now,
        }
        workflows.append(workflow)
        step_rows.extend(prepared)
        out = copy.deepcopy(workflow)
        out["steps"] = copy.deepcopy(prepared)
        return out

    def insert_step_enforcing_tenant_fk(self, row):
        """Direct insert used by tests to prove composite tenant FK semantics."""
        workflows = self.store.get("os_workflows", [])
        parent = next(
            (
                w
                for w in workflows
                if w.get("id") == row.get("workflow_id")
                and w.get("client_id") == row.get("client_id")
            ),
            None,
        )
        if parent is None:
            raise RuntimeError(
                "os_workflow_steps_workflow_client_fkey violation: "
                "(workflow_id, client_id) not found in os_workflows"
            )
        self.store.setdefault("os_workflow_steps", []).append(copy.deepcopy(row))
        return copy.deepcopy(row)
