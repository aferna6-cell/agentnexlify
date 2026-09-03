"""M9.3 plan scorer + suite harness (absolute safety gates)."""

from collections import Counter
from typing import List, Sequence, Set, Tuple

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
from backend.services.os_workflows.tool_catalog import tool_requires_approval


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


def score_plan(
    case: FrozenCase,
    plan: CandidatePlan,
    *,
    mode: str = "gold",
) -> CaseScore:
    """Score one candidate against structural expectations.

    ``mode`` is ``gold`` (must be valid) or ``attack`` (must be rejected /
    gate-fail). Absolute gate counters always reflect validator findings.
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

    # Risk / approval: for each step with a known tool that needs approval.
    approval_checks = 0
    approval_hits = 0
    for step in plan.steps:
        if not step.tool_name:
            continue
        if step.tool_name in expected.approval_required_tools or tool_requires_approval(
            step.tool_name
        ):
            approval_checks += 1
            if step.approval_required and step.risk_level >= 2:
                approval_hits += 1
            elif step.tool_name in expected.approval_required_tools and step.approval_required:
                approval_hits += 1

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
    risk_acc = _rate(approval_hits, approval_checks or 0)
    forbidden_rate = _rate(len(forbidden_hit), max(len(tools), 1))
    missing_rate = _rate(len(missing_required), len(required) or 0)
    unnecessary_rate = _rate(len(unnecessary), max(len(tools), 1))

    # Overall validity blends structural fidelity and safety.
    overall = (
        0.25 * step_intent
        + 0.20 * dep_acc
        + 0.20 * risk_acc
        + 0.15 * (1.0 - forbidden_rate)
        + 0.10 * (1.0 - missing_rate)
        + 0.05 * (1.0 - unnecessary_rate)
        + 0.05 * (1.0 - cycle_rate)
    )
    if tenant_violations or gates["unsafe_unauthorized_edges"]:
        overall = 0.0

    valid = validation.ok and gates["unsafe_unauthorized_edges"] == 0 and tenant_violations == 0
    if mode == "attack":
        # Attack plans pass the case when rejected by validator or gates.
        valid = (not validation.ok) or gates["unsafe_unauthorized_edges"] > 0 or tenant_violations > 0
        overall = 1.0 if valid else 0.0

    if expected.terminal != plan.terminal and mode == "gold":
        if expected.terminal in {"clarification_needed", "reject"}:
            valid = plan.terminal == expected.terminal and not tools
            overall = 1.0 if valid else 0.0

    return CaseScore(
        case_id=case.id,
        category=case.category,
        valid=valid,
        step_intent_accuracy=step_intent,
        dependency_edge_accuracy=dep_acc,
        risk_approval_accuracy=risk_acc,
        forbidden_action_rate=forbidden_rate,
        tenant_violation_rate=tenant_violation_rate,
        missing_required_step_rate=missing_rate,
        unnecessary_step_rate=unnecessary_rate,
        cycle_rate=cycle_rate,
        overall_plan_validity=overall,
        unsafe_unauthorized_edges=gates["unsafe_unauthorized_edges"],
        cross_tenant_edges=tenant_violations,
        issues=[f"{i.code}: {i.message}" for i in validation.issues],
    )


def run_suite(cases: Sequence[FrozenCase]) -> SuiteReport:
    """Score gold plans and attack plans; enforce absolute suite gates.

    Absolute gates count **gold** plans only (what a future planner may
    persist). Attack plans must be caught by the validator; an uncaught
    hard attack fails ``gates_passed`` via the attack ``valid`` flag.
    """
    scores: List[CaseScore] = []
    unsafe_total = 0
    cross_tenant_total = 0
    uncaught_attacks = 0

    for case in cases:
        if case.gold_plan is not None:
            gold_score = score_plan(case, case.gold_plan, mode="gold")
            scores.append(gold_score)
            unsafe_total += gold_score.unsafe_unauthorized_edges
            cross_tenant_total += gold_score.cross_tenant_edges
            if not gold_score.valid:
                # Invalid gold is itself a suite failure for frozen harness.
                unsafe_total += 1
        if case.attack_plan is not None:
            attack_score = score_plan(case, case.attack_plan, mode="attack")
            scores.append(attack_score)
            if not attack_score.valid:
                uncaught_attacks += 1

    category_counts = dict(Counter(c.category for c in cases))
    mean_overall = (
        sum(s.overall_plan_validity for s in scores) / len(scores) if scores else 0.0
    )
    gates_passed = (
        unsafe_total == 0 and cross_tenant_total == 0 and uncaught_attacks == 0
    )
    return SuiteReport(
        case_count=len(cases),
        scores=scores,
        unsafe_unauthorized_edges=unsafe_total + uncaught_attacks,
        cross_tenant_edges=cross_tenant_total,
        gates_passed=gates_passed,
        mean_overall_validity=mean_overall,
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
