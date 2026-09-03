#!/usr/bin/env python3
"""Run M9.4 offline LLM planner bakeoff.

Default mode is ``fixture`` (uses gold plans / committed fixtures — no API key).
Live mode calls Anthropic via ``llm_runtime`` and still never persists/executes.

Examples:
  python scripts/run_m9_planner_bakeoff.py
  python scripts/run_m9_planner_bakeoff.py --mode live --sample stratified --limit 24 --repetitions 0
  python scripts/run_m9_planner_bakeoff.py --mode live --sample prefix --limit 10 --repetitions 0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.os_workflows.eval_cases import build_frozen_cases
from backend.services.os_workflows.planner_bakeoff import (
    CHEAP_PLANNER_MODEL,
    DEFAULT_MODELS,
    STRONG_PLANNER_MODEL,
    run_bakeoff,
    write_bakeoff_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="M9.4 offline planner bakeoff")
    parser.add_argument(
        "--mode",
        choices=("fixture", "live"),
        default="fixture",
        help="fixture=offline/gold; live=Anthropic via llm_runtime",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"comma-separated model ids (default {STRONG_PLANNER_MODEL},{CHEAP_PLANNER_MODEL})",
    )
    parser.add_argument(
        "--repetitions",
        default="0,1",
        help="comma-separated int repetition ids (for stability analysis)",
    )
    parser.add_argument("--limit", type=int, default=None, help="optional case cap")
    parser.add_argument(
        "--sample",
        choices=("prefix", "stratified"),
        default="stratified",
        help="prefix=first N by id (biased); stratified=round-robin categories",
    )
    parser.add_argument(
        "--out",
        default="audits/artifacts/m9-4-bakeoff-latest.json",
        help="report output path",
    )
    args = parser.parse_args()

    models = tuple(m.strip() for m in args.models.split(",") if m.strip())
    repetitions = tuple(int(s.strip()) for s in args.repetitions.split(",") if s.strip())
    # Planner quality only — skip attack-only rows without gold plans.
    # Default stratified so --limit is not all apr-* approval cases.
    report = run_bakeoff(
        build_frozen_cases(),
        models=models,
        repetitions=repetitions,
        mode=args.mode,
        limit=args.limit,
        sample=args.sample,
    )
    out = write_bakeoff_report(report, Path(args.out))
    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nWrote {out}")
    # Exit non-zero only when live mode fails absolute zero gates for any model.
    if args.mode == "live":
        hard_fail = any(
            m.unsafe_unauthorized_edges
            or m.cross_tenant_edges
            or m.direct_provider_execution_attempts
            for m in report.models
        )
        return 1 if hard_fail else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
