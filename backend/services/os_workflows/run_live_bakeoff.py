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
