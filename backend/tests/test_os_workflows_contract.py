"""M9.1 workflow contract — types and transition rules only."""

import pytest

from backend.services.os_workflows import (
    ALLOWED_STEP_TRANSITIONS,
    ALLOWED_WORKFLOW_TRANSITIONS,
    InvalidWorkflowTransition,
    PlannerExecutionForbidden,
    ToolIntent,
    Workflow,
    WorkflowStep,
    assert_planner_cannot_execute,
    is_step_terminal,
    is_workflow_terminal,
    transition_step,
    transition_workflow,
)
from backend.services.os_workflows.contract import STEP_TERMINAL_STATES


def test_l0_l1_ready_may_run_without_approval():
    assert transition_step("ready", "running", risk_level=0) == "running"
    assert transition_step("ready", "running", risk_level=1) == "running"


def test_l2_l3_cannot_skip_approval():
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("ready", "running", risk_level=2)
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("ready", "running", risk_level=3)


def test_missing_risk_on_ready_to_running_fails_closed():
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("ready", "running")


def test_approval_path_for_l2():
    state = transition_step("planned", "ready", risk_level=2)
    state = transition_step(state, "pending_approval", risk_level=2)
    state = transition_step(state, "running", risk_level=2)
    assert state == "running"


def test_step_happy_path_l1_to_succeeded():
    state = "planned"
    for target in ("ready", "running", "verifying", "succeeded"):
        state = transition_step(state, target, risk_level=1)
    assert state == "succeeded"
    assert is_step_terminal(state)


def test_failed_is_retryable_not_terminal():
    assert "failed" not in STEP_TERMINAL_STATES
    assert not is_step_terminal("failed")
    assert transition_step("failed", "ready", risk_level=1) == "ready"
    assert transition_step("failed", "planned", risk_level=1) == "planned"
    assert transition_step("failed", "cancelled", risk_level=1) == "cancelled"


def test_terminal_steps_have_empty_outbound():
    for terminal in ("succeeded", "cancelled"):
        assert is_step_terminal(terminal)
        assert ALLOWED_STEP_TRANSITIONS[terminal] == frozenset()
        with pytest.raises(InvalidWorkflowTransition):
            transition_step(terminal, "ready")


def test_l0_l1_unknown_allows_controlled_recovery():
    assert transition_step("unknown", "ready", risk_level=0) == "ready"
    assert transition_step("unknown", "planned", risk_level=1) == "planned"
    assert transition_step("unknown", "blocked", risk_level=1) == "blocked"
    assert transition_step("unknown", "cancelled", risk_level=1) == "cancelled"


def test_l2_l3_unknown_cancel_only_no_replay():
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "running", risk_level=2)
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "ready", risk_level=2)
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "planned", risk_level=3)
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "blocked", risk_level=3)
    assert transition_step("unknown", "cancelled", risk_level=2) == "cancelled"


def test_workflow_pause_resume():
    status = transition_workflow("planned", "running")
    status = transition_workflow(status, "paused")
    status = transition_workflow(status, "running")
    assert status == "running"
    assert not is_workflow_terminal(status)


def test_workflow_failed_is_genuinely_terminal():
    assert ALLOWED_WORKFLOW_TRANSITIONS["failed"] == frozenset()
    assert is_workflow_terminal("failed")
    with pytest.raises(InvalidWorkflowTransition):
        transition_workflow("failed", "cancelled")


def test_planner_cannot_execute():
    with pytest.raises(PlannerExecutionForbidden):
        assert_planner_cannot_execute("m9.1-test")


def test_workflow_model_uses_client_id_alias():
    step = WorkflowStep(
        id="s1",
        workflow_id="w1",
        ordinal=0,
        description="List unpaid invoices",
        tool_intent=ToolIntent(tool_name="list_invoices", arguments={"days": 30}),
        risk_level=0,
    )
    wf = Workflow(
        id="w1",
        tenantId="tenant-abc",
        ownerGoal="Follow up unpaid invoices",
        steps=[step],
    )
    assert wf.client_id == "tenant-abc"
    assert wf.tenant_id == "tenant-abc"
    dumped = wf.model_dump(by_alias=True)
    assert dumped["tenantId"] == "tenant-abc"
    assert dumped["ownerGoal"].startswith("Follow")


def test_step_rejects_self_dependency():
    with pytest.raises(ValueError, match="depend on itself"):
        WorkflowStep(
            id="s1",
            workflow_id="w1",
            ordinal=0,
            description="bad",
            dependencies=["s1"],
        )


def test_step_transition_to_helper_enforces_l2_approval():
    step = WorkflowStep(
        id="s1",
        workflow_id="w1",
        ordinal=0,
        description="Send reminder",
        risk_level=2,
        state="ready",
    )
    with pytest.raises(InvalidWorkflowTransition):
        step.transition_to("running")
    next_step = step.transition_to("pending_approval")
    assert next_step.state == "pending_approval"
    assert step.state == "ready"


def test_workflow_step_mismatch_rejected():
    with pytest.raises(ValueError, match="workflow_id"):
        Workflow(
            id="w1",
            tenantId="t1",
            ownerGoal="goal",
            steps=[
                WorkflowStep(
                    id="s1",
                    workflow_id="other",
                    ordinal=0,
                    description="x",
                )
            ],
        )


def test_unknown_current_state_rejected():
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("not_a_state", "ready", risk_level=1)
    with pytest.raises(InvalidWorkflowTransition):
        transition_workflow("not_a_status", "running")


def test_tool_intent_rejects_whitespace_only_name():
    with pytest.raises(ValueError, match="non-empty"):
        ToolIntent(tool_name="   ")


def test_duplicate_dependencies_are_deduped():
    step = WorkflowStep(
        id="s1",
        workflow_id="w1",
        ordinal=0,
        description="x",
        dependencies=["a", "b", "a"],
    )
    assert step.dependencies == ["a", "b"]


def test_workflow_transition_to_helper():
    wf = Workflow(id="w1", tenantId="t1", ownerGoal="goal")
    next_wf = wf.transition_to("running")
    assert next_wf.status == "running"
    assert wf.status == "planned"
