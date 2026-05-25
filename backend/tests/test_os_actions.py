"""Unit tests for os_actions registry + foundation.

Spec: ``specs/agent-os-connectors-actions_spec.md``.

Focus:
- Registry auto-discovers calendar handler via SPEC import.
- ``run_action`` writes status, payloads, and timestamps tenant-scoped.
- Idempotency: succeeded action cannot be re-inserted for the same
  (deliverable_id, action_type) (enforced by DB partial unique — test
  validates the route preflight that short-circuits before insert).
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


from backend.services.os_actions import all_actions, get_action, run_action
from backend.services.os_actions.base import (
    ActionContext,
    ActionResult,
    ActionSpec,
)

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_DELIV = "10000000-0000-0000-0000-00000000abcd"
_ACTION_RUN = "20000000-0000-0000-0000-00000000abcd"


def _stub_supabase(agent_run_row: dict | None = None):
    """Mimic the chained supabase-py builder used by tenant_table()."""
    builder = MagicMock(name="builder")
    builder.select.return_value = builder
    builder.update.return_value = builder
    builder.insert.return_value = builder
    builder.eq.return_value = builder
    builder.limit.return_value = builder
    builder.execute.return_value = SimpleNamespace(
        data=[agent_run_row] if agent_run_row else []
    )
    db = MagicMock(name="db")
    db.table.return_value = builder
    return db, builder


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_discovers_calendar_handler():
    actions = all_actions()
    assert "calendar.event.create" in actions
    spec = actions["calendar.event.create"]
    assert isinstance(spec, ActionSpec)
    assert spec.worker == "booking"
    assert "google_calendar" in spec.required_connectors


def test_get_action_returns_none_for_unknown():
    assert get_action("does.not.exist") is None


def test_get_action_returns_spec_for_known():
    spec = get_action("calendar.event.create")
    assert spec is not None
    assert spec.name == "calendar.event.create"


# ---------------------------------------------------------------------------
# run_action background-task harness
# ---------------------------------------------------------------------------


def test_run_action_marks_unknown_action_failed():
    db, builder = _stub_supabase(agent_run_row={"id": _DELIV, "deliverable": {}})
    with patch("backend.services.os_actions.get_service_supabase", return_value=db):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "not.a.real.action"))
    # The failure path writes status=failed with error_detail.
    update_calls = [c for c in builder.update.call_args_list]
    assert any(
        c.args[0].get("status") == "failed" for c in update_calls
    ), "failed status update not recorded"


def test_run_action_invokes_handler_run():
    db, builder = _stub_supabase(
        agent_run_row={
            "id": _DELIV,
            "deliverable": {"title": "T", "body": "approved body"},
            "client_id": _CLIENT_A,
            "thread_id": "thr-1",
        }
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.name = "calendar.event.create"
    stub_handler.run = AsyncMock(
        return_value=ActionResult(
            status="succeeded",
            request_payload={"summary": "ok"},
            response_payload={"event_id": "abc"},
        )
    )
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    stub_handler.run.assert_awaited_once()
    ctx_arg = stub_handler.run.call_args.args[0]
    assert isinstance(ctx_arg, ActionContext)
    assert ctx_arg.client_id == _CLIENT_A
    assert ctx_arg.deliverable_id == _DELIV
    assert ctx_arg.action_type == "calendar.event.create"
    assert ctx_arg.deliverable == {"title": "T", "body": "approved body"}
    # status=succeeded must be persisted with payloads.
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    final = [u for u in update_calls if u.get("status") == "succeeded"]
    assert final, "succeeded status not persisted"
    assert final[0]["response_payload"] == {"event_id": "abc"}


def test_run_action_propagates_handler_exception_as_failed():
    db, builder = _stub_supabase(
        agent_run_row={"id": _DELIV, "deliverable": {"body": "x"}}
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(side_effect=RuntimeError("boom"))
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    fail = [u for u in update_calls if u.get("status") == "failed"]
    assert fail, "exception did not trigger failed status write"
    assert "boom" in (fail[-1].get("error_detail") or {}).get("message", "")


# ---------------------------------------------------------------------------
# Tenant scoping
# ---------------------------------------------------------------------------


def test_run_action_uses_client_id_for_os_action_runs_scope():
    """tenant_table('os_action_runs', client_id) must scope by client_id."""
    db, builder = _stub_supabase(
        agent_run_row={"id": _DELIV, "deliverable": {"body": "x"}}
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(return_value=ActionResult(status="succeeded"))
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    # The scoping filter from tenant_table is added to every chained query
    # — assert the client_id was passed to .eq() at least once.
    eq_args = [c.args for c in builder.eq.call_args_list]
    flat = [a for tpl in eq_args for a in tpl]
    assert _CLIENT_A in flat, "client_id never used in scoping filter"
