"""M9 Persistent Planner — workflow contract surface.

M9.1 ships types and transition rules only. Persistence and the
deterministic engine land in M9.2. The planner may decide what should
happen next; it must never independently perform the action.
"""

from backend.services.os_workflows.contract import (
    ALLOWED_STEP_TRANSITIONS,
    ALLOWED_WORKFLOW_TRANSITIONS,
    STEP_TERMINAL_STATES,
    WORKFLOW_TERMINAL_STATUSES,
    InvalidWorkflowTransition,
    PlannerExecutionForbidden,
    RiskLevel,
    StepState,
    ToolIntent,
    VerificationState,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    assert_planner_cannot_execute,
    is_step_terminal,
    is_workflow_terminal,
    transition_step,
    transition_workflow,
)

__all__ = [
    "ALLOWED_STEP_TRANSITIONS",
    "ALLOWED_WORKFLOW_TRANSITIONS",
    "STEP_TERMINAL_STATES",
    "WORKFLOW_TERMINAL_STATUSES",
    "InvalidWorkflowTransition",
    "PlannerExecutionForbidden",
    "RiskLevel",
    "StepState",
    "ToolIntent",
    "VerificationState",
    "Workflow",
    "WorkflowStatus",
    "WorkflowStep",
    "assert_planner_cannot_execute",
    "is_step_terminal",
    "is_workflow_terminal",
    "transition_step",
    "transition_workflow",
]
