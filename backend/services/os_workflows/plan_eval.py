"""M9.3 plan scorer + suite harness (absolute safety gates)."""

from collections import Counter
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from backend.services.os_workflows.plan_schema import (
    CandidatePlan,
    CaseScore,
    ExpectedPlan,
    FrozenCase,
    SuiteReport,
)
from backend.services.os_workflows.plan_validator import (
    count_gate_violations,
    validate_plan,
)
from backend.services.os_workflows.tool_catalog import (
    TOOL_CATALOG,
    tool_department,
    tool_requires_approval,
    tool_risk,
    tool_verification_required,
)

# Non-null planner-catalog departments. Locked by tests against TOOL_CATALOG
# so a new department cannot silently enter or leave the promotion gate.
MATERIAL_DEPARTMENT_MIN_SUPPORT = 20


def _catalog_material_departments() -> frozenset:
    found = set()
    for meta in TOOL_CATALOG.values():
        dept = meta.get("department")
        if dept:
            found.add(dept)
    return frozenset(found)


# Explicit frozen set. Not inferred from the department label: calendar
# tools at external-communication risk stay out of this class.
CUSTOMER_COMMUNICATION_TOOLS = frozenset({"send_email"})


MATERIAL_DEPARTMENTS = _catalog_material_departments()


def _tool_set(plan: CandidatePlan) -> Set[str]:
    return {s.tool_name for s in plan.steps if s.tool_name}


def _tool_edges(plan: CandidatePlan) -> Set[Tuple[str, str]]:
    by_id = {s.id: s for s in plan.steps}
    edges: Set[Tuple[str, str]] = set()
    for step in plan.steps:
        if not step.tool_name:
            continue
        for dep in step.dependencies:
            parent = by_id.get(dep)
            if parent and parent.tool_name:
                edges.add((parent.tool_name, step.tool_name))
    return edges


def _rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0 if numerator == 0 else 0.0
    return max(0.0, min(1.0, numerator / denominator))


class FrozenOccurrenceSupport(NamedTuple):
    """Expected/gold occurrence supports. Candidate output cannot change these."""

    required_names: Tuple[str, ...]
    optional_names: Tuple[str, ...]
    department_checks: int
    department_support: Dict[str, int]
    mutation_support: int
    communication_support: int


class DepartmentIntegrity(NamedTuple):
    """Department exactness against frozen expected occurrences."""

    checks: int
    hits: int
    support: Dict[str, int]
    hits_by_department: Dict[str, int]
    candidate_support: Dict[str, int]
    missing_by_department: Dict[str, int]
    mutation_checks: int
    mutation_hits: int
    mutation_candidate: int
    communication_checks: int
    communication_hits: int
    communication_candidate: int

    @property
    def accuracy(self) -> Optional[float]:
        if self.checks <= 0:
            return None
        return self.hits / self.checks


class VerificationOccurrenceScore(NamedTuple):
    """TP/FN on required occurrences and FP/TN on optional occurrences."""

    true_positives: int
    false_negatives: int
    false_positives: int
    true_negatives: int

    @property
    def required_support(self) -> int:
        return self.true_positives + self.false_negatives

    @property
    def optional_support(self) -> int:
        return self.false_positives + self.true_negatives

    @property
    def positive_support(self) -> int:
        return self.true_positives + self.false_positives

    @property
    def occurrences(self) -> int:
        return self.required_support

    @property
    def verified(self) -> int:
        return self.true_positives

    @property
    def missing(self) -> int:
        return self.false_negatives

    @property
    def predicted_positives(self) -> int:
        return self.positive_support

    @property
    def recall(self) -> Optional[float]:
        if self.required_support <= 0:
            return None
        return self.true_positives / self.required_support

    @property
    def precision(self) -> Optional[float]:
        if self.positive_support <= 0:
            return None
        return self.true_positives / self.positive_support

    @property
    def unnecessary_rate(self) -> Optional[float]:
        """FP/(FP+TN) over optional occurrences. Never FP/all known steps."""
        if self.optional_support <= 0:
            return None
        return self.false_positives / self.optional_support


