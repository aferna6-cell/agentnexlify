"""M9.1 workflow contract — types and transition rules only."""

import pytest

from backend.services.os_workflows import (
    ALLOWED_STEP_TRANSITIONS,
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


def test_step_happy_path_to_succeeded():
    state = "planned"
    for target in ("ready", "running", "verifying", "succeeded"):
        state = transition_step(state, target, risk_level=1)
    assert state == "succeeded"
    assert is_step_terminal(state)


def test_approval_path_for_l2():
    state = transition_step("planned", "ready", risk_level=2)
    state = transition_step(state, "pending_approval", risk_level=2)
    state = transition_step(state, "running", risk_level=2)
    assert state == "running"


def test_unknown_cannot_auto_replay_even_if_allowlist_widened():
    """L2/L3 unknown must stay unknown except manual cancel."""
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "running", risk_level=2)
    with pytest.raises(InvalidWorkflowTransition):
        transition_step("unknown", "ready", risk_level=3)
    assert transition_step("unknown", "cancelled", risk_level=2) == "cancelled"


def test_terminal_steps_have_empty_outbound():
    for terminal in ("succeeded", "cancelled"):
        assert ALLOWED_STEP_TRANSITIONS[terminal] == frozenset()
        with pytest.raises(InvalidWorkflowTransition):
            transition_step(terminal, "ready")


def test_workflow_pause_resume():
    status = transition_workflow("planned", "running")
    status = transition_workflow(status, "paused")
    status = transition_workflow(status, "running")
    assert status == "running"
    assert not is_workflow_terminal(status)


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


def test_step_transition_to_helper():
    step = WorkflowStep(
        id="s1",
        workflow_id="w1",
        ordinal=0,
        description="Send reminder",
        risk_level=2,
        state="ready",
    )
    next_step = step.transition_to("pending_approval")
    assert next_step.state == "pending_approval"
    assert step.state == "ready"  # immutable copy


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


def test_l0_ready_may_skip_approval():
    assert transition_step("ready", "running", risk_level=0) == "running"
