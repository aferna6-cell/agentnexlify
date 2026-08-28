"""
Score every router on one split with one metric implementation.

Model D (LLM) is included only when a credential exists. Where it does not, it
appears in the table as "not measured" with its estimated cost rather than as a
blank or, worse, a number carried over from somewhere else.

    python compare.py --split validation
    python compare.py --split test        # ONCE, at the end of the experiment
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn

import datasets
import heuristic
from evaluate import (Prediction, confidence_analysis, coverage_at, metrics_to_dict,
                      print_confusion, risk_coverage, score)

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
REPO = Path(__file__).resolve().parents[2]


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def tfidf_predictions(asks: list[str]) -> list[Prediction]:
    from train_tfidf import predictions_from
    return predictions_from(joblib.load(ARTIFACTS / "tfidf.joblib"), asks)


def embedding_predictions(asks: list[str]) -> list[Prediction]:
    from train_embeddings import _encoder, predictions_from
    return predictions_from(joblib.load(ARTIFACTS / "embedding_lr.joblib"), _encoder(), asks)


#: The orchestrator's own routing floor (`MIN_BUSINESS_EVIDENCE` in
#: `_orchestrator.ts`). Below this the shipped system does not route at all, so
#: this — not zero — is the boundary of the heuristic's silence. Taken from
#: production code rather than tuned against any split.
MIN_BUSINESS_EVIDENCE = 3.0


def hybrid_predictions(base: list[Prediction], fallback: list[Prediction],
                       min_score: float = MIN_BUSINESS_EVIDENCE) -> list[Prediction]:
    """
    Model E — the heuristic, with an ML model answering only where it cannot.

    This is the architecture the error analysis actually points at. The
    Milestone-4 heuristic is precise where it fires; its documented failure is
    that on 24 of 42 remaining frozen routing errors NOTHING scored at all. A
    model that replaces the heuristic must beat it everywhere; a model that
    covers only its silence has to beat nothing — it only has to be better than
    no answer.

    Latency is additive only on the cases that fall through, which is the other
    reason this shape is attractive: the common path stays at heuristic speed.
    """
    out: list[Prediction] = []
    for h, f in zip(base, fallback):
        if h.predicted is not None and h.proba.get("_score", 0.0) >= min_score:
            out.append(h)
        else:
            out.append(Prediction(
                predicted=f.predicted, confidence=f.confidence, ranked=f.ranked,
                latency_ms=h.latency_ms + f.latency_ms, proba=f.proba,
            ))
    return out


def llm_predictions(asks: list[str]) -> tuple[list[Prediction] | None, dict]:
    """Live LLM predictions, or None plus the reason and the cost estimate."""
    payload = "\n".join(json.dumps({"ask": a}) for a in asks) + "\n"
    proc = subprocess.run(
        ["node", "--experimental-strip-types", "evals/export-llm-predictions.ts"],
        input=payload, capture_output=True, text=True, cwd=REPO / "agent-service", check=True,
    )
    first = proc.stdout.lstrip()[:1]
    if first == "{":  # estimate object: no credential
        return None, json.loads(proc.stdout)

    preds, malformed = [], 0
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["fallback_would_be_used"]:
            malformed += 1
        preds.append(Prediction(
            predicted=row["llm_predicted"], confidence=float(row["confidence"]),
            ranked=row["ranked"], latency_ms=float(row["latency_ms"]),
        ))
    summary = json.loads(proc.stderr.strip().splitlines()[-1]) if proc.stderr.strip() else {}
    summary["malformed_or_unmapped"] = malformed
    return preds, summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test"], default="validation")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    split = datasets.load_validation() if args.split == "validation" else datasets.load_test()
    if args.split == "test":
        print("!! FROZEN TEST SPLIT — this is the final measurement, not an iteration step.\n")
    print(f"split: {split.name} ({split.version}), {len(split)} cases with a department label\n")

    runs: dict[str, list[Prediction]] = {}
    t0 = time.perf_counter(); runs["Heuristic (prod)"] = heuristic.predict(split.asks)
    print(f"heuristic  {time.perf_counter() - t0:.1f}s")
    t0 = time.perf_counter(); runs["TF-IDF + LR"] = tfidf_predictions(split.asks)
    print(f"tfidf      {time.perf_counter() - t0:.1f}s")
    t0 = time.perf_counter(); runs["Embedding + LR"] = embedding_predictions(split.asks)
    print(f"embedding  {time.perf_counter() - t0:.1f}s")

    runs["Hybrid: heur -> TF-IDF"] = hybrid_predictions(runs["Heuristic (prod)"], runs["TF-IDF + LR"])
    runs["Hybrid: heur -> Embed"] = hybrid_predictions(runs["Heuristic (prod)"], runs["Embedding + LR"])

    llm_preds, llm_info = llm_predictions(split.asks)
    if llm_preds is not None:
        runs["LLM (Haiku)"] = llm_preds
        print(f"llm        measured, malformed {llm_info.get('malformed_or_unmapped')}")
    else:
        print(f"llm        NOT MEASURED (no credential); est ${llm_info['approx_cost_usd_per_1k_calls']}/1k")

    print(f"\n{'model':<22} {'acc':>7}  {'macroF1':>7}  {'top2':>7}  {'p50ms':>7}  {'p95ms':>7}")
    metrics = {}
    for name, preds in runs.items():
        m = score(name, split.name, split.labels, preds)
        metrics[name] = m
        print(m.summary_row())

    for name, m in metrics.items():
        print_confusion(m)

    print("\nPer-department F1:")
    depts = sorted({d for m in metrics.values() for d in m.per_department})
    print(f"  {'department':<18} " + "  ".join(f"{n[:14]:>14}" for n in metrics))
    for d in depts:
        cells = []
        for m in metrics.values():
            pd = m.per_department.get(d)
            cells.append(f"{pd['f1']:>14.3f}" if pd else f"{'-':>14}")
        support = next((m.per_department[d]["support"] for m in metrics.values() if d in m.per_department), 0)
        print(f"  {d:<18} " + "  ".join(cells) + f"   (n={int(support)})")

    print("\nRisk / coverage (accuracy on the subset the router is allowed to decide):")
    for name, preds in runs.items():
        cells = [coverage_at(split.labels, preds, c) for c in (0.95, 0.9, 0.8, 0.7)]
        line = "  ".join(
            f"{int(c['target_coverage'] * 100)}%:{'n/a' if c['accuracy'] is None else format(c['accuracy'] * 100, '.1f') + '%'}"
            for c in cells
        )
        print(f"  {name:<22} {line}")

    payload = {
        "split": split.name,
        "split_version": split.version,
        "cases": len(split),
        "git_sha": git_sha(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "seed": 20260828,
        },
        "train_version": datasets.TRAIN_VERSION,
        "models": {name: metrics_to_dict(m) for name, m in metrics.items()},
        "risk_coverage": {name: risk_coverage(split.labels, p) for name, p in runs.items()},
        "confidence": {name: confidence_analysis(split.labels, p) for name, p in runs.items()},
        "llm": ({"measured": True, **llm_info} if llm_preds is not None
                else {"measured": False, "reason": "no ANTHROPIC_API_KEY in this environment", **llm_info}),
        "per_case": [
            {"id": (split.ids[i] if split.ids else None), "ask": split.asks[i], "expected": split.labels[i],
             **{name: {"predicted": p[i].predicted, "confidence": round(p[i].confidence, 4)} for name, p in runs.items()}}
            for i in range(len(split))
        ],
    }
    out = Path(args.out) if args.out else ARTIFACTS / f"comparison-{split.name}.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"\nwritten -> {out}")


if __name__ == "__main__":
    main()
