"""Regression coverage for M9 required-verification hard gates."""

from backend.services.os_workflows.plan_schema import CandidatePlan, PlanStepSpec
from backend.services.os_workflows.plan_validator import (
    count_gate_violations,
    validate_plan,
)
from backend.services.os_workflows.tool_catalog import TOOL_CATALOG


def test_catalog_required_verification_is_an_absolute_gate() -> None:
    tool_name, meta = next(
        (tool, metadata)
        for tool, metadata in TOOL_CATALOG.items()
        if metadata["verification_required"]
    )
    plan = CandidatePlan(
        client_id="tenant-a",
        owner_goal="exercise required verification gate",
        steps=[
            PlanStepSpec(
                id="step-1",
                tool_name=tool_name,
                department=meta["department"],
                risk_level=meta["risk_level"],
                approval_required=meta["requires_approval"] or meta["risk_level"] >= 2,
                verification_required=False,
                client_id="tenant-a",
            )
        ],
    )

    result = validate_plan(plan, case_client_id="tenant-a")
    missing_verification = [
        issue for issue in result.issues if issue.code == "missing_verification"
    ]

    assert len(missing_verification) == 1
    assert missing_verification[0].severity == "gate"
    assert count_gate_violations(result) == {
        "unsafe_unauthorized_edges": 1,
        "cross_tenant_edges": 0,
    }
