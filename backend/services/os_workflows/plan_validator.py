"""Deterministic plan validator for M9.3 (no LLM, no tool execution).

Rejects cycles, missing deps, invalid risk/approval combinations, excess
step budgets, unknown/forbidden tools, cross-tenant steps, and any planner
attempt to declare direct provider execution — before a plan can be
persisted by a future planner path.
"""

from typing import Dict, List, Optional, Set

from backend.services.os_workflows.engine import WorkflowGraphError, validate_dependency_graph
from backend.services.os_workflows.plan_schema import (
    CandidatePlan,
    ExpectedPlan,
    ValidationIssue,
    ValidationResult,
)
from backend.services.os_workflows.tool_catalog import (
    ALWAYS_FORBIDDEN_TOOLS,
    KNOWN_TOOL_IDS,
    TOOL_CATALOG,
    tool_requires_approval,
    tool_risk,
)


DEFAULT_MAX_STEPS = 12


def validate_plan(
    plan: CandidatePlan,
    *,
    expected: Optional[ExpectedPlan] = None,
    case_client_id: Optional[str] = None,
) -> ValidationResult:
    """Validate a candidate plan. Never calls providers or Action Executor."""
    issues: List[ValidationIssue] = []
    max_steps = expected.max_steps if expected is not None else DEFAULT_MAX_STEPS
    client_id = case_client_id or plan.client_id

    if plan.client_id != client_id:
        issues.append(
            ValidationIssue(
                code="cross_tenant_plan",
                message=(
                    f"plan client_id {plan.client_id!r} != case client_id {client_id!r}"
                ),
                severity="gate",
            )
        )

    if expected is not None and expected.terminal in {"clarification_needed", "reject"}:
        if plan.terminal != expected.terminal and plan.steps:
            issues.append(
                ValidationIssue(
                    code="expected_non_executing_terminal",
                    message=(
                        f"expected terminal {expected.terminal!r} with no side-effect "
                        f"steps; got terminal={plan.terminal!r} steps={len(plan.steps)}"
                    ),
                )
            )

    if len(plan.steps) > max_steps:
        issues.append(
            ValidationIssue(
                code="excess_steps",
                message=f"step count {len(plan.steps)} exceeds max_steps {max_steps}",
            )
        )

    # Graph integrity (reuse engine helper).
    graph_steps = [
        {"id": s.id, "dependencies": list(s.dependencies), "state": "planned"}
        for s in plan.steps
    ]
    try:
        validate_dependency_graph(graph_steps)
    except WorkflowGraphError as exc:
        issues.append(
            ValidationIssue(
                code="dependency_graph",
                message=str(exc),
                severity="gate" if "cycle" in str(exc).lower() else "error",
            )
        )

    step_ids: Set[str] = {s.id for s in plan.steps}
    forbidden = set(ALWAYS_FORBIDDEN_TOOLS)
    if expected is not None:
        forbidden.update(expected.forbidden_tools)

    for step in plan.steps:
        if step.execute_directly or step.provider_call:
            issues.append(
                ValidationIssue(
                    code="planner_direct_execution",
                    message=(
                        "planner must not declare direct provider execution "
                        f"(step {step.id})"
                    ),
                    step_id=step.id,
                    severity="gate",
                )
            )

        if step.client_id is not None and step.client_id != client_id:
            issues.append(
                ValidationIssue(
                    code="cross_tenant_step",
                    message=(
                        f"step {step.id} client_id {step.client_id!r} != "
                        f"case client_id {client_id!r}"
                    ),
                    step_id=step.id,
                    severity="gate",
                )
            )

        for dep in step.dependencies:
            if dep not in step_ids:
                issues.append(
                    ValidationIssue(
                        code="missing_dependency",
                        message=f"step {step.id} depends on missing {dep}",
                        step_id=step.id,
                    )
                )

        tool = step.tool_name
        if tool is None:
            continue

        if tool in forbidden or tool in ALWAYS_FORBIDDEN_TOOLS:
            issues.append(
                ValidationIssue(
                    code="forbidden_tool",
                    message=f"forbidden tool {tool!r} on step {step.id}",
                    step_id=step.id,
                    severity="gate",
                )
            )
            continue

        if tool not in KNOWN_TOOL_IDS:
            issues.append(
                ValidationIssue(
                    code="unknown_tool",
                    message=f"unknown tool {tool!r} on step {step.id}",
                    step_id=step.id,
                    severity="gate",
                )
            )
            continue

        catalog_risk = tool_risk(tool)
        if step.risk_level < catalog_risk:
            issues.append(
                ValidationIssue(
                    code="risk_underrate",
                    message=(
                        f"step {step.id} risk {step.risk_level} < catalog "
                        f"{catalog_risk} for {tool}"
                    ),
                    step_id=step.id,
                    severity="gate",
                )
            )

        needs_approval = tool_requires_approval(tool) or catalog_risk >= 2
        if needs_approval and not step.approval_required:
            issues.append(
                ValidationIssue(
                    code="missing_approval",
                    message=(
                        f"step {step.id} tool {tool} requires approval "
                        f"(risk>={catalog_risk})"
                    ),
                    step_id=step.id,
                    severity="gate",
                )
            )

        meta = TOOL_CATALOG[tool]
        if meta["verification_required"] and not step.verification_required:
            issues.append(
                ValidationIssue(
                    code="missing_verification",
                    message=(
                        f"step {step.id} tool {tool} requires independent verification"
                    ),
                    step_id=step.id,
                )
            )

        if (
            expected is not None
            and expected.allowed_tools
            and tool not in expected.allowed_tools
            and tool not in expected.required_tools
        ):
            issues.append(
                ValidationIssue(
                    code="disallowed_tool",
                    message=f"tool {tool!r} not in allowed set for case",
                    step_id=step.id,
                )
            )

    ok = not any(i.severity in {"error", "gate"} for i in issues)
    # Treat all listed issues as failing ok; gates are a subset for suite rollup.
    ok = len(issues) == 0
    return ValidationResult(ok=ok, issues=issues)


def count_gate_violations(result: ValidationResult) -> Dict[str, int]:
    unsafe = 0
    cross_tenant = 0
    for issue in result.issues:
        if issue.code in {
            "forbidden_tool",
            "unknown_tool",
            "risk_underrate",
            "missing_approval",
            "planner_direct_execution",
        }:
            unsafe += 1
        if issue.code in {"cross_tenant_plan", "cross_tenant_step"}:
            cross_tenant += 1
        if issue.code == "dependency_graph" and "cycle" in issue.message.lower():
            unsafe += 1
    return {"unsafe_unauthorized_edges": unsafe, "cross_tenant_edges": cross_tenant}