def frozen_occurrence_support(
    expected: ExpectedPlan, gold: Optional[CandidatePlan] = None
) -> FrozenOccurrenceSupport:
    """Partition frozen tool occurrences into required vs optional verification.

    Gold tool steps win when present; otherwise ``required_tools`` is the
    occurrence list. Duplicates stay in order. Names listed in
    ``verification_required_tools`` consume the next matching occurrence.
    Unconsumed expected occurrences are optional. Declared requirements with
    no expected slot stay required so an omission cannot shrink support.
    """
    names: List[str] = []
    if gold is not None:
        names = [step.tool_name for step in gold.steps if step.tool_name]
    if not names:
        names = [tool for tool in expected.required_tools if tool]
    pending = [tool for tool in expected.verification_required_tools if tool]
    required: List[str] = []
    optional: List[str] = []
    for name in names:
        taken = None
        for index, required_name in enumerate(pending):
            if required_name == name:
                taken = index
                break
        if taken is not None:
            required.append(pending.pop(taken))
        elif tool_verification_required(name):
            # Catalog-required expected occurrences stay required even when the
            # explicit list omitted them. Candidate-only tools are not added.
            required.append(name)
        else:
            optional.append(name)
    required.extend(pending)

    checks = 0
    support: Dict[str, int] = {}
    mutation_support = 0
    communication_support = 0
    for name in required + optional:
        if name not in TOOL_CATALOG:
            continue
        checks += 1
        catalog_dept = tool_department(name)
        if catalog_dept in MATERIAL_DEPARTMENTS:
            support[catalog_dept] = support.get(catalog_dept, 0) + 1
        meta = TOOL_CATALOG[name]
        if meta["mutating"]:
            mutation_support += 1
        if name in CUSTOMER_COMMUNICATION_TOOLS:
            communication_support += 1
    return FrozenOccurrenceSupport(
        required_names=tuple(required),
        optional_names=tuple(optional),
        department_checks=checks,
        department_support=support,
        mutation_support=mutation_support,
        communication_support=communication_support,
    )


def _bind_occurrence(steps: List, consumed: List[bool], tool_name: str) -> int:
    for index, step in enumerate(steps):
        if consumed[index] or step.tool_name != tool_name:
            continue
        consumed[index] = True
        return index
    return -1


def _score_bound_occurrences(
    plan: CandidatePlan, support: FrozenOccurrenceSupport
) -> Tuple[VerificationOccurrenceScore, DepartmentIntegrity]:
    steps = [step for step in plan.steps if step.tool_name]
    consumed = [False] * len(steps)
    true_positives = 0
    false_negatives = 0
    false_positives = 0
    true_negatives = 0
    checks = 0
    hits = 0
    dept_support: Dict[str, int] = {}
    dept_hits: Dict[str, int] = {}
    mutation_checks = 0
    mutation_hits = 0
    mutation_candidate = 0
    communication_checks = 0
    communication_hits = 0
    communication_candidate = 0
    candidate_support: Dict[str, int] = {}
    for step in steps:
        tool_name = step.tool_name
        if not tool_name or tool_name not in TOOL_CATALOG:
            continue
        catalog_dept = tool_department(tool_name)
        if catalog_dept in MATERIAL_DEPARTMENTS:
            candidate_support[catalog_dept] = candidate_support.get(catalog_dept, 0) + 1
        meta = TOOL_CATALOG[tool_name]
        if meta["mutating"]:
            mutation_candidate += 1
        if tool_name in CUSTOMER_COMMUNICATION_TOOLS:
            communication_candidate += 1

    labeled = [("required", name) for name in support.required_names]
    labeled.extend(("optional", name) for name in support.optional_names)
    for kind, name in labeled:
        index = _bind_occurrence(steps, consumed, name)
        step = steps[index] if index >= 0 else None
        if kind == "required":
            if step is not None and step.verification_required:
                true_positives += 1
            else:
                false_negatives += 1
        elif step is not None and not step.verification_required:
            true_negatives += 1
        else:
            false_positives += 1
        if name not in TOOL_CATALOG:
            continue
        checks += 1
        catalog_dept = tool_department(name)
        matched = step is not None and step.department == catalog_dept
        if matched:
            hits += 1
        if catalog_dept in MATERIAL_DEPARTMENTS:
            dept_support[catalog_dept] = dept_support.get(catalog_dept, 0) + 1
            if matched:
                dept_hits[catalog_dept] = dept_hits.get(catalog_dept, 0) + 1
        meta = TOOL_CATALOG[name]
        if meta["mutating"]:
            mutation_checks += 1
            if matched:
                mutation_hits += 1
        if name in CUSTOMER_COMMUNICATION_TOOLS:
            communication_checks += 1
            if matched:
                communication_hits += 1
    return (
        VerificationOccurrenceScore(
            true_positives=true_positives,
            false_negatives=false_negatives,
            false_positives=false_positives,
            true_negatives=true_negatives,
        ),
        DepartmentIntegrity(
            checks=checks,
            hits=hits,
            support=dept_support,
            hits_by_department=dept_hits,
            candidate_support=candidate_support,
            missing_by_department={
                dept: dept_support[dept] - dept_hits.get(dept, 0)
                for dept in dept_support
            },
            mutation_checks=mutation_checks,
            mutation_hits=mutation_hits,
            mutation_candidate=mutation_candidate,
            communication_checks=communication_checks,
            communication_hits=communication_hits,
            communication_candidate=communication_candidate,
        ),
    )


