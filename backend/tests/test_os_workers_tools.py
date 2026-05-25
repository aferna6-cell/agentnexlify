"""Unit tests for WorkerTools — read-only tenant-scoped data access for OS workers.

Spec: ``specs/agent-os-worker-tools_spec.md`` (build order, schema reminders).

Focus: tenant isolation. Every method must filter by ``client_id`` (or the
canonical ``tenant_id`` column for ``appointments`` / ``chat_messages``) so a
worker run for tenant A cannot ever see tenant B's rows. We assert this by
inspecting the chained query the tool builds against a MagicMock supabase
client.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.services.os_workers.tools import WorkerTools

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_CLIENT_B = "00000000-0000-0000-0000-00000000000b"


def _run(coro):
    return (
        asyncio.get_event_loop().run_until_complete(coro)
        if False
        else asyncio.run(coro)
    )


def _stub_supabase(rows: list[dict] | None = None):
    """Return a MagicMock that mimics the chained supabase-py builder API.

    Every chained call (``.select().eq().limit().execute()``) returns the same
    MagicMock so callers can assert on the final ``.execute().data`` row set.
    """
    builder = MagicMock(name="builder")
    builder.select.return_value = builder
    builder.eq.return_value = builder
    builder.neq.return_value = builder
    builder.gte.return_value = builder
    builder.lte.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.execute.return_value = SimpleNamespace(data=rows or [])
    db = MagicMock(name="db")
    db.table.return_value = builder
    return db, builder


# ---------------------------------------------------------------------------
# Construction / immutability
# ---------------------------------------------------------------------------


def test_worker_tools_is_frozen():
    db, _ = _stub_supabase()
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    with pytest.raises(Exception):
        tools.client_id = _CLIENT_B  # type: ignore[misc]


# ---------------------------------------------------------------------------
# recent_leads — must scope by client_id, never tenant_id
# ---------------------------------------------------------------------------


def test_recent_leads_scopes_by_client_id():
    rows = [{"id": "lead-1", "name": "Alice"}]
    db, builder = _stub_supabase(rows)
    tools = WorkerTools(db=db, client_id=_CLIENT_A)

    out = _run(tools.recent_leads(days=7, limit=5))

    assert out == rows
    db.table.assert_called_with("leads")
    eq_calls = [c.args for c in builder.eq.call_args_list]
    assert (
        "client_id",
        _CLIENT_A,
    ) in eq_calls, "leads must be scoped by client_id, not tenant_id"
    for call_args in eq_calls:
        assert call_args[0] != "tenant_id", "tenant_id is NEVER correct on leads"


def test_recent_leads_returns_empty_on_db_error():
    db = MagicMock()
    db.table.side_effect = RuntimeError("boom")
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.recent_leads(days=7, limit=5)) == []


def test_recent_leads_clamps_huge_limit():
    db, builder = _stub_supabase([])
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    _run(tools.recent_leads(days=30, limit=10_000_000))
    limit_calls = [c.args[0] for c in builder.limit.call_args_list]
    assert all(n <= 1000 for n in limit_calls), "HARD_LIMIT 1000 must be enforced"


# ---------------------------------------------------------------------------
# stale_leads — excludes closed + unsubscribed (real lead statuses)
# ---------------------------------------------------------------------------


def test_stale_leads_excludes_closed_and_unsubscribed():
    db, builder = _stub_supabase([])
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    _run(tools.stale_leads(days_since_last_touch=14, limit=10))
    neq_calls = [c.args for c in builder.neq.call_args_list]
    assert ("status", "closed") in neq_calls
    assert ("status", "unsubscribed") in neq_calls


# ---------------------------------------------------------------------------
# widget_conversation — scopes by client_id on conversations + chat_messages
# ---------------------------------------------------------------------------


def test_widget_conversation_returns_none_when_session_missing():
    db, _ = _stub_supabase([])
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.widget_conversation("bogus-session")) is None


def test_widget_conversation_returns_none_on_empty_session_id():
    db, _ = _stub_supabase()
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.widget_conversation("")) is None


# ---------------------------------------------------------------------------
# tenant_profile — joins tenants + widget_configs into one dict
# ---------------------------------------------------------------------------


def test_tenant_profile_merges_tenant_row_and_kb():
    db = MagicMock(name="db")

    tenants_builder = MagicMock(name="tenants")
    tenants_builder.select.return_value = tenants_builder
    tenants_builder.eq.return_value = tenants_builder
    tenants_builder.limit.return_value = tenants_builder
    tenants_builder.execute.return_value = SimpleNamespace(
        data=[{"id": _CLIENT_A, "business_name": "Acme", "timezone": "UTC"}]
    )

    widget_builder = MagicMock(name="widget_configs")
    widget_builder.select.return_value = widget_builder
    widget_builder.eq.return_value = widget_builder
    widget_builder.limit.return_value = widget_builder
    widget_builder.execute.return_value = SimpleNamespace(
        data=[{"knowledge_base": "Hours: 9-5", "custom_instructions": "Be terse."}]
    )

    def _route(name):
        if name == "tenants":
            return tenants_builder
        if name == "widget_configs":
            return widget_builder
        raise AssertionError(f"unexpected table {name}")

    db.table.side_effect = _route
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    profile = _run(tools.tenant_profile())

    assert profile["business_name"] == "Acme"
    assert profile["knowledge_base"] == "Hours: 9-5"
    assert profile["custom_instructions"] == "Be terse."
    eq_calls = [c.args for c in tenants_builder.eq.call_args_list]
    assert ("id", _CLIENT_A) in eq_calls


def test_tenant_profile_kb_empty_when_widget_row_missing():
    db = MagicMock(name="db")

    tenants_builder = MagicMock()
    tenants_builder.select.return_value = tenants_builder
    tenants_builder.eq.return_value = tenants_builder
    tenants_builder.limit.return_value = tenants_builder
    tenants_builder.execute.return_value = SimpleNamespace(
        data=[{"id": _CLIENT_A, "business_name": "Acme"}]
    )

    widget_builder = MagicMock()
    widget_builder.select.return_value = widget_builder
    widget_builder.eq.return_value = widget_builder
    widget_builder.limit.return_value = widget_builder
    widget_builder.execute.return_value = SimpleNamespace(data=[])

    def _route(name):
        return tenants_builder if name == "tenants" else widget_builder

    db.table.side_effect = _route
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    profile = _run(tools.tenant_profile())

    assert profile["knowledge_base"] == ""
    assert profile["custom_instructions"] == ""


def test_widget_knowledge_base_returns_string():
    db = MagicMock()
    tenants_builder = MagicMock()
    tenants_builder.select.return_value = tenants_builder
    tenants_builder.eq.return_value = tenants_builder
    tenants_builder.limit.return_value = tenants_builder
    tenants_builder.execute.return_value = SimpleNamespace(data=[])

    widget_builder = MagicMock()
    widget_builder.select.return_value = widget_builder
    widget_builder.eq.return_value = widget_builder
    widget_builder.limit.return_value = widget_builder
    widget_builder.execute.return_value = SimpleNamespace(
        data=[{"knowledge_base": "KB", "custom_instructions": ""}]
    )

    db.table.side_effect = lambda name: (
        tenants_builder if name == "tenants" else widget_builder
    )
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.widget_knowledge_base()) == "KB"


# ---------------------------------------------------------------------------
# search_memory — empty query short-circuits without DB call
# ---------------------------------------------------------------------------


def test_search_memory_empty_query_returns_empty_list_without_db():
    db = MagicMock()
    db.table.side_effect = AssertionError("must not hit db on empty query")
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.search_memory("", match_count=4)) == []


# ---------------------------------------------------------------------------
# lead_by_id — None on empty id, scoped by client_id otherwise
# ---------------------------------------------------------------------------


def test_lead_by_id_empty_returns_none():
    db = MagicMock()
    db.table.side_effect = AssertionError("must not hit db on empty id")
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    assert _run(tools.lead_by_id("")) is None


def test_lead_by_id_scopes_by_client_id():
    rows = [{"id": "lead-1", "name": "Alice"}]
    db, builder = _stub_supabase(rows)
    tools = WorkerTools(db=db, client_id=_CLIENT_A)
    out = _run(tools.lead_by_id("lead-1"))
    assert out == rows[0]
    eq_calls = [c.args for c in builder.eq.call_args_list]
    assert ("client_id", _CLIENT_A) in eq_calls
    assert ("id", "lead-1") in eq_calls
