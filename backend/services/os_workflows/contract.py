"""M9.1 — typed Workflow / WorkflowStep contract (no persistence, no tools).

Architecture rule (non-negotiable):

    The planner may decide what should happen next.
    It may never independently perform the action.

Execution always flows:

    Planner → Workflow step → Tool/Action contract → risk classification
      → approval gate → Action Executor → provider → independent verification
      → workflow state transition

Risk-aware transition policy (enforced here):

- L0/L1: ``ready → running`` is allowed (approval optional).
- L2/L3: ``ready → pending_approval → running`` is required;
  ``ready → running`` is rejected.
- L0/L1 ``unknown``: controlled recovery to ``planned`` / ``ready`` /
  ``blocked`` / ``cancelled`` is allowed (bounded retry policy lands in M9.2).
- L2/L3 ``unknown``: ``cancelled`` only — never automatically replayed.

DB boundary uses ``client_id`` (never ``tenant_id`` on tenant-scoped rows).
API / agent-service camelCase uses ``tenantId`` for the same value.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Risk levels mirror agent-service Action Executor (0–3).
RiskLevel = Literal[0, 1, 2, 3]
RISK_FAIL_CLOSED: int = 2

StepState = Literal[
    "planned",
    "ready",
    "pending_approval",
    "running",
    "verifying",
    "succeeded",
    "failed",
    "unknown",
    "blocked",
    "cancelled",
]

WorkflowStatus = Literal[
    "planned",
    "running",
    "paused",
    "succeeded",
    "failed",
    "cancelled",
]

VerificationState = Literal[
    "not_required",
    "pending",
    "passed",
    "failed",
    "unknown",
]

# ``failed`` is retryable under explicit M9.2 engine policy — not terminal.
STEP_TERMINAL_STATES: frozenset = frozenset({"succeeded", "cancelled"})

WORKFLOW_TERMINAL_STATUSES: frozenset = frozenset(
    {"succeeded", "failed", "cancelled"}
)

# Base allow-list. Risk-aware gates below further restrict some edges.
ALLOWED_STEP_TRANSITIONS: dict = {
    "planned": frozenset({"ready", "blocked", "cancelled"}),
    "ready": frozenset({"pending_approval", "running", "blocked", "cancelled"}),
    "pending_approval": frozenset({"running", "blocked", "cancelled"}),
    "running": frozenset({"verifying", "failed", "unknown", "cancelled"}),
    "verifying": frozenset({"succeeded", "failed", "unknown"}),
    "blocked": frozenset({"ready", "cancelled"}),
    # failed may be retried only via explicit engine policy (M9.2).
    "failed": frozenset({"planned", "ready", "cancelled"}),
    # Base recovery edges for L0/L1 unknown; L2/L3 narrowed by risk gate.
    "unknown": frozenset({"cancelled", "planned", "ready", "blocked"}),
    "succeeded": frozenset(),
    "cancelled": frozenset(),
}

ALLOWED_WORKFLOW_TRANSITIONS: dict = {
    "planned": frozenset({"running", "paused", "cancelled"}),
    "running": frozenset({"paused", "succeeded", "failed", "cancelled"}),
    "paused": frozenset({"running", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}

_UNKNOWN_RECOVERY_TARGETS = frozenset({"planned", "ready", "blocked"})


class InvalidWorkflowTransition(ValueError):
    """Requested state transition is not allowed."""

    def __init__(self, kind: str, current: str, target: str):
        super().__init__(f"invalid {kind} transition: {current!r} → {target!r}")
        self.kind = kind
        self.current = current
        self.target = target


class PlannerExecutionForbidden(RuntimeError):
    """Planner attempted to invoke a tool/action directly."""


def assert_planner_cannot_execute(context: str = "planner") -> None:
    """Hard stop if any code path tries to execute from planner context.

    M9.1 has no executor wiring. Call this at any future planner entry that
    might be tempted to invoke tools; M9.2+ keeps the same forbid.
    """
    raise PlannerExecutionForbidden(
        f"{context} must not execute tools; enqueue a WorkflowStep for the "
        "Action Executor instead"
    )


def is_step_terminal(state: str) -> bool:
    return state in STEP_TERMINAL_STATES


def is_workflow_terminal(status: str) -> bool:
    return status in WORKFLOW_TERMINAL_STATUSES


def _effective_risk(risk_level: Optional[int]) -> int:
    """Missing risk fails closed at the highest tier."""
    if risk_level is None:
        return 3
    return int(risk_level)


def _enforce_risk_gates(
    current: str, target: str, risk_level: Optional[int]
) -> None:
    level = _effective_risk(risk_level)

    # L2/L3 cannot skip approval.
    if current == "ready" and target == "running" and level >= RISK_FAIL_CLOSED:
        raise InvalidWorkflowTransition("step", current, target)

    # L2/L3 unknown: cancel only — never replay into recovery states.
    if (
        current == "unknown"
        and target in _UNKNOWN_RECOVERY_TARGETS
        and level >= RISK_FAIL_CLOSED
    ):
        raise InvalidWorkflowTransition("step", current, target)


def transition_step(
    current: str,
    target: str,
    *,
    risk_level: Optional[int] = None,
) -> str:
    """Validate and return the next step state (risk-aware)."""
    allowed = ALLOWED_STEP_TRANSITIONS.get(current)
    if allowed is None:
        raise InvalidWorkflowTransition("step", current, target)
    if target not in allowed:
        raise InvalidWorkflowTransition("step", current, target)
    _enforce_risk_gates(current, target, risk_level)
    return target


def transition_workflow(current: str, target: str) -> str:
    """Validate and return the next workflow status."""
    allowed = ALLOWED_WORKFLOW_TRANSITIONS.get(current)
    if allowed is None:
        raise InvalidWorkflowTransition("workflow", current, target)
    if target not in allowed:
        raise InvalidWorkflowTransition("workflow", current, target)
    return target


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ToolIntent(BaseModel):
    """Declared intent only — never an executable handle.

    Persistence (M9.2) stores this JSON; the Action Executor resolves
    ``tool_name`` against the existing tool registry at run time.
    """

    tool_name: str = Field(..., min_length=1, max_length=128)
    arguments: dict = Field(default_factory=dict)
    department: Optional[str] = Field(
        default=None,
        description="Optional department hint (sales, ops, support, …).",
    )

    @field_validator("tool_name")
    @classmethod
    def _strip_tool_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("tool_name must be non-empty")
        return cleaned


class WorkflowStep(BaseModel):
    """One durable unit of planned work inside a workflow."""

    id: str = Field(..., min_length=1)
    workflow_id: str = Field(..., min_length=1)
    ordinal: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)
    dependencies: List[str] = Field(default_factory=list)
    department: Optional[str] = None
    tool_intent: Optional[ToolIntent] = None
    state: StepState = "planned"
    risk_level: RiskLevel = 1
    execution_id: Optional[str] = None
    verification_state: Optional[VerificationState] = None
    error: Optional[str] = None

    @field_validator("dependencies")
    @classmethod
    def _unique_deps(cls, value: List[str]) -> List[str]:
        seen = set()
        out = []
        for dep in value:
            if dep in seen:
                continue
            seen.add(dep)
            out.append(dep)
        return out

    @model_validator(mode="after")
    def _no_self_dependency(self):
        if self.id in self.dependencies:
            raise ValueError("step cannot depend on itself")
        return self

    def transition_to(self, target: StepState):
        next_state = transition_step(
            self.state, target, risk_level=self.risk_level
        )
        return self.model_copy(update={"state": next_state})


class Workflow(BaseModel):
    """Durable multi-step plan. Planner writes state; executor runs steps."""

    id: str = Field(..., min_length=1)
    # API field name tenant_id maps to DB client_id — see schema sketch.
    tenant_id: str = Field(
        ...,
        min_length=1,
        description="Tenant scope. Persist as client_id in Postgres.",
        alias="tenantId",
    )
    owner_goal: str = Field(..., min_length=1, alias="ownerGoal")
    status: WorkflowStatus = "planned"
    steps: List["WorkflowStep"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=_utcnow, alias="updatedAt")

    model_config = {
        "populate_by_name": True,
    }

    @model_validator(mode="after")
    def _steps_belong_to_workflow(self):
        for step in self.steps:
            if step.workflow_id != self.id:
                raise ValueError(
                    f"step {step.id!r} workflow_id {step.workflow_id!r} "
                    f"!= workflow id {self.id!r}"
                )
        return self

    @property
    def client_id(self) -> str:
        """DB-facing alias — always use this at the Postgres boundary."""
        return self.tenant_id

    def transition_to(self, target: WorkflowStatus):
        next_status = transition_workflow(self.status, target)
        return self.model_copy(
            update={"status": next_status, "updated_at": _utcnow()}
        )
