"""One-shot M9.4 live bakeoff entry for the staging Railway runner.

Staging-only. Does not persist workflows or call the Action Executor.
The production backend image does not use this module.
"""

import json
from typing import Any, Dict, List

from backend.services.os_workflows.eval_cases import build_frozen_cases
from backend.services.os_workflows.planner_bakeoff import (
    CHEAP_PLANNER_MODEL,
    PROMOTION_BAR,
    STRONG_PLANNER_MODEL,
    BakeoffReport,
    run_bakeoff,
)

SUMMARY_PREFIX = "M9_BAKEOFF_SUMMARY"

# Spend plus every promotion-bar metric, plus the evaluated pass/fail fields.
COMPACT_MODEL_KEYS = (
    "model",
    "attempts",
    "estimated_total_cost_usd",
    "parse_success_rate",
    "valid_plan_rate",
    "required_step_recall",
    "risk_approval_accuracy",
    "dependency_accuracy",
    "clarify_reject_correctness",
    "unsafe_unauthorized_edges",
    "cross_tenant_edges",
    "direct_provider_execution_attempts",
    "mean_cycle_rate",
    "promotion_passed",
    "promotion_failures",
    "miss_counts",
)


def compact_bakeoff_summary(report: BakeoffReport) -> Dict[str, Any]:
    """One-line payload: both models' spend and every promotion gate."""
    models: List[Dict[str, Any]] = []
    known_costs: List[float] = []
    for model in report.models:
        if model.estimated_total_cost_usd is not None:
            known_costs.append(model.estimated_total_cost_usd)
        models.append(
            {
                "model": model.model,
                "attempts": model.attempts,
                "estimated_total_cost_usd": model.estimated_total_cost_usd,
                "parse_success_rate": model.parse_success_rate,
                "valid_plan_rate": model.valid_plan_rate,
                "required_step_recall": model.required_step_recall,
                "risk_approval_accuracy": model.risk_approval_accuracy,
                "dependency_accuracy": model.dependency_accuracy,
                "clarify_reject_correctness": model.clarify_reject_correctness,
                "unsafe_unauthorized_edges": model.unsafe_unauthorized_edges,
                "cross_tenant_edges": model.cross_tenant_edges,
                "direct_provider_execution_attempts": model.direct_provider_execution_attempts,
                "mean_cycle_rate": model.mean_cycle_rate,
                "promotion_passed": model.promotion_passed,
                "promotion_failures": list(model.promotion_failures),
                "miss_counts": dict(model.miss_counts),
            }
        )
    cost_complete = bool(report.models) and all(
        model.estimated_total_cost_usd is not None for model in report.models
    )
    return {
        "mode": report.mode,
        "sample": report.sample,
        "case_count": len(report.case_ids),
        "category_count": len(report.category_counts),
        "estimated_total_cost_usd": sum(known_costs) if cost_complete else None,
        "promotion_bar": dict(PROMOTION_BAR),
        "models": models,
    }


def format_compact_summary_line(report: BakeoffReport) -> str:
    return SUMMARY_PREFIX + " " + json.dumps(compact_bakeoff_summary(report), sort_keys=True)


def main() -> int:
    report = run_bakeoff(
        build_frozen_cases(),
        models=(STRONG_PLANNER_MODEL, CHEAP_PLANNER_MODEL),
        repetitions=(0,),
        mode="live",
        limit=24,
        sample="stratified",
    )
    # One compact line first so Railway's 500 logs/sec cap cannot hide gates.
    print(format_compact_summary_line(report), flush=True)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    hard_fail = any(
        m.unsafe_unauthorized_edges
        or m.cross_tenant_edges
        or m.direct_provider_execution_attempts
        for m in report.models
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
