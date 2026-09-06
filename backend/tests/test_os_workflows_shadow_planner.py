"""M9.5 shadow-path skeleton tests.

In-memory only. No WorkflowStore, no Action Executor, no provider calls.
"""

import ast
from pathlib import Path

import pytest

from backend.services.os_workflows.plan_schema import CandidatePlan, PlanStepSpec
from backend.services.os_workflows.shadow_planner import (
    ShadowObservation,
    ShadowRequest,
    run_shadow,
)

MODULE_PATH = Path("backend/services/os_workflows/shadow_planner.py")


def _clarify_planner(request: ShadowRequest) -> CandidatePlan:
    return CandidatePlan(
        client_id=request.client_id,
        owner_goal=request.owner_goal,
        terminal="clarification_needed",
        notes="shadow skeleton: no provider",
        steps=[],
    )


def test_shadow_module_does_not_import_store_executor_or_provider():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            for alias in node.names:
                imported.add(alias.name)
    joined = " ".join(sorted(imported))
    assert "store" not in joined
    assert "WorkflowStore" not in joined
    assert "os_tool_executions" not in joined
    assert "google_calendar" not in joined
    assert "gmail" not in joined
    assert "executor" not in joined
    assert "action_executor" not in joined
    assert "llm_runtime" not in joined
    assert "anthropic" not in joined.lower()


def test_live_shadow_hard_fails_before_provider_when_key_absent(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    request = ShadowRequest(client_id="t_shadow", owner_goal="Bill a customer")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        run_shadow(request, mode="live")


def test_live_shadow_skeleton_refuses_provider_even_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    request = ShadowRequest(client_id="t_shadow", owner_goal="Bill a customer")
    with pytest.raises(RuntimeError, match="no provider wiring"):
        run_shadow(request, mode="live")


def test_fixture_shadow_returns_in_memory_observation_only():
    request = ShadowRequest(
        client_id="t_shadow",
        owner_goal="Remind overdue invoices",
        context={"source": "unit-test"},
    )
    observation = run_shadow(request, planner=_clarify_planner, mode="fixture")
    assert isinstance(observation, ShadowObservation)
    assert observation.persisted is False
    assert observation.executed is False
    assert observation.provider_called is False
    assert observation.plan is not None
    assert observation.plan.client_id == "t_shadow"
    assert observation.plan.terminal == "clarification_needed"
    assert observation.validation is not None
    assert observation.validation.ok is True


def test_shadow_does_not_call_injected_store_or_executor():
    calls: list[str] = []

    class ForbiddenStore:
        def create(self, *args, **kwargs):
            calls.append("store")
            raise AssertionError("WorkflowStore must not be used in M9.5 shadow")

    class ForbiddenExecutor:
        def execute(self, *args, **kwargs):
            calls.append("executor")
            raise AssertionError("Action Executor must not be used in M9.5 shadow")

    request = ShadowRequest(client_id="t_shadow", owner_goal="Do not persist")
    observation = run_shadow(
        request,
        planner=_clarify_planner,
        mode="fixture",
        store=ForbiddenStore(),
        executor=ForbiddenExecutor(),
    )
    assert calls == []
    assert observation.persisted is False
    assert observation.executed is False


def test_shadow_rejects_cross_tenant_plan_in_memory():
    def other_tenant(request: ShadowRequest) -> CandidatePlan:
        return CandidatePlan(
            client_id="other_tenant",
            owner_goal=request.owner_goal,
            steps=[
                PlanStepSpec(
                    id="s1",
                    description="search",
                    tool_name="search_customers",
                    department="sales",
                )
            ],
        )

    request = ShadowRequest(client_id="t_shadow", owner_goal="Find customers")
    observation = run_shadow(request, planner=other_tenant, mode="fixture")
    assert observation.persisted is False
    assert observation.executed is False
    assert observation.validation is not None
    assert observation.validation.ok is False
    assert any(i.code == "cross_tenant_plan" for i in observation.validation.issues)
