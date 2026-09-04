"""M9.3 frozen planner-eval schemas (structure expectations, not prose)."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


TerminalBehavior = Literal[
    "valid_plan",
    "clarification_needed",
    "reject",
    "cancelled",
    "failed_exhausted",
]


class PlanStepSpec(BaseModel):
    """One candidate / gold plan step (intent only — never executes)."""

    id: str
    description: str = ""
    tool_name: Optional[str] = None
    department: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    risk_level: int = 1
    approval_required: bool = False
    verification_required: bool = False
    # Planner must never set these — validator rejects.
    execute_directly: bool = False
    provider_call: bool = False
    client_id: Optional[str] = None

    @field_validator("risk_level")
    @classmethod
    def _risk_range(cls, value: int) -> int:
        if value not in (0, 1, 2, 3):
            raise ValueError("risk_level must be 0..3")
        return value


class CandidatePlan(BaseModel):
    """A proposed workflow plan for a single owner goal."""

    client_id: str
    owner_goal: str
    steps: List[PlanStepSpec] = Field(default_factory=list)
    terminal: TerminalBehavior = "valid_plan"
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _unique_step_ids(self) -> "CandidatePlan":
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate step ids in candidate plan")
        return self


class ExpectedPlan(BaseModel):
    """Structural expectations for a frozen case (not brittle prose)."""

    departments: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    forbidden_tools: List[str] = Field(default_factory=list)
    # Ordered pairs (from_tool, to_tool) — soft match on tool names.
    dependency_edges: List[List[str]] = Field(default_factory=list)
    approval_required_tools: List[str] = Field(default_factory=list)
    verification_required_tools: List[str] = Field(default_factory=list)
    max_steps: int = 8
    terminal: TerminalBehavior = "valid_plan"
    # When True, an empty plan (or clarification terminal) is correct.
    expect_no_side_effects: bool = False


class FrozenCase(BaseModel):
    """One frozen planner evaluation case."""

    id: str
    category: str
    goal: str
    client_id: str
    expected: ExpectedPlan
    gold_plan: Optional[CandidatePlan] = None
    # Intentionally bad plan used to prove validator/gates reject attacks.
    attack_plan: Optional[CandidatePlan] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    code: str
    message: str
    step_id: Optional[str] = None
    severity: Literal["error", "gate"] = "error"


class ValidationResult(BaseModel):
    ok: bool
    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def gate_failures(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "gate"]


class CaseScore(BaseModel):
    case_id: str
    category: str
    score_kind: Literal["planner", "attack"] = "planner"
    valid: bool
    step_intent_accuracy: float
    dependency_edge_accuracy: float
    department_accuracy: float
    verification_placement_accuracy: float
    risk_tier_accuracy: float
    risk_approval_accuracy: float
    unnecessary_approval_rate: float
    unnecessary_verification_rate: float
    forbidden_action_rate: float
    tenant_violation_rate: float
    missing_required_step_rate: float
    unnecessary_step_rate: float
    cycle_rate: float
    overall_plan_validity: float
    unsafe_unauthorized_edges: int
    cross_tenant_edges: int
    issues: List[str] = Field(default_factory=list)


class SuiteReport(BaseModel):
    case_count: int
    scores: List[CaseScore]
    planner_scores: List[CaseScore] = Field(default_factory=list)
    attack_scores: List[CaseScore] = Field(default_factory=list)
    unsafe_unauthorized_edges: int
    cross_tenant_edges: int
    gates_passed: bool
    # Planner quality only — attack catch rates are NOT mixed in.
    mean_overall_validity: float
    mean_planner_quality: float = 0.0
    attacks_total: int = 0
    attacks_caught: int = 0
    attack_catch_rate: float = 0.0
    category_counts: Dict[str, int] = Field(default_factory=dict)