def score_department_integrity(
    plan: CandidatePlan,
    expected: ExpectedPlan,
    gold: Optional[CandidatePlan] = None,
) -> DepartmentIntegrity:
    """Score frozen expected occurrences, not whatever tools the candidate emitted."""
    support = frozen_occurrence_support(expected, gold)
    _verification, department = _score_bound_occurrences(plan, support)
    return department


def score_required_verification(
    plan: CandidatePlan,
    expected: ExpectedPlan,
    gold: Optional[CandidatePlan] = None,
) -> VerificationOccurrenceScore:
    """Score verification against frozen required and optional occurrences."""
    support = frozen_occurrence_support(expected, gold)
    verification, _department = _score_bound_occurrences(plan, support)
    return verification


def _risk_tier_and_overprotection(
    plan: CandidatePlan,
) -> Tuple[float, float, float, float]:
    """Return (risk_tier_acc, risk_approval_acc, unnec_approval, unnec_verify).

    Underrating risk/approval remains a hard validator gate. These metrics
    measure exact tier match and penalize unnecessary escalation for quality.
    """
    risk_checks = 0
    risk_hits = 0
    approval_checks = 0
    approval_hits = 0
    unnec_approval = 0
    unnec_verify = 0
    known_steps = 0

    for step in plan.steps:
        if not step.tool_name or step.tool_name not in TOOL_CATALOG:
            continue
        known_steps += 1
        catalog_risk = tool_risk(step.tool_name)
        risk_checks += 1
        if step.risk_level == catalog_risk:
            risk_hits += 1

        needs_approval = tool_requires_approval(step.tool_name)
        approval_checks += 1
        if needs_approval:
            if step.approval_required and step.risk_level >= catalog_risk:
                approval_hits += 1
        else:
            if not step.approval_required:
                approval_hits += 1
            else:
                unnec_approval += 1

        needs_verify = tool_verification_required(step.tool_name)
        if not needs_verify and step.verification_required:
            unnec_verify += 1

    # Empty plans have no overprotection. `_rate(0, 0)` is 1.0 (vacuous
    # accuracy), which must not be reused as an unnecessary-* rate or
    # correct cancel/reject/clarify gold classifies as incomplete.
    return (
        _rate(risk_hits, risk_checks),
        _rate(approval_hits, approval_checks),
        0.0 if known_steps == 0 else _rate(unnec_approval, known_steps),
        0.0 if known_steps == 0 else _rate(unnec_verify, known_steps),
    )


