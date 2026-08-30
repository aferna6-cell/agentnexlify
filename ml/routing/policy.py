"""
Turning measurements into a routing policy.

Accuracy alone cannot choose a router, because the four things a router can do
with a request do not cost the same:

    route locally and correctly     ~0.03 ms, $0
    fall through to TF-IDF          ~0.3 ms,  $0
    escalate to the LLM             ~500 ms,  ~$0.001
    ask the owner                   unbounded, and it is the owner's time

The first three are objectively measurable and are measured. The fourth is not
reducible to a number: what a clarification costs depends on whether the owner
is standing at a lift with oily hands or sitting at a desk, and any dollar
figure put on it here would be invented. So it is reported as its own axis and
the trade is shown rather than solved (brief §9).

That is why the output of this module is a Pareto front and not a winner. Where
one architecture dominates another on every axis, this says so. Where it does
not, it says that too, and the choice belongs to whoever owns the product.

Three analyses live here:

  risk_coverage_table   accuracy as a function of how much traffic the router is
                        allowed to decide. A router reaching 98% by asking about
                        half of all requests is visible here and invisible in a
                        single accuracy number.
  low_evidence_report   the same comparison restricted to the region below the
                        production evidence floor. Milestone 5 showed the hybrid
                        wins *there*; pooling that region with the easy one lets
                        184 easy cases drown the 30 that decide the architecture.
  evidence_floor_sweep  MIN_BUSINESS_EVIDENCE is a production constant that has
                        never been measured. This measures it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from decision import (Cascade, RouterDecision, Stage, always_accepts,
                      heuristic_accepts, utilisation)
from evaluate import Prediction

#: Published Haiku pricing, per million tokens. Used only to convert a measured
#: token count into dollars; no token count is invented from it.
HAIKU_USD_PER_MTOK_IN = 1.00
HAIKU_USD_PER_MTOK_OUT = 5.00


# --- Risk / coverage ---------------------------------------------------------

def risk_coverage_table(
    labels: Sequence[str],
    preds: Sequence[Prediction],
    coverages: Sequence[float] = (1.0, 0.95, 0.90, 0.85, 0.80, 0.70),
) -> list[dict]:
    """
    Accuracy at a series of coverage levels (brief §8).

    Predictions are ranked by confidence and the top `c` fraction taken; the
    rest are treated as abstentions. This measures whether the confidence signal
    ORDERS predictions usefully — which is a weaker and more robust property
    than calibration, and the one selective routing actually depends on.

    `risk` is the error rate among the requests the router was allowed to
    decide. It is the number a product owner cares about: of the things we did
    without asking, how many did we get wrong.
    """
    scored = sorted(
        [(p.confidence, y, p.predicted) for y, p in zip(labels, preds) if p.predicted is not None],
        key=lambda t: -t[0],
    )
    n = len(labels)
    rows: list[dict] = []
    for c in coverages:
        k = int(round(c * n))
        taken = scored[:k]
        if not taken:
            rows.append({"target_coverage": c, "actual_coverage": 0.0, "n_routed": 0,
                         "accuracy": None, "risk": None, "threshold": None})
            continue
        correct = sum(1 for _, y, pr in taken if pr == y)
        acc = correct / len(taken)
        rows.append({
            "target_coverage": c,
            "actual_coverage": round(len(taken) / n, 4),
            "n_routed": len(taken),
            "accuracy": round(acc, 4),
            "risk": round(1 - acc, 4),
            "errors": len(taken) - correct,
            "threshold": round(taken[-1][0], 4),
        })
    return rows


# --- Cost model --------------------------------------------------------------

@dataclass(frozen=True)
class CostProfile:
    """
    What one architecture costs to run 1,000 requests, on axes that can be
    measured. Owner clarifications are counted, never priced.
    """

    name: str
    llm_calls_per_1k: float
    usd_per_1k: float
    clarifications_per_1k: float
    routing_error_per_1k: float
    latency_p50_ms: float
    latency_p95_ms: float
    #: True when any component of this profile could not be measured in this
    #: environment. A profile carrying an unmeasured component is never compared
    #: against a measured one as though both were facts.
    complete: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "architecture": self.name,
            "llm_calls_per_1k": round(self.llm_calls_per_1k, 1),
            "usd_per_1k": round(self.usd_per_1k, 4),
            "clarifications_per_1k": round(self.clarifications_per_1k, 1),
            "routing_errors_per_1k": round(self.routing_error_per_1k, 1),
            "latency_p50_ms": round(self.latency_p50_ms, 3),
            "latency_p95_ms": round(self.latency_p95_ms, 3),
            "measured": self.complete,
            "note": self.note,
        }


def cost_profile(name: str, decisions: Sequence[RouterDecision], labels: Sequence[str],
                 llm_stage_name: str = "llm", usd_per_llm_call: float = 0.0,
                 complete: bool = True, note: str = "") -> CostProfile:
    u = utilisation(decisions, labels)
    n = u["n"]
    llm_reached = u["reached_by_stage"].get(llm_stage_name, {"count": 0})["count"]
    errors = sum(1 for d, y in zip(decisions, labels) if not d.abstained and d.department != y)
    return CostProfile(
        name=name,
        llm_calls_per_1k=1000 * llm_reached / n,
        usd_per_1k=1000 * llm_reached * usd_per_llm_call / n,
        clarifications_per_1k=1000 * u["owner_clarification_rate"],
        routing_error_per_1k=1000 * errors / n,
        latency_p50_ms=u["latency_p50_ms"],
        latency_p95_ms=u["latency_p95_ms"],
        complete=complete,
        note=note,
    )


#: The axes a routing policy trades against, and the direction that is better.
#: All four are minimised. Downstream task error is added by the caller when an
#: end-to-end run is available, because it cannot be computed from routing alone.
PARETO_AXES = ("routing_errors_per_1k", "clarifications_per_1k", "usd_per_1k", "latency_p95_ms")


def pareto_front(profiles: Sequence[CostProfile], axes: Sequence[str] = PARETO_AXES) -> dict:
    """
    Which architectures are not beaten on every axis at once.

    A profile is dominated when another is at least as good on every axis and
    strictly better on one. Everything left is a real choice, and presenting
    those choices — rather than collapsing them with invented weights — is the
    honest output when one of the axes (owner friction) has no defensible price.
    """
    rows = [p.to_dict() for p in profiles]
    # An architecture with an unmeasured component is held out of the dominance
    # comparison entirely. NaN compares False against everything, so leaving one
    # in would make it appear undominated — it would join the Pareto front by
    # virtue of not having been measured, which is the opposite of evidence.
    comparable = [r for r in rows if r["measured"]]
    excluded = [r for r in rows if not r["measured"]]

    def dominates(a: dict, b: dict) -> bool:
        return (all(a[k] <= b[k] for k in axes) and any(a[k] < b[k] for k in axes))

    front, dominated = [], []
    for r in comparable:
        losers = [o for o in comparable if o is not r and dominates(o, r)]
        (dominated if losers else front).append({
            "architecture": r["architecture"],
            **{k: r[k] for k in axes},
            "dominated_by": [o["architecture"] for o in losers] or None,
            "measured": True,
        })
    return {
        "not_comparable": [
            {"architecture": r["architecture"],
             "llm_calls_per_1k": r["llm_calls_per_1k"], "usd_per_1k": r["usd_per_1k"],
             "measured": False, "note": r["note"]}
            for r in excluded
        ],
        "axes": list(axes),
        "note": (
            "All axes are minimised. Owner clarifications are COUNTED, never priced: "
            "the cost of interrupting an owner is not reducible to a dollar figure and "
            "inventing one would decide the trade-off by assumption rather than by evidence."
        ),
        "pareto_front": sorted(front, key=lambda r: r["routing_errors_per_1k"]),
        "dominated": sorted(dominated, key=lambda r: r["routing_errors_per_1k"]),
    }


# --- Low-evidence region -----------------------------------------------------

def low_evidence_mask(heuristic_preds: Sequence[Prediction],
                      floor: float = 3.0) -> np.ndarray:
    """
    The cases production would not route on: heuristic evidence below the floor,
    including the ones where nothing scored at all.
    """
    return np.array(
        [(p.predicted is None) or (p.proba.get("_score", 0.0) < floor) for p in heuristic_preds],
        dtype=bool,
    )


def low_evidence_report(labels: Sequence[str], runs: dict[str, list[Prediction]],
                        heuristic_preds: Sequence[Prediction], floor: float = 3.0) -> dict:
    """
    Every router's accuracy restricted to the region the heuristic cannot serve
    (brief §11).

    This is the region the production architecture actually needs help in. The
    high-evidence region is where the heuristic already wins and where any
    reasonable model looks fine; letting those cases into the headline number
    is how a comparison ends up dominated by the cases that were never in
    question.
    """
    from evaluate import score

    mask = low_evidence_mask(heuristic_preds, floor)
    idx = np.flatnonzero(mask)
    hi = np.flatnonzero(~mask)
    sub_labels = [labels[i] for i in idx]

    out: dict = {
        "floor": floor,
        "n_total": len(labels),
        "n_low_evidence": int(mask.sum()),
        "share_low_evidence": round(float(mask.mean()), 4),
        "n_no_candidate_at_all": int(sum(1 for p in heuristic_preds if p.predicted is None)),
        "models": {},
        "high_evidence_models": {},
    }
    if len(idx) == 0:
        out["note"] = "no case fell below the floor on this split"
        return out

    for name, preds in runs.items():
        m = score(name, "low_evidence", sub_labels, [preds[i] for i in idx])
        out["models"][name] = {
            "accuracy": m.accuracy, "macro_f1": m.macro_f1,
            "top2_accuracy": m.top2_accuracy, "no_evidence_rate": m.no_evidence_rate,
            "n": m.n,
        }
        if len(hi):
            mh = score(name, "high_evidence", [labels[i] for i in hi], [preds[i] for i in hi])
            out["high_evidence_models"][name] = {"accuracy": mh.accuracy, "macro_f1": mh.macro_f1, "n": mh.n}
    return out


# --- Evidence-floor sweep ----------------------------------------------------

def evidence_floor_sweep(
    labels: Sequence[str],
    heuristic_preds: list[Prediction],
    fallback_preds: list[Prediction],
    floors: Sequence[float] = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
    fallback_name: str = "tfidf",
) -> list[dict]:
    """
    What each candidate value of MIN_BUSINESS_EVIDENCE would buy (brief §12).

    The floor decides how much traffic the heuristic keeps. Raise it and more
    requests fall through to the fallback: coverage of the deterministic path
    drops, the fallback's error becomes a larger share of the total, and — in a
    cascade whose fallback is an LLM — the bill rises. Lower it and the
    heuristic answers on evidence too thin to mean anything.

    Measured on validation only. The existing value is not assumed optimal and
    is not protected; it also is not replaced on a small gain, because a
    threshold moved on 184 hand-written sentences is a threshold fitted to 184
    hand-written sentences.
    """
    rows: list[dict] = []
    for floor in floors:
        stages = [
            Stage("heuristic", heuristic_preds, heuristic_accepts(floor), "heuristic_below_floor"),
            Stage(fallback_name, fallback_preds, always_accepts, "fallback_had_no_answer"),
        ]
        decisions = Cascade(f"floor={floor}", stages).run(len(labels))
        u = utilisation(decisions, labels)
        kept = u["by_source"].get("heuristic", {"share": 0.0, "accuracy": None})
        fell = u["by_source"].get(fallback_name, {"share": 0.0, "accuracy": None})
        rows.append({
            "floor": floor,
            "heuristic_share": kept["share"],
            "heuristic_accuracy": kept["accuracy"],
            "fallback_share": fell["share"],
            "fallback_accuracy": fell["accuracy"],
            "owner_clarification_rate": u["owner_clarification_rate"],
            "end_to_end_accuracy": u["end_to_end_accuracy"],
        })
    return rows


def stress_breakdown(labels: Sequence[str], preds: Sequence[Prediction],
                     stress: Sequence[str | None]) -> dict:
    """
    Accuracy by the routing boundary each case was written to probe.

    A pooled accuracy of 85% can be 98% on the easy region and 40% on the region
    that decides the architecture. This is the split that shows which.
    """
    buckets: dict[str, dict] = {}
    for y, p, s in zip(labels, preds, stress):
        key = s or "unlabelled"
        b = buckets.setdefault(key, {"n": 0, "correct": 0, "abstained": 0})
        b["n"] += 1
        if p.predicted == y:
            b["correct"] += 1
        if p.predicted is None:
            b["abstained"] += 1
    return {
        k: {"n": v["n"], "accuracy": round(v["correct"] / v["n"], 4),
            "abstention_rate": round(v["abstained"] / v["n"], 4)}
        for k, v in sorted(buckets.items(), key=lambda kv: kv[1]["n"], reverse=True)
    }


def abstention_sweep(
    labels: Sequence[str],
    heuristic_preds: list[Prediction],
    fallback_preds: list[Prediction],
    calibrated: Sequence[float] | None,
    floor: float = 3.0,
    thresholds: Sequence[float] = (0.0, 0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9),
) -> list[dict]:
    """
    What each abstention threshold buys, for a heuristic -> fallback -> owner cascade.

    This is the risk/coverage trade in the form the product actually faces:
    raising the bar sends more requests to the owner and makes the router more
    often right about the ones it keeps. Both directions are costly, and neither
    cost is denominated in the other, so the table is the deliverable and the
    single chosen threshold is only one row of it.
    """
    from decision import Cascade, Stage, confidence_accepts, heuristic_accepts

    rows: list[dict] = []
    for t in thresholds:
        stages = [
            Stage("heuristic", heuristic_preds, heuristic_accepts(floor), "heuristic_below_floor"),
            Stage("fallback", fallback_preds, confidence_accepts(t, calibrated),
                  "fallback_below_abstention_threshold"),
        ]
        decisions = Cascade(f"abstain<{t}", stages).run(len(labels))
        u = utilisation(decisions, labels)
        rows.append({
            "abstain_below_calibrated": t,
            "coverage": u["coverage"],
            "owner_clarification_rate": u["owner_clarification_rate"],
            "accuracy_on_routed": u["accuracy_on_routed"],
            "risk_on_routed": (round(1 - u["accuracy_on_routed"], 4)
                               if u["accuracy_on_routed"] is not None else None),
            "end_to_end_accuracy": u["end_to_end_accuracy"],
        })
    return rows
