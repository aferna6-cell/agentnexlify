"""M9 Persistent Planner — workflow contract + engine surface.

M9.1: types and transition rules.
M9.2: durable store + deterministic engine (no LLM, no tool execution).
M9.3: frozen planner eval + deterministic plan validator (still no LLM).
M9.4: offline LLM planner bakeoff (CandidatePlan JSON only — no persist/execute).
M9.5: shadow-path skeleton (in-memory observe only — no store/executor/provider).
"""

from backend.services.os_workflows.contract import (
    ALLOWED_STEP_TRANSITIONS,
    ALLOWED_WORKFLOW_TRANSITIONS,
    RISK_FAIL_CLOSED,
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
from backend.services.os_workflows.engine import (
    WorkflowEngine,
    WorkflowGraphError,
    compute_ready_step_ids,
    derive_workflow_status,
    validate_dependency_graph,
)
from backend.services.os_workflows.store import (
    ConcurrentModification,
    InMemoryWorkflowStore,
    SupabaseWorkflowStore,
    WorkflowStoreError,
)
from backend.services.os_workflows.plan_validator import validate_plan
from backend.services.os_workflows.plan_eval import assert_absolute_gates, run_suite
from backend.services.os_workflows.eval_cases import build_frozen_cases

__all__ = [
    "ALLOWED_STEP_TRANSITIONS",
    "ALLOWED_WORKFLOW_TRANSITIONS",
    "RISK_FAIL_CLOSED",
    "STEP_TERMINAL_STATES",
    "WORKFLOW_TERMINAL_STATUSES",
    "ConcurrentModification",
    "InMemoryWorkflowStore",
    "InvalidWorkflowTransition",
    "PlannerExecutionForbidden",
    "RiskLevel",
    "StepState",
    "SupabaseWorkflowStore",
    "ToolIntent",
    "VerificationState",
    "Workflow",
    "WorkflowEngine",
    "WorkflowGraphError",
    "WorkflowStatus",
    "WorkflowStep",
    "WorkflowStoreError",
    "assert_planner_cannot_execute",
    "compute_ready_step_ids",
    "derive_workflow_status",
    "is_step_terminal",
    "is_workflow_terminal",
    "transition_step",
    "transition_workflow",
    "validate_dependency_graph",
    "validate_plan",
    "assert_absolute_gates",
    "run_suite",
    "build_frozen_cases",
]
