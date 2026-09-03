"""One-shot M9.4 live bakeoff entry for the staging Railway runner.

Uses the existing backend image contents. Does not persist workflows or
call the Action Executor.
"""

import json

from backend.services.os_workflows.eval_cases import build_frozen_cases
from backend.services.os_workflows.planner_bakeoff import (
    CHEAP_PLANNER_MODEL,
    STRONG_PLANNER_MODEL,
    run_bakeoff,
)


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
    summary = {
        "mode": report.mode,
        "sample": report.sample,
        "case_ids": list(report.case_ids),
        "category_counts": dict(report.category_counts),
        "models": [
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
            for model in report.models
        ],
    }
    print("M9_BAKEOFF_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
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
