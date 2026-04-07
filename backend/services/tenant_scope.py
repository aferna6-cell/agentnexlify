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


def tenant_update(db: Any, table_name: str, tenant_id: str, values: Mapping[str, Any]) -> Any:
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


def tenant_upsert(db: Any, table_name: str, tenant_id: str, rows: Any, **upsert_kwargs: Any) -> Any:
    """Start an upsert query after injecting and validating tenant ownership."""
    return db.table(table_name).upsert(
        _scope_insert_rows(table_name, tenant_id, rows),
        **upsert_kwargs,
    )


def _scope_insert_rows(table_name: str, tenant_id: str, rows: Any) -> Any:
    scope_column = tenant_scope_column(table_name)

    if isinstance(rows, Mapping):
        return _scope_insert_row(scope_column, tenant_id, rows)

    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        return [_scope_insert_row(scope_column, tenant_id, row) for row in rows]

    raise TypeError("tenant_insert rows must be a mapping or sequence of mappings")


def _scope_insert_row(scope_column: str, tenant_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise TypeError("tenant_insert row items must be mappings")

    scoped = deepcopy(dict(row))
    if scope_column in scoped and scoped[scope_column] != tenant_id:
        raise TenantScopeError(f"Refusing to insert row for another tenant via {scope_column}")

    scoped[scope_column] = tenant_id
    return scoped
