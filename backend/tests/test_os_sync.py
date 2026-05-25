"""Unit tests for os_sync registry + foundation.

Spec: agent-os-rehaul (migration 127 + backend/services/os_sync/).

Focus:
- Registry auto-discovers leads handler via SPEC import.
- ``run_sync`` writes status, cursor, and rows_seen_total tenant-scoped.
- ``run_sync`` short-circuits when state_row.enabled is False.
- Unknown source returns status='error' and persists last_error.
- Handler exception is caught and recorded as status='error'.
- Tenant scope uses client_id for os_sync_state.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


from backend.services.os_sync import all_syncs, get_sync, run_sync
from backend.services.os_sync.base import (
    SyncContext,
    SyncResult,
    SyncSpec,
)

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_STATE_ID = "30000000-0000-0000-0000-00000000abcd"


def _stub_supabase(state_row: dict | None = None):
    """Mimic the chained supabase-py builder used by tenant_table()."""
    builder = MagicMock(name="builder")
    builder.select.return_value = builder
    builder.update.return_value = builder
    builder.insert.return_value = builder
    builder.delete.return_value = builder
    builder.eq.return_value = builder
    builder.gt.return_value = builder
    builder.limit.return_value = builder
    builder.order.return_value = builder
    builder.execute.return_value = SimpleNamespace(
        data=[state_row] if state_row else []
    )
    db = MagicMock(name="db")
    db.table.return_value = builder
    return db, builder


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_discovers_leads_handler():
    syncs = all_syncs()
    assert "leads" in syncs
    spec = syncs["leads"]
    assert isinstance(spec, SyncSpec)
    assert spec.name == "leads"
    assert callable(spec.run)


def test_get_sync_returns_none_for_unknown():
    assert get_sync("does.not.exist") is None


def test_get_sync_returns_spec_for_known():
    spec = get_sync("leads")
    assert spec is not None
    assert spec.name == "leads"


# ---------------------------------------------------------------------------
# run_sync background-task harness
# ---------------------------------------------------------------------------


def test_run_sync_marks_unknown_source_error():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "not.a.real.source",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    with patch("backend.services.os_sync.get_service_supabase", return_value=db):
        result = asyncio.run(run_sync(_CLIENT_A, "not.a.real.source"))
    assert result.status == "error"
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    assert any(
        u.get("status") == "error" for u in update_calls
    ), "error status update not recorded"


def test_run_sync_invokes_handler_run_and_persists_cursor():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
        "last_seen_cursor": None,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.name = "leads"
    stub_handler.run = AsyncMock(
        return_value=SyncResult(
            status="ok",
            rows_seen=5,
            new_cursor="2026-05-25T12:00:00+00:00",
        )
    )
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        result = asyncio.run(run_sync(_CLIENT_A, "leads"))
    assert result.status == "ok"
    assert result.rows_seen == 5
    stub_handler.run.assert_awaited_once()
    ctx_arg = stub_handler.run.call_args.args[0]
    assert isinstance(ctx_arg, SyncContext)
    assert ctx_arg.client_id == _CLIENT_A
    assert ctx_arg.source == "leads"
    assert ctx_arg.backfill is False
    # Cursor + rows_seen_total must persist.
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    final = [u for u in update_calls if u.get("status") == "idle"]
    assert final, "idle status not persisted on success"
    last = final[-1]
    assert last["last_seen_cursor"] == "2026-05-25T12:00:00+00:00"
    assert last["rows_seen_total"] == 5


def test_run_sync_propagates_handler_exception_as_error():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        result = asyncio.run(run_sync(_CLIENT_A, "leads"))
    assert result.status == "error"
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    fail = [u for u in update_calls if u.get("status") == "error"]
    assert fail, "exception did not trigger error status write"
    assert "boom" in (fail[-1].get("last_error") or "")


def test_run_sync_propagates_backfill_flag():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
        "last_seen_cursor": "2026-05-01T00:00:00+00:00",
    }
    db, _ = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(return_value=SyncResult(status="ok"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        asyncio.run(run_sync(_CLIENT_A, "leads", backfill=True))
    ctx_arg = stub_handler.run.call_args.args[0]
    assert ctx_arg.backfill is True


# ---------------------------------------------------------------------------
# Tenant scoping
# ---------------------------------------------------------------------------


def test_run_sync_uses_client_id_for_os_sync_state_scope():
    """tenant_table('os_sync_state', client_id) must scope by client_id."""
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(return_value=SyncResult(status="ok"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        asyncio.run(run_sync(_CLIENT_A, "leads"))
    # tenant_table injects .eq(client_id, _CLIENT_A) on every chained query.
    eq_args = [c.args for c in builder.eq.call_args_list]
    flat = [a for tpl in eq_args for a in tpl]
    assert _CLIENT_A in flat, "client_id never used in scoping filter"


# ---------------------------------------------------------------------------
# leads SPEC contract
# ---------------------------------------------------------------------------


def test_leads_spec_metadata():
    from backend.services.os_sync.leads import SPEC

    assert SPEC.name == "leads"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == []


def test_leads_summarize_handles_minimal_row():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead({"id": "x", "name": "Alice"})
    assert "Alice" in text
    assert text.startswith("Lead:")


def test_leads_summarize_handles_unnamed_row():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead({"id": "x"})
    assert "Unnamed lead" in text


def test_leads_summarize_includes_status_and_temperature():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead(
        {
            "id": "x",
            "name": "Bob",
            "status": "qualified",
            "lead_temperature": "hot",
            "lead_score": 87,
        }
    )
    assert "status=qualified" in text
    assert "temperature=hot" in text
    assert "score=87" in text