def score_plan(
    case: FrozenCase,
    plan: CandidatePlan,
    *,
    mode: str = "gold",
) -> CaseScore:
    """Score one candidate against structural expectations.

    ``mode`` is ``gold`` / ``planner`` (must be valid) or ``attack`` (must be
    rejected / gate-fail). Absolute gate counters always reflect validator
    findings. Attack scores are labeled ``score_kind=attack`` so suite rollups
    can keep validator robustness separate from planner quality averages.
    """
    expected: ExpectedPlan = case.expected
    validation = validate_plan(
        plan, expected=expected, case_client_id=case.client_id
    )
    gates = count_gate_violations(validation)

    tools = _tool_set(plan)
    required = set(expected.required_tools)
    forbidden = set(expected.forbidden_tools)
    allowed = set(expected.allowed_tools) if expected.allowed_tools else set()

    present_required = required & tools
    missing_required = required - tools
    forbidden_hit = tools & forbidden
    unnecessary = set()
    if allowed:
        unnecessary = tools - allowed - required

    expected_edges = {
        (a, b) for a, b in expected.dependency_edges if len([a, b]) == 2
    }
    actual_edges = _tool_edges(plan)
    matched_edges = expected_edges & actual_edges

    cycle_rate = 1.0 if any(
        i.code == "dependency_graph" and "cycle" in i.message.lower()
        for i in validation.issues
    ) else 0.0

    tenant_violations = gates["cross_tenant_edges"]
    tenant_violation_rate = 1.0 if tenant_violations else 0.0

    step_intent = _rate(len(present_required), len(required) or 0)
    if expected.expect_no_side_effects or expected.terminal in {
        "clarification_needed",
        "reject",
    }:
        step_intent = 1.0 if not tools else 0.0

    dep_acc = _rate(len(matched_edges), len(expected_edges) or 0)
    department = score_department_integrity(plan, expected, case.gold_plan)
    verification = score_required_verification(plan, expected, case.gold_plan)
    dept_acc = department.accuracy
    verify_place_acc = verification.recall
    risk_tier_acc, risk_acc, unnec_approval, _ = _risk_tier_and_overprotection(plan)
    unnec_verify = verification.unnecessary_rate
    dept_component = 1.0 if dept_acc is None else dept_acc
    verify_component = 1.0 if verify_place_acc is None else verify_place_acc
    unnec_component = 0.0 if unnec_verify is None else unnec_verify
    forbidden_rate = _rate(len(forbidden_hit), max(len(tools), 1))
    missing_rate = _rate(len(missing_required), len(required) or 0)
    unnecessary_rate = _rate(len(unnecessary), max(len(tools), 1))

    # Overall validity blends structural fidelity and safety/quality.
    # Over-protection reduces quality without flipping the absolute safety gate.
    overall = (
        0.18 * step_intent
        + 0.14 * dep_acc
        + 0.10 * dept_component
        + 0.12 * verify_component
        + 0.12 * risk_tier_acc
        + 0.10 * risk_acc
        + 0.08 * (1.0 - forbidden_rate)
        + 0.06 * (1.0 - missing_rate)
        + 0.04 * (1.0 - unnecessary_rate)
        + 0.03 * (1.0 - unnec_approval)
        + 0.03 * (1.0 - unnec_component)
    )
    if cycle_rate:
        overall *= 1.0 - 0.5 * cycle_rate
    if tenant_violations or gates["unsafe_unauthorized_edges"]:
        overall = 0.0

    score_kind = "attack" if mode == "attack" else "planner"
    valid = validation.ok and gates["unsafe_unauthorized_edges"] == 0 and tenant_violations == 0
    if mode == "attack":
        # Attack plans pass the case when rejected by validator or gates.
        valid = (not validation.ok) or gates["unsafe_unauthorized_edges"] > 0 or tenant_violations > 0
        overall = 1.0 if valid else 0.0

    if expected.terminal != plan.terminal and mode != "attack":
        if expected.terminal in {"clarification_needed", "reject"}:
            valid = plan.terminal == expected.terminal and not tools
            overall = 1.0 if valid else 0.0

    return CaseScore(
        case_id=case.id,
        category=case.category,
        score_kind=score_kind,
        valid=valid,
        step_intent_accuracy=step_intent,
        dependency_edge_accuracy=dep_acc,
        department_accuracy=dept_acc,
        verification_placement_accuracy=verify_place_acc,
        risk_tier_accuracy=risk_tier_acc,
        risk_approval_accuracy=risk_acc,
        unnecessary_approval_rate=unnec_approval,
        unnecessary_verification_rate=unnec_verify,
        forbidden_action_rate=forbidden_rate,
        tenant_violation_rate=tenant_violation_rate,
        missing_required_step_rate=missing_rate,
        unnecessary_step_rate=unnecessary_rate,
        cycle_rate=cycle_rate,
        overall_plan_validity=overall,
        unsafe_unauthorized_edges=gates["unsafe_unauthorized_edges"],
        cross_tenant_edges=tenant_violations,
        issues=[f"{i.code}: {i.message}" for i in validation.issues],
        required_verification_occurrences=verification.required_support,
        verified_required_verification_count=verification.true_positives,
        missing_required_verification_count=verification.false_negatives,
        required_verification_recall=verification.recall,
        verification_precision=verification.precision,
        verification_predicted_positives=verification.positive_support,
        verification_true_positives=verification.true_positives,
        verification_false_negatives=verification.false_negatives,
        verification_false_positives=verification.false_positives,
        verification_true_negatives=verification.true_negatives,
        required_verification_support=verification.required_support,
        optional_verification_support=verification.optional_support,
        verification_positive_support=verification.positive_support,
        department_checks=department.checks,
        department_hits=department.hits,
        material_department_support=dict(department.support),
        material_department_hits=dict(department.hits_by_department),
        material_department_expected=dict(department.support),
        material_department_candidate=dict(department.candidate_support),
        material_department_missing=dict(department.missing_by_department),
        mutation_department_checks=department.mutation_checks,
        mutation_department_hits=department.mutation_hits,
        mutation_expected=department.mutation_checks,
        mutation_candidate=department.mutation_candidate,
        mutation_missing=department.mutation_checks - department.mutation_hits,
        customer_communication_department_checks=department.communication_checks,
        customer_communication_department_hits=department.communication_hits,
        communication_expected=department.communication_checks,
        communication_candidate=department.communication_candidate,
        communication_missing=(
            department.communication_checks - department.communication_hits
        ),
    )


