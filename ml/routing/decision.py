"""
One auditable routing decision, and the cascades that produce them.

Milestone 5 compared routers by their accuracy. That is enough to rank them and
not nearly enough to run one: when a route turns out wrong, "the hybrid picked
Sales" does not say whether the heuristic was confident and mistaken, whether
the heuristic was silent and TF-IDF guessed, or whether both were uncertain and
nobody escalated. Those three have different fixes. `RouterDecision` is the
record that tells them apart.

The shape (brief §13):

    department              what was chosen, or None if the router abstained
    source                  which stage actually decided
    raw_score               that stage's own number, on that stage's own scale
    calibrated_confidence   the comparable number, or None when uncalibrated
    alternates              runners-up, for the clarification prompt
    abstained               True when no department was chosen
    escalation_reason       why control left the previous stage

`raw_score` is never overwritten by the calibrated value. They answer different
questions — "how much evidence did this stage have" versus "how often is this
stage right when it says that" — and collapsing them into one field is how a
system loses the ability to explain itself. The heuristic's 3.0 and TF-IDF's
0.42 are not comparable and are not stored as though they were.

--- The cascades -------------------------------------------------------------

Six architectures, A-F, matching the brief. Each is a `Cascade`: an ordered list
of stages plus the gate that decides whether a stage's answer is good enough to
stop at. The gates are deterministic and are taken from production code where
production has an opinion (`MIN_BUSINESS_EVIDENCE`), not tuned to make a
favoured architecture win.

--- What this module must never do -------------------------------------------

Choose a department, and stop. Approval, risk level, tool selection, tenant
scope, verification and destructive-action refusal are decided downstream by the
action executor, which never reads any of this. A `RouterDecision` with
confidence 1.0 buys exactly as much authority as one with confidence 0.01:
namely, which of eight departments gets to draft a reply.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

from evaluate import Prediction

#: The orchestrator's routing floor, read from `_orchestrator.ts`. Below this a
#: department has matched a generic intent and nothing about WHICH business
#: function the ask belongs to, and the shipped system does not route on it.
#: Milestone 6 sweeps alternatives (see policy.evidence_floor_sweep) but the
#: default stays whatever production does.
MIN_BUSINESS_EVIDENCE = 3.0

#: How close the runner-up must be, as a share of the leader's evidence, before
#: the two count as indistinguishable and the owner is asked. Also from
#: `_orchestrator.ts` (`RESOLUTION_RATIO`).
RESOLUTION_RATIO = 0.85


@dataclass
class RouterDecision:
    """One routing decision, with enough provenance to audit it after the fact."""

    department: str | None
    source: str
    raw_score: float | None
    #: The deciding stage's own top-1 confidence, always in [0, 1].
    #:
    #: Distinct from `raw_score`, which for the heuristic is an unbounded
    #: EVIDENCE score (2, 8, 17...). Both are needed: `raw_score` is what the
    #: orchestrator's floor and ambiguity tests read, and this is the only one
    #: of the two that can stand in for a probability when no calibrator exists.
    #: Conflating them lets an evidence score of 8.0 be sorted as though it were
    #: a confidence, which silently ranks every heuristic-decided case above
    #: every other case in a risk/coverage curve.
    source_confidence: float = 0.0
    calibrated_confidence: float | None = None
    alternates: list[str] = field(default_factory=list)
    abstained: bool = False
    escalation_reason: str | None = None
    #: Which stages ran, in order. `["heuristic", "tfidf"]` means the heuristic
    #: was consulted, declined, and TF-IDF answered.
    stages_used: list[str] = field(default_factory=list)
    #: Wall time attributable to this decision, summed over the stages that ran.
    latency_ms: float = 0.0
    #: Per-stage raw numbers, kept separately and never merged. This is what
    #: makes "the heuristic was confident and wrong" distinguishable from "the
    #: heuristic was silent".
    stage_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# --- Stages ------------------------------------------------------------------

@dataclass(frozen=True)
class Stage:
    """
    One router in a cascade.

    `accepts(prediction, index)` decides whether this stage's answer is good
    enough to stop at. It takes the case index explicitly so it stays a PURE
    function: a gate that consulted a per-instance side table by incrementing an
    internal counter would give different answers depending on how many times
    the stage had been asked before, and this Stage is deliberately reused
    across the cascade run and the escalation-rate calculation.
    """

    name: str
    predictions: list[Prediction]
    accepts: Callable[[Prediction, int], bool]
    #: Why control moved past this stage, recorded on the decision when it does.
    escalation_reason: str
    #: Marginal monetary cost of consulting this stage, per call, in USD.
    cost_per_call_usd: float = 0.0
    #: Calibrated top-1 confidences, aligned with `predictions`, where a
    #: calibrator has been fitted for this stage. None means uncalibrated, and
    #: the decision then carries `calibrated_confidence: None` rather than a
    #: raw number wearing a calibrated label.
    calibrated: Sequence[float] | None = None


def heuristic_accepts(min_evidence: float = MIN_BUSINESS_EVIDENCE) -> Callable[[Prediction], bool]:
    """
    Production's own acceptance test: a department with at least `min_evidence`
    raw score. Deliberately NOT a confidence threshold — `score/(score+2)`
    saturates, so a confidence cut and an evidence cut select different cases,
    and the evidence cut is the one the shipped orchestrator makes.
    """
    def accepts(p: Prediction, i: int) -> bool:
        return p.predicted is not None and p.proba.get("_score", 0.0) >= min_evidence
    return accepts


def confidence_accepts(threshold: float, calibrated: Sequence[float] | None = None) -> Callable[[Prediction, int], bool]:
    """
    Accept when the stage's confidence clears a threshold.

    Uses the CALIBRATED confidence when one is supplied. This is exactly the
    comparison the brief warns about: a bare `conf > x` rule written against a
    raw logistic-regression probability is a threshold on an arbitrary scale.
    After calibration the number means "how often predictions like this are
    right", and a threshold on it is a statement about acceptable risk.
    """
    def accepts(p: Prediction, i: int) -> bool:
        if p.predicted is None:
            return False
        value = calibrated[i] if calibrated is not None else p.confidence
        return value >= threshold
    return accepts


def always_accepts(p: Prediction, i: int) -> bool:
    """Accept anything with a prediction. The terminal stage of a cascade."""
    return p.predicted is not None


# --- Cascade -----------------------------------------------------------------

@dataclass
class Cascade:
    name: str
    stages: list[Stage]
    #: When every stage declines, ask the owner rather than routing on nothing.
    #: This is the abstention arm, and its rate is a first-class product metric:
    #: a router that reaches high accuracy by asking about half of all requests
    #: has moved the work to the owner, not done it.
    clarify_on_exhaustion: bool = True

    def decide(self, i: int) -> RouterDecision:
        """Run case `i` through the cascade and record how it was decided."""
        stages_used: list[str] = []
        stage_scores: dict[str, float] = {}
        latency = 0.0
        reason: str | None = None
        alternates: list[str] = []

        for stage in self.stages:
            p = stage.predictions[i]
            stages_used.append(stage.name)
            latency += p.latency_ms
            stage_scores[stage.name] = round(
                float(p.proba.get("_score", p.confidence)) if stage.name == "heuristic" else float(p.confidence), 4
            )
            if stage.accepts(p, i):
                cal = float(stage.calibrated[i]) if stage.calibrated is not None else None
                return RouterDecision(
                    department=p.predicted,
                    source=stage.name,
                    raw_score=stage_scores[stage.name],
                    source_confidence=float(p.confidence),
                    calibrated_confidence=cal,
                    alternates=[a for a in p.ranked[1:3] if a != p.predicted],
                    abstained=False,
                    escalation_reason=reason,
                    stages_used=stages_used,
                    latency_ms=round(latency, 4),
                    stage_scores=stage_scores,
                )
            reason = stage.escalation_reason
            if p.predicted is not None and not alternates:
                alternates = [p.predicted]

        return RouterDecision(
            department=None,
            source="owner_clarification",
            raw_score=None,
            calibrated_confidence=None,
            alternates=alternates,
            abstained=True,
            escalation_reason=reason or "every stage declined",
            stages_used=stages_used,
            latency_ms=round(latency, 4),
            stage_scores=stage_scores,
        )

    def run(self, n: int) -> list[RouterDecision]:
        return [self.decide(i) for i in range(n)]


# --- Utilisation -------------------------------------------------------------

def utilisation(decisions: Sequence[RouterDecision], labels: Sequence[str]) -> dict:
    """
    Who handled what, and how well (brief §10).

    Reports, per source: the share of traffic it decided, its accuracy on that
    share, and the share that reached it at all. The last is the cost driver —
    an LLM stage that is *reached* by 30% of traffic costs 30% of the call
    volume even if it only *decides* 8%, because a stage that declines has
    already been paid for.
    """
    n = len(decisions)
    if n == 0:
        return {"n": 0}

    by_source: dict[str, dict] = {}
    for d, y in zip(decisions, labels):
        row = by_source.setdefault(d.source, {"handled": 0, "correct": 0})
        row["handled"] += 1
        if d.department == y:
            row["correct"] += 1

    reached: dict[str, int] = {}
    for d in decisions:
        for s in d.stages_used:
            reached[s] = reached.get(s, 0) + 1

    routed = [(d, y) for d, y in zip(decisions, labels) if not d.abstained]
    clarified = sum(1 for d in decisions if d.abstained)

    return {
        "n": n,
        "by_source": {
            src: {
                "handled": r["handled"],
                "share": round(r["handled"] / n, 4),
                "accuracy": (round(r["correct"] / r["handled"], 4) if r["handled"] else None),
            }
            for src, r in sorted(by_source.items(), key=lambda kv: -kv[1]["handled"])
        },
        "reached_by_stage": {s: {"count": c, "share": round(c / n, 4)} for s, c in reached.items()},
        "coverage": round(len(routed) / n, 4),
        "owner_clarification_rate": round(clarified / n, 4),
        "accuracy_on_routed": (round(sum(1 for d, y in routed if d.department == y) / len(routed), 4)
                               if routed else None),
        "end_to_end_accuracy": round(sum(1 for d, y in zip(decisions, labels) if d.department == y) / n, 4),
        "latency_p50_ms": _pct([d.latency_ms for d in decisions], 50),
        "latency_p95_ms": _pct([d.latency_ms for d in decisions], 95),
    }


def _pct(values: Sequence[float], q: int) -> float:
    import numpy as np
    return round(float(np.percentile(np.asarray(values, dtype=float), q)), 4) if len(values) else 0.0


def to_predictions(decisions: Sequence[RouterDecision]) -> list[Prediction]:
    """
    Adapt cascade output back to `Prediction` so the shared scorer in
    `evaluate.py` measures cascades with exactly the code it measures single
    routers with. One metric implementation, or the comparison degenerates into
    a comparison of metric implementations.

    An abstention becomes `predicted=None`, which `evaluate.score` already
    counts as an error and reports separately as `no_evidence_rate`. That is the
    honest treatment: asking the owner is not a correct route, and it is also
    not the same failure as routing to the wrong department.

    The confidence carried forward is the calibrated one where it exists and the
    deciding stage's own confidence otherwise — never `raw_score`, which for a
    heuristic decision is an unbounded evidence score and would sort ahead of
    every genuine probability in a risk/coverage curve.
    """
    out: list[Prediction] = []
    for d in decisions:
        conf = d.calibrated_confidence if d.calibrated_confidence is not None else d.source_confidence
        out.append(Prediction(
            predicted=d.department,
            confidence=float(conf) if d.department else 0.0,
            ranked=([d.department] + d.alternates) if d.department else [],
            latency_ms=d.latency_ms,
            proba=dict(d.stage_scores),
        ))
    return out
