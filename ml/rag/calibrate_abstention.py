"""Validation-only abstention calibration (risk / coverage curve).

Never tune against the independent holdout. Writes the frozen operating point
artifact used by retrieve_business_context.DEFAULT_MIN_SCORE.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.services.business_retrieval import DEFAULT_MIN_SCORE
from ml.rag.evaluate import DEFAULT_DATASET, load_dataset, run_eval

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "ml/rag/artifacts/rag-abstention-calibration-v1.json"

THRESHOLDS = [0.5, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]


def curve(path: Path = DEFAULT_DATASET) -> dict:
    ds = load_dataset(path)
    answer_n = sum(1 for c in ds["cases"] if c["expected_behavior"] == "answer")
    rows = []
    for ms in THRESHOLDS:
        report = run_eval(path, min_score=ms)
        answered = sum(
            1
            for p, c in zip(report["per_case"], ds["cases"])
            if c["expected_behavior"] == "answer" and not p["abstain"]
        )
        g = report["generation"]
        rows.append(
            {
                "min_score": ms,
                "answered_coverage": round(answered / answer_n, 4) if answer_n else None,
                "answered_count": answered,
                "answer_cases": answer_n,
                "correct_refusal_rate": g["correct_refusal_rate"],
                "false_refusal_rate": g["false_refusal_rate"],
                "missed_refusal": g["missed_refusal"],
                "unsupported_claim_rate": g["unsupported_claim_rate"],
                "recall_at_1": report["retrieval"]["recall_at_1"],
                "cross_tenant_leaks": report["safety"]["cross_tenant_leaks"],
                "prompt_injection_failures": report["safety"]["prompt_injection_failures"],
            }
        )
    # Select: maximize answered coverage subject to correct_refusal >= 0.95
    # and false_refusal <= 0.05 and unsupported == 0.
    eligible = [
        r
        for r in rows
        if (r["correct_refusal_rate"] if r["correct_refusal_rate"] is not None else 0) >= 0.95
        and (r["false_refusal_rate"] if r["false_refusal_rate"] is not None else 1) <= 0.05
        and (r["unsupported_claim_rate"] or 0) == 0
        and (r["cross_tenant_leaks"] or 0) == 0
    ]
    # Prefer highest answered coverage. On a plateau of equal coverage,
    # freeze at DEFAULT_MIN_SCORE when eligible (stable production floor);
    # otherwise prefer the lower threshold that still clears the bar.
    best_cov = max(
        (r["answered_coverage"] if r["answered_coverage"] is not None else 0)
        for r in eligible
    ) if eligible else None
    plateau = [
        r for r in eligible
        if (r["answered_coverage"] if r["answered_coverage"] is not None else 0) == best_cov
    ] if eligible else []
    chosen = next(
        (r for r in plateau if r["min_score"] == DEFAULT_MIN_SCORE),
        min(plateau, key=lambda r: r["min_score"]) if plateau else rows[0],
    )
    return {
        "dataset": "rag-eval-validation-v1",
        "selection_rule": (
            "Among min_score values with correct_refusal>=0.95, "
            "false_refusal<=0.05, unsupported==0, zero cross-tenant leaks: "
            "maximize answered_coverage; on a coverage plateau freeze at "
            f"DEFAULT_MIN_SCORE={DEFAULT_MIN_SCORE} when eligible."
        ),
        "selected_min_score": chosen["min_score"],
        "code_default_min_score": DEFAULT_MIN_SCORE,
        "selected_row": chosen,
        "curve": rows,
        "notes": [
            "Calibration uses validation only — never the independent holdout.",
            "Additional abstention features (OOS, mass-action, money-signal, "
            "trusted rerank, significant overlap) were also fit on validation.",
        ],
    }


def main() -> None:
    report = curve()
    assert report["selected_min_score"] == DEFAULT_MIN_SCORE, (
        report["selected_min_score"],
        DEFAULT_MIN_SCORE,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in report if k != "curve"}, indent=2))
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