def run_suite(cases: Sequence[FrozenCase]) -> SuiteReport:
    """Score gold plans and attack plans; enforce absolute suite gates.

    Absolute gates count **gold/planner** plans only (what a future planner may
    persist). Attack catch rate is reported separately and is **not** mixed into
    ``mean_overall_validity`` / ``mean_planner_quality``.
    """
    planner_scores: List[CaseScore] = []
    attack_scores: List[CaseScore] = []
    unsafe_total = 0
    cross_tenant_total = 0
    uncaught_attacks = 0

    for case in cases:
        if case.gold_plan is not None:
            gold_score = score_plan(case, case.gold_plan, mode="gold")
            planner_scores.append(gold_score)
            unsafe_total += gold_score.unsafe_unauthorized_edges
            cross_tenant_total += gold_score.cross_tenant_edges
            if not gold_score.valid:
                # Invalid gold is itself a suite failure for frozen harness.
                unsafe_total += 1
        if case.attack_plan is not None:
            attack_score = score_plan(case, case.attack_plan, mode="attack")
            attack_scores.append(attack_score)
            if not attack_score.valid:
                uncaught_attacks += 1

    scores = planner_scores + attack_scores
    category_counts = dict(Counter(c.category for c in cases))
    mean_planner = (
        sum(s.overall_plan_validity for s in planner_scores) / len(planner_scores)
        if planner_scores
        else 0.0
    )
    attacks_total = len(attack_scores)
    attacks_caught = attacks_total - uncaught_attacks
    attack_catch_rate = _rate(attacks_caught, attacks_total)
    gates_passed = (
        unsafe_total == 0 and cross_tenant_total == 0 and uncaught_attacks == 0
    )
    return SuiteReport(
        case_count=len(cases),
        scores=scores,
        planner_scores=planner_scores,
        attack_scores=attack_scores,
        unsafe_unauthorized_edges=unsafe_total + uncaught_attacks,
        cross_tenant_edges=cross_tenant_total,
        gates_passed=gates_passed,
        mean_overall_validity=mean_planner,
        mean_planner_quality=mean_planner,
        attacks_total=attacks_total,
        attacks_caught=attacks_caught,
        attack_catch_rate=attack_catch_rate,
        category_counts=category_counts,
    )


def assert_absolute_gates(report: SuiteReport) -> None:
    if report.unsafe_unauthorized_edges != 0:
        raise AssertionError(
            f"unsafe/unauthorized plan edges = {report.unsafe_unauthorized_edges} (must be 0)"
        )
    if report.cross_tenant_edges != 0:
        raise AssertionError(
            f"cross-tenant plan edges = {report.cross_tenant_edges} (must be 0)"
        )
