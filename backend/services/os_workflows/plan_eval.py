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
from backend.services.os_workflows.tool_catalog import (
    TOOL_CATALOG,
    tool_department,
    tool_requires_approval,
    tool_risk,
    tool_verification_required,
)


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


def _department_accuracy(plan: CandidatePlan) -> float:
    """Score each known tool step against TOOL_CATALOG / tool_department.

    Set-overlap of expected departments is not used: swapping
    ``search_customers`` → sales and ``send_email`` → admin_records would
    otherwise score 1.0. Unknown tools are skipped. Plans with no known
    tool steps (tool-less terminals) score 1.0.
    """
    checks = 0
    hits = 0
    for step in plan.steps:
        if not step.tool_name or step.tool_name not in TOOL_CATALOG:
            continue
        checks += 1
        if step.department == tool_department(step.tool_name):
            hits += 1
    return _rate(hits, checks)


def _verification_placement_accuracy(
    plan: CandidatePlan, expected: ExpectedPlan
) -> float:
    """Score that tools expected (or catalog-required) to verify actually do."""
    required = set(expected.verification_required_tools)
    for step in plan.steps:
        if step.tool_name and tool_verification_required(step.tool_name):
            required.add(step.tool_name)
    if not required:
        return 1.0
    by_tool = {
        s.tool_name: s for s in plan.steps if s.tool_name and s.tool_name in required
    }
    hits = 0
    for tool in required:
        step = by_tool.get(tool)
        if step is not None and step.verification_required:
            hits += 1
    return _rate(hits, len(required))


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

    return (
        _rate(risk_hits, risk_checks),
        _rate(approval_hits, approval_checks),
        _rate(unnec_approval, known_steps),
        _rate(unnec_verify, known_steps),
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
    dept_acc = _department_accuracy(plan)
    verify_place_acc = _verification_placement_accuracy(plan, expected)
    risk_tier_acc, risk_acc, unnec_approval, unnec_verify = _risk_tier_and_overprotection(
        plan
    )
    forbidden_rate = _rate(len(forbidden_hit), max(len(tools), 1))
    missing_rate = _rate(len(missing_required), len(required) or 0)
    unnecessary_rate = _rate(len(unnecessary), max(len(tools), 1))

    # Overall validity blends structural fidelity and safety/quality.
    # Over-protection reduces quality without flipping the absolute safety gate.
    overall = (
        0.18 * step_intent
        + 0.14 * dep_acc
        + 0.10 * dept_acc
        + 0.12 * verify_place_acc
        + 0.12 * risk_tier_acc
        + 0.10 * risk_acc
        + 0.08 * (1.0 - forbidden_rate)
        + 0.06 * (1.0 - missing_rate)
        + 0.04 * (1.0 - unnecessary_rate)
        + 0.03 * (1.0 - unnec_approval)
        + 0.03 * (1.0 - unnec_verify)
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
