"""
Shared scoring for every router in the experiment.

One implementation, used by all four models. A comparison in which each model
brings its own metric code is a comparison of metric code.

Two conventions worth stating because they change the numbers:

  * A prediction of `None` means the router declined to choose — the heuristic
    scoring nothing at all. It counts as an error for accuracy, and it is
    reported separately as `no_evidence_rate`, because "picked the wrong
    department" and "could not pick one" call for different fixes.
  * Macro precision/recall/F1 are averaged over the departments PRESENT IN THE
    LABELS, not over every department the model can emit. Averaging over
    classes that never appear rewards a model for correctly never predicting
    something nobody asked for.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

import numpy as np


@dataclass
class Prediction:
    predicted: str | None
    confidence: float
    ranked: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    #: Full probability vector where the model exposes one, for calibration work.
    proba: dict[str, float] = field(default_factory=dict)


@dataclass
class Metrics:
    model: str
    split: str
    n: int
    accuracy: float
    top2_accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    no_evidence_rate: float
    per_department: dict[str, dict[str, float]]
    confusion: dict[str, dict[str, int]]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_mean_ms: float

    def summary_row(self) -> str:
        return (
            f"{self.model:<22} {self.accuracy * 100:6.1f}%  {self.macro_f1:6.4f}  "
            f"{self.top2_accuracy * 100:6.1f}%  {self.latency_p50_ms:7.2f}  {self.latency_p95_ms:7.2f}"
        )


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(model: str, split: str, labels: Sequence[str], preds: Sequence[Prediction]) -> Metrics:
    assert len(labels) == len(preds), "one prediction per label"
    n = len(labels)
    present = sorted(set(labels))

    correct = sum(1 for y, p in zip(labels, preds) if p.predicted == y)
    top2 = sum(1 for y, p in zip(labels, preds) if y in (p.ranked[:2] or ([p.predicted] if p.predicted else [])))
    no_evidence = sum(1 for p in preds if p.predicted is None)

    per_dept: dict[str, dict[str, float]] = {}
    macro_p = macro_r = macro_f = 0.0
    for dept in present:
        tp = sum(1 for y, p in zip(labels, preds) if y == dept and p.predicted == dept)
        fp = sum(1 for y, p in zip(labels, preds) if y != dept and p.predicted == dept)
        fn = sum(1 for y, p in zip(labels, preds) if y == dept and p.predicted != dept)
        p, r, f = _prf(tp, fp, fn)
        per_dept[dept] = {
            "support": sum(1 for y in labels if y == dept),
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
        }
        macro_p, macro_r, macro_f = macro_p + p, macro_r + r, macro_f + f
    k = len(present) or 1

    confusion: dict[str, dict[str, int]] = {}
    for y, p in zip(labels, preds):
        got = p.predicted or "«no evidence»"
        confusion.setdefault(y, {})
        confusion[y][got] = confusion[y].get(got, 0) + 1

    lat = np.array([p.latency_ms for p in preds], dtype=float)
    return Metrics(
        model=model, split=split, n=n,
        accuracy=round(correct / n, 4),
        top2_accuracy=round(top2 / n, 4),
        macro_precision=round(macro_p / k, 4),
        macro_recall=round(macro_r / k, 4),
        macro_f1=round(macro_f / k, 4),
        no_evidence_rate=round(no_evidence / n, 4),
        per_department=per_dept,
        confusion=confusion,
        latency_p50_ms=round(float(np.percentile(lat, 50)), 4) if n else 0.0,
        latency_p95_ms=round(float(np.percentile(lat, 95)), 4) if n else 0.0,
        latency_mean_ms=round(float(lat.mean()), 4) if n else 0.0,
    )


# --- Selective classification ------------------------------------------------

def risk_coverage(labels: Sequence[str], preds: Sequence[Prediction],
                  thresholds: Sequence[float] | None = None) -> list[dict]:
    """
    Accuracy as a function of how much traffic the router is allowed to decide.

    Abstaining below a confidence threshold trades coverage for accuracy. This
    reports the trade at each threshold so the shape of the curve is visible
    rather than a single operating point being asserted.

    Confidences here are raw model outputs and are NOT calibrated. The curve is
    still meaningful — it only requires that confidence RANKS predictions, not
    that it equals a probability — but no number on it should be read as "the
    model is 90% sure".
    """
    if thresholds is None:
        thresholds = [round(t, 2) for t in np.arange(0.0, 1.0, 0.05)]

    rows: list[dict] = []
    for t in thresholds:
        routed = [(y, p) for y, p in zip(labels, preds) if p.predicted is not None and p.confidence >= t]
        cov = len(routed) / len(labels) if labels else 0.0
        acc = (sum(1 for y, p in routed if p.predicted == y) / len(routed)) if routed else float("nan")
        rows.append({
            "threshold": float(t),
            "coverage": round(cov, 4),
            "routed": len(routed),
            "abstained": len(labels) - len(routed),
            "accuracy_on_routed": (round(acc, 4) if routed else None),
            "errors_on_routed": sum(1 for y, p in routed if p.predicted != y),
        })
    return rows


def coverage_at(labels: Sequence[str], preds: Sequence[Prediction], target_coverage: float) -> dict:
    """Accuracy at (approximately) a chosen coverage level."""
    scored = sorted(
        [(p.confidence, y, p) for y, p in zip(labels, preds) if p.predicted is not None],
        key=lambda x: -x[0],
    )
    k = int(round(target_coverage * len(labels)))
    taken = scored[:k]
    acc = sum(1 for _, y, p in taken if p.predicted == y) / len(taken) if taken else float("nan")
    return {
        "target_coverage": target_coverage,
        "actual_coverage": round(len(taken) / len(labels), 4) if labels else 0.0,
        "accuracy": round(acc, 4) if taken else None,
        "threshold": round(taken[-1][0], 4) if taken else None,
    }


# --- Confidence quality (measurement only, never calibration) ----------------

def confidence_analysis(labels: Sequence[str], preds: Sequence[Prediction], bins: int = 5) -> dict:
    """
    Accuracy by confidence bucket, Brier score and expected calibration error.

    Reported to establish whether these numbers COULD be trusted as
    probabilities. Today they are not, and nothing here adjusts them — that is
    deliberately a later milestone. A model whose ECE is 0.30 is not broken; it
    is uncalibrated, which is the normal state of an un-tuned classifier and
    exactly what this measurement is for.
    """
    conf = np.array([p.confidence for p in preds], dtype=float)
    hit = np.array([1.0 if p.predicted == y else 0.0 for y, p in zip(labels, preds)], dtype=float)

    edges = np.linspace(0.0, 1.0, bins + 1)
    buckets = []
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf >= lo) & (conf < hi if hi < 1.0 else conf <= 1.0)
        count = int(mask.sum())
        if count == 0:
            buckets.append({"range": [round(lo, 2), round(hi, 2)], "count": 0,
                            "mean_confidence": None, "accuracy": None})
            continue
        mean_conf = float(conf[mask].mean())
        acc = float(hit[mask].mean())
        ece += (count / len(conf)) * abs(acc - mean_conf)
        buckets.append({"range": [round(lo, 2), round(hi, 2)], "count": count,
                        "mean_confidence": round(mean_conf, 4), "accuracy": round(acc, 4)})

    # Brier over the top-1 confidence treated as P(correct) — the one-vs-rest
    # form, which is what a router's abstention threshold actually consumes.
    brier = float(np.mean((conf - hit) ** 2))
    return {
        "note": "UNCALIBRATED. Reported to measure calibration quality, not to assert it.",
        "buckets": buckets,
        "brier_score_top1": round(brier, 4),
        "expected_calibration_error": round(float(ece), 4),
        "mean_confidence_when_correct": round(float(conf[hit == 1].mean()), 4) if hit.sum() else None,
        "mean_confidence_when_wrong": round(float(conf[hit == 0].mean()), 4) if (1 - hit).sum() else None,
    }


def timed(fn: Callable[[str], Prediction], asks: Sequence[str]) -> list[Prediction]:
    """Run a single-ask predictor, recording per-call wall time."""
    out: list[Prediction] = []
    for ask in asks:
        t0 = time.perf_counter()
        pred = fn(ask)
        pred.latency_ms = (time.perf_counter() - t0) * 1000
        out.append(pred)
    return out


def print_confusion(m: Metrics) -> None:
    print(f"\nConfusion — {m.model} on {m.split} (expected -> predicted):")
    for expected in sorted(m.confusion):
        got = sorted(m.confusion[expected].items(), key=lambda kv: -kv[1])
        line = "  ".join(f"{k}:{v}" for k, v in got)
        print(f"  {expected:<18} {line}")


def metrics_to_dict(m: Metrics) -> dict:
    return asdict(m)


if __name__ == "__main__":
    print(json.dumps({"module": "evaluate", "usage": "imported by the train_* scripts"}, indent=2))
