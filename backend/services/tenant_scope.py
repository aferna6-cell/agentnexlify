"""Tenant-scoped Supabase query helpers.

The app uses a Supabase service-role client, so RLS is not the primary guardrail.
These helpers keep tenant filters/inserts consistent at the callsite.
"""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


class TenantScopeError(ValueError):
    """Raised when a caller tries to cross tenant boundaries."""


_TENANT_COLUMN_OVERRIDES = {
    "conversations": "client_id",
    "leads": "client_id",
    "tenants": "id",
    "tenant_integrations": "client_id",
    "os_threads": "client_id",
    "os_messages": "client_id",
    "os_agent_runs": "client_id",
    "os_memory_entries": "client_id",
    "os_backlog_requests": "client_id",
    "os_tenant_usage": "client_id",
    "os_action_runs": "client_id",
    "os_sync_state": "client_id",
    "os_outbound_log": "client_id",
    "os_routing_decision": "client_id",
    "os_model_call_log": "client_id",
    "os_graph_nodes": "client_id",
    "os_graph_edges": "client_id",
    "os_uploads": "client_id",
    "os_scheduled_tasks": "client_id",
}


def tenant_scope_column(table_name: str) -> str:
    """Return the tenant ownership column for a table."""
    return _TENANT_COLUMN_OVERRIDES.get(table_name, "tenant_id")


def tenant_select(
    db: Any,
    table_name: str,
    tenant_id: str,
    columns: str = "*",
    **select_kwargs: Any,
) -> Any:
    """Start a select query scoped to the tenant."""
    return (
        db.table(table_name)
        .select(columns, **select_kwargs)
        .eq(tenant_scope_column(table_name), tenant_id)
    )


def tenant_update(
    db: Any, table_name: str, tenant_id: str, values: Mapping[str, Any]
) -> Any:
    """Start an update query scoped to the tenant."""
    return (
        db.table(table_name)
        .update(dict(values))
        .eq(tenant_scope_column(table_name), tenant_id)
    )


def tenant_delete(db: Any, table_name: str, tenant_id: str) -> Any:
    """Start a delete query scoped to the tenant."""
    return db.table(table_name).delete().eq(tenant_scope_column(table_name), tenant_id)


def tenant_insert(db: Any, table_name: str, tenant_id: str, rows: Any) -> Any:
    """Start an insert query after injecting and validating tenant ownership."""
    return db.table(table_name).insert(_scope_insert_rows(table_name, tenant_id, rows))


def tenant_upsert(
    db: Any, table_name: str, tenant_id: str, rows: Any, **upsert_kwargs: Any
) -> Any:
    """Start an upsert query after injecting and validating tenant ownership."""
    return db.table(table_name).upsert(
        _scope_insert_rows(table_name, tenant_id, rows),
        **upsert_kwargs,
    )


class TenantScopedTable:
    """Small table facade that scopes every tenant-owned operation."""

    def __init__(self, db: Any, table_name: str, tenant_id: str):
        self.db = db
        self.table_name = table_name
        self.tenant_id = tenant_id

    def select(self, columns: str = "*", **select_kwargs: Any) -> Any:
        return tenant_select(
            self.db, self.table_name, self.tenant_id, columns, **select_kwargs
        )

    def update(self, values: Mapping[str, Any]) -> Any:
        return tenant_update(self.db, self.table_name, self.tenant_id, values)

    def delete(self) -> Any:
        return tenant_delete(self.db, self.table_name, self.tenant_id)

    def insert(self, rows: Any) -> Any:
        return tenant_insert(self.db, self.table_name, self.tenant_id, rows)

    def upsert(self, rows: Any, **upsert_kwargs: Any) -> Any:
        return tenant_upsert(
            self.db, self.table_name, self.tenant_id, rows, **upsert_kwargs
        )


def tenant_table(db: Any, table_name: str, tenant_id: str) -> TenantScopedTable:
    """Return a table facade that injects the tenant scope automatically."""
    return TenantScopedTable(db, table_name, tenant_id)


class TenantScopedClient:
    """Tenant-scoped client facade for request-path database access."""

    def __init__(self, db: Any, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def table(self, table_name: str) -> TenantScopedTable:
        return tenant_table(self.db, table_name, self.tenant_id)

    def rpc(self, *args: Any, **kwargs: Any) -> Any:
        return self.db.rpc(*args, **kwargs)

    @property
    def storage(self) -> Any:
        return self.db.storage


def tenant_client(db: Any, tenant_id: str) -> TenantScopedClient:
    """Return a client facade that scopes table operations to a tenant."""
    return TenantScopedClient(db, tenant_id)


def _scope_insert_rows(table_name: str, tenant_id: str, rows: Any) -> Any:
    scope_column = tenant_scope_column(table_name)

    if isinstance(rows, Mapping):
        return _scope_insert_row(scope_column, tenant_id, rows)

    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        return [_scope_insert_row(scope_column, tenant_id, row) for row in rows]

    raise TypeError("tenant_insert rows must be a mapping or sequence of mappings")


def _scope_insert_row(
    scope_column: str, tenant_id: str, row: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise TypeError("tenant_insert row items must be mappings")

    scoped = deepcopy(dict(row))
    if scope_column in scoped and scoped[scope_column] != tenant_id:
        raise TenantScopeError(
            f"Refusing to insert row for another tenant via {scope_column}"
        )

    scoped[scope_column] = tenant_id
    return scoped
