"""Focused billing lifecycle tests for tenant-scoped graph AI nodes."""

from types import SimpleNamespace

import pytest

from backend.graph.adapters import llm as llm_adapter
from backend.graph.errors import BudgetExhausted
from backend.graph.nodes import NodeContext
from backend.services.llm_runtime import ClaudeCallResult


def _result() -> ClaudeCallResult:
    return ClaudeCallResult(
        text="ok",
        duration_ms=1,
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=None,
        cache_read_input_tokens=None,
        stop_reason="end_turn",
    )


def _ctx() -> NodeContext:
    return NodeContext(
        state={}, node="draft", superstep=0, run_id="run-1", tenant_id="tenant-1"
    )


def _install_meter(monkeypatch, *, allowed=True):
    reservation = SimpleNamespace(allowed=allowed)
    calls = {"reserve": [], "record": [], "release": []}
    monkeypatch.setattr(
        llm_adapter,
        "_load_budget_tenant",
        lambda tenant_id: {"id": tenant_id, "plan": "agent_os"},
    )
    monkeypatch.setattr(
        llm_adapter,
        "reserve_ai_tokens",
        lambda **kwargs: calls["reserve"].append(kwargs) or reservation,
    )
    monkeypatch.setattr(
        llm_adapter,
        "record_ai_usage",
        lambda **kwargs: calls["record"].append(kwargs),
    )
    monkeypatch.setattr(
        llm_adapter,
        "release_ai_token_reservation",
        lambda value: calls["release"].append(value),
    )
    return reservation, calls


class _TenantQuery:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "tenants"
        return self

    def select(self, fields):
        assert "ai_monthly_token_hard_limit" in fields
        return self

    def eq(self, field, value):
        assert (field, value) == ("id", "tenant-1")
        return self

    def limit(self, value):
        assert value == 1
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


def test_load_budget_tenant_returns_policy(monkeypatch):
    monkeypatch.setattr(
        llm_adapter,
        "get_service_supabase",
        lambda: _TenantQuery([{"id": "stale-id", "plan": "agent_os"}]),
    )

    tenant = llm_adapter._load_budget_tenant("tenant-1")

    assert tenant == {"id": "tenant-1", "plan": "agent_os"}


def test_load_budget_tenant_missing_returns_none(monkeypatch):
    monkeypatch.setattr(
        llm_adapter,
        "get_service_supabase",
        lambda: _TenantQuery([]),
    )

    assert llm_adapter._load_budget_tenant("tenant-1") is None


def test_load_budget_tenant_query_failure_returns_none(monkeypatch):
    def fail_client():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(llm_adapter, "get_service_supabase", fail_client)

    assert llm_adapter._load_budget_tenant("tenant-1") is None


async def test_tenant_graph_call_reserves_then_records(monkeypatch):
    reservation, calls = _install_meter(monkeypatch)
    provider_calls = []

    async def fake_provider(**kwargs):
        provider_calls.append(kwargs)
        return _result()

    monkeypatch.setattr(llm_adapter, "call_claude_messages", fake_provider)
    node = llm_adapter.agent_node(
        operation="graph.draft", model="claude-sonnet-5", prompt="hello"
    )

    result = await node(_ctx())

    assert result.updates == {"reply": "ok"}
    assert len(provider_calls) == 1
    assert calls["reserve"][0]["tenant"]["id"] == "tenant-1"
    assert calls["reserve"][0]["session_id"] == "run-1"
    assert calls["record"][0]["reservation"] is reservation
    assert calls["record"][0]["result"].text == "ok"
    assert calls["release"] == []


async def test_tenant_graph_provider_failure_releases_reservation(monkeypatch):
    reservation, calls = _install_meter(monkeypatch)

    async def fake_provider(**kwargs):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(llm_adapter, "call_claude_messages", fake_provider)
    node = llm_adapter.agent_node(
        operation="graph.draft", model="claude-sonnet-5", prompt="hello"
    )

    with pytest.raises(RuntimeError, match="provider failed"):
        await node(_ctx())

    assert calls["record"] == []
    assert calls["release"] == [reservation]


async def test_tenant_graph_record_failure_releases_reservation(monkeypatch):
    reservation, calls = _install_meter(monkeypatch)

    async def fake_provider(**kwargs):
        return _result()

    def fail_record(**kwargs):
        calls["record"].append(kwargs)
        raise RuntimeError("record failed")

    monkeypatch.setattr(llm_adapter, "call_claude_messages", fake_provider)
    monkeypatch.setattr(llm_adapter, "record_ai_usage", fail_record)
    node = llm_adapter.agent_node(
        operation="graph.draft", model="claude-sonnet-5", prompt="hello"
    )

    with pytest.raises(RuntimeError, match="record failed"):
        await node(_ctx())

    assert len(calls["record"]) == 1
    assert calls["release"] == [reservation]


async def test_tenant_graph_hard_limit_blocks_provider(monkeypatch):
    _, calls = _install_meter(monkeypatch, allowed=False)
    provider_calls = []

    async def fake_provider(**kwargs):
        provider_calls.append(kwargs)
        return _result()

    monkeypatch.setattr(llm_adapter, "call_claude_messages", fake_provider)
    node = llm_adapter.agent_node(
        operation="graph.draft", model="claude-sonnet-5", prompt="hello"
    )

    with pytest.raises(BudgetExhausted, match="monthly AI usage limit"):
        await node(_ctx())

    assert provider_calls == []
    assert len(calls["reserve"]) == 1
    assert calls["record"] == []
    assert calls["release"] == []


async def test_tenant_lookup_failure_blocks_provider(monkeypatch):
    provider_calls = []
    monkeypatch.setattr(llm_adapter, "_load_budget_tenant", lambda tenant_id: None)

    async def fake_provider(**kwargs):
        provider_calls.append(kwargs)
        return _result()

    monkeypatch.setattr(llm_adapter, "call_claude_messages", fake_provider)
    node = llm_adapter.agent_node(
        operation="graph.draft", model="claude-sonnet-5", prompt="hello"
    )

    with pytest.raises(RuntimeError, match="tenant policy could not be loaded"):
        await node(_ctx())

    assert provider_calls == []
