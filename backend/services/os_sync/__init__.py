"""Agent OS sync registry — auto-discovers every sync module here.

Drop a module in this package that defines a module-level ``SPEC: SyncSpec``
and it registers automatically. The scheduled tick (``run_due_syncs``) reads
``os_sync_state``, picks rows whose ``enabled=true`` and not currently
``running``, and dispatches the matching SyncSpec.

Cursor + status are persisted to ``os_sync_state`` per (client_id, source).
"""

import importlib
import logging
import pkgutil

from backend.models.database import get_service_supabase
from backend.services.os_sync.base import (
    SyncContext,
    SyncResult,
    SyncSpec,
    now_iso,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, SyncSpec] = {}
_DISCOVERED = False


def _discover() -> None:
    """Import every sync module once and collect its ``SPEC``."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package = importlib.import_module(__name__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name == "base" or info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{info.name}")
        except Exception:
            logger.exception("os_sync: failed to import module %s", info.name)
            continue
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, SyncSpec):
            _REGISTRY[spec.name] = spec
        else:
            logger.warning("os_sync: module %s has no SyncSpec SPEC", info.name)


def all_syncs() -> dict[str, SyncSpec]:
    _discover()
    return dict(_REGISTRY)


def get_sync(name: str) -> SyncSpec | None:
    _discover()
    return _REGISTRY.get(name)


def _load_state(db, client_id: str, source: str) -> dict | None:
    result = (
        tenant_table(db, "os_sync_state", client_id)
        .select("*")
        .eq("source", source)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _ensure_state(db, client_id: str, source: str) -> dict:
    """Return existing os_sync_state row or create one with defaults."""
    existing = _load_state(db, client_id, source)
    if existing:
        return existing
    created = (
        tenant_table(db, "os_sync_state", client_id)
        .insert(
            {
                "client_id": client_id,
                "source": source,
                "enabled": True,
                "status": "idle",
                "rows_seen_total": 0,
            }
        )
        .execute()
    )
    return created.data[0]


async def run_sync(
    client_id: str,
    source: str,
    backfill: bool = False,
) -> SyncResult:
    """Run one sync end to end. Writes status + cursor back to os_sync_state.

    Returns the SyncResult so callers (scheduler tick, run-now route) can
    surface the outcome. Every failure is caught and recorded as ``error``.
    """
    try:
        db = get_service_supabase()
        sync_table = tenant_table(db, "os_sync_state", client_id)
    except Exception:
        logger.exception(
            "os_sync: could not open db client_id=%s source=%s", client_id, source
        )
        return SyncResult(status="error", error_detail="db_unavailable")

    state_row = _ensure_state(db, client_id, source)
    state_id = state_row["id"]

    spec = get_sync(source)
    if spec is None:
        err = f"unknown sync source '{source}'"
        sync_table.update(
            {
                "status": "error",
                "last_run_at": now_iso(),
                "last_error": err,
                "updated_at": now_iso(),
            }
        ).eq("id", state_id).execute()
        return SyncResult(status="error", error_detail=err)

    if not state_row.get("enabled", True):
        return SyncResult(status="ok", error_detail="disabled")

    sync_table.update(
        {"status": "running", "last_run_at": now_iso(), "updated_at": now_iso()}
    ).eq("id", state_id).execute()

    try:
        ctx = SyncContext(
            db=db,
            client_id=client_id,
            source=source,
            state_row=state_row,
            backfill=backfill,
        )
        result = await spec.run(ctx)
    except Exception as e:
        logger.exception(
            "os_sync: handler crashed client_id=%s source=%s", client_id, source
        )
        sync_table.update(
            {
                "status": "error",
                "last_error": str(e)[:500],
                "updated_at": now_iso(),
            }
        ).eq("id", state_id).execute()
        return SyncResult(status="error", error_detail=str(e)[:500])

    update_fields: dict = {
        "status": "error" if result.status == "error" else "idle",
        "last_error": result.error_detail,
        "rows_seen_total": (state_row.get("rows_seen_total") or 0) + result.rows_seen,
        "updated_at": now_iso(),
    }
    if result.status == "ok":
        update_fields["last_success_at"] = now_iso()
    if result.new_cursor is not None:
        update_fields["last_seen_cursor"] = result.new_cursor

    sync_table.update(update_fields).eq("id", state_id).execute()
    return result


async def run_due_syncs(client_id: str | None = None) -> list[dict]:
    """Scheduler hook: dispatch every enabled+idle sync for tenant(s).

    If ``client_id`` is None, scans every enabled sync row across all tenants.
    Returns a list of {client_id, source, status, rows_seen} dicts for logging.
    """
    db = get_service_supabase()
    builder = db.table("os_sync_state").select("client_id, source, enabled, status")
    builder = builder.eq("enabled", True).neq("status", "running")
    if client_id:
        builder = builder.eq("client_id", client_id)
    rows = builder.execute().data or []

    outcomes: list[dict] = []
    for row in rows:
        result = await run_sync(row["client_id"], row["source"])
        outcomes.append(
            {
                "client_id": row["client_id"],
                "source": row["source"],
                "status": result.status,
                "rows_seen": result.rows_seen,
            }
        )
    return outcomes


__all__ = [
    "SyncContext",
    "SyncResult",
    "SyncSpec",
    "all_syncs",
    "get_sync",
    "run_sync",
    "run_due_syncs",
    "now_iso",
]
