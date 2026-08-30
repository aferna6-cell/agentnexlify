"""
Tests for the Milestone-6 routing machinery.

These target the properties that, if broken, would produce a plausible-looking
number that is wrong — which is the only kind of bug that matters in an
experiment whose whole output is numbers.

    python -m pytest ml/routing/tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calibration  # noqa: E402
import leakage  # noqa: E402
from datasets import Split  # noqa: E402
from decision import (Cascade, Stage, always_accepts, confidence_accepts,  # noqa: E402
                      heuristic_accepts, to_predictions, utilisation)
from evaluate import Prediction  # noqa: E402


def pred(dept, conf=0.5, score=None, ranked=None, latency=1.0):
    proba = {"_score": score} if score is not None else {}
    return Prediction(predicted=dept, confidence=conf, ranked=ranked or ([dept] if dept else []),
                      latency_ms=latency, proba=proba)


# --- Calibration -------------------------------------------------------------

class TestCalibration:
    def test_perfectly_calibrated_input_has_near_zero_ece(self):
        rng = np.random.default_rng(0)
        conf = rng.uniform(0.05, 0.95, 4000)
        correct = (rng.uniform(size=4000) < conf).astype(int)
        assert calibration.expected_calibration_error(conf, correct) < 0.03

    def test_overconfident_input_has_large_ece(self):
        conf = np.full(500, 0.95)
        correct = np.zeros(500, dtype=int)
        correct[:250] = 1  # 50% accurate while claiming 95%
        assert calibration.expected_calibration_error(conf, correct) == pytest.approx(0.45, abs=0.01)

    def test_platt_fixes_a_systematically_overconfident_router(self):
        rng = np.random.default_rng(1)
        n = 600
        conf = rng.uniform(0.6, 1.0, n)
        # True accuracy is far below the stated confidence.
        correct = (rng.uniform(size=n) < conf * 0.6).astype(int)
        r = calibration.cross_fitted("platt", conf, correct)
        assert r.usable
        assert r.ece_out_of_fold < r.ece_raw, "calibration should reduce out-of-fold ECE here"

    def test_cross_fitting_reports_isotonic_overfitting_rather_than_hiding_it(self):
        # Confidence carries no signal at all: nothing is learnable, so a
        # flexible fit can only memorise. In-fold ECE collapses to ~0 while
        # out-of-fold does not, and the gap is what exposes it.
        rng = np.random.default_rng(2)
        n = 120
        conf = rng.uniform(0, 1, n)
        correct = rng.integers(0, 2, n)
        r = calibration.cross_fitted("isotonic", conf, correct)
        assert r.ece_in_fold < 0.01
        assert r.overfit_gap > 0.02, "the in-fold/out-of-fold gap must expose memorisation"

    def test_selection_rejects_a_calibrator_that_overfits(self):
        results = {
            "identity": calibration.CalibrationResult(
                method="identity", n=100, folds=5, calibrated=np.zeros(1), ece_out_of_fold=0.10),
            "isotonic": calibration.CalibrationResult(
                method="isotonic", n=100, folds=5, calibrated=np.zeros(1),
                ece_out_of_fold=0.02, ece_in_fold=0.0, overfit_gap=0.20),
        }
        chosen, reason = calibration.select_calibrator(results)
        assert chosen == "identity"
        assert "rejected" in reason

    def test_selection_keeps_identity_when_the_gain_is_marginal(self):
        results = {
            "identity": calibration.CalibrationResult(
                method="identity", n=100, folds=5, calibrated=np.zeros(1), ece_out_of_fold=0.10),
            "platt": calibration.CalibrationResult(
                method="platt", n=100, folds=5, calibrated=np.zeros(1),
                ece_out_of_fold=0.09, overfit_gap=0.0),
        }
        chosen, _ = calibration.select_calibrator(results)
        assert chosen == "identity", "a 0.01 ECE gain must not buy a fitted component"

    def test_temperature_refuses_to_run_without_a_score_vector(self):
        # Refusing is the point: a temperature has nothing to act on when only
        # the top-1 scalar survived, and inventing one would produce a number
        # with no meaning attached.
        r = calibration.cross_fitted("temperature", [0.5, 0.9], [0, 1], vectors=None)
        assert not r.usable
        assert "vector" in r.note

    def test_calibrated_values_are_out_of_fold(self):
        rng = np.random.default_rng(3)
        n = 200
        conf = rng.uniform(0, 1, n)
        correct = (rng.uniform(size=n) < conf).astype(int)
        r = calibration.cross_fitted("platt", conf, correct, folds=4)
        assert len(r.calibrated) == n
        assert r.folds == 4


# --- Cascades ----------------------------------------------------------------

class TestCascade:
    def test_evidence_floor_matches_production_semantics(self):
        strong = pred("sales", 0.8, score=8)
        weak = pred("sales", 0.5, score=2)
        gate = heuristic_accepts(3.0)
        assert gate(strong, 0)
        assert not gate(weak, 0), "score 2 is below MIN_BUSINESS_EVIDENCE and must fall through"

    def test_gates_are_pure_and_reusable(self):
        # A gate that counted its own invocations would give different answers
        # on a second pass. The escalation-rate calculation and the cascade run
        # both call it, so this is a real failure mode, not a hypothetical.
        calibrated = [0.9, 0.1, 0.9]
        gate = confidence_accepts(0.5, calibrated)
        preds = [pred("sales"), pred("sales"), pred("sales")]
        first = [gate(p, i) for i, p in enumerate(preds)]
        second = [gate(p, i) for i, p in enumerate(preds)]
        assert first == second == [True, False, True]

    def test_fallback_only_runs_where_the_heuristic_declines(self):
        heur = [pred("sales", 0.8, score=8), pred("invoicing", 0.5, score=1)]
        fb = [pred("marketing", 0.9), pred("people", 0.7)]
        c = Cascade("t", [
            Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor"),
            Stage("tfidf", fb, always_accepts, "no_answer"),
        ])
        d = c.run(2)
        assert d[0].source == "heuristic" and d[0].department == "sales"
        assert d[1].source == "tfidf" and d[1].department == "people"
        assert d[1].escalation_reason == "below_floor"
        assert d[1].stages_used == ["heuristic", "tfidf"]

    def test_abstains_when_every_stage_declines(self):
        heur = [pred(None, 0.0)]
        fb = [pred(None, 0.0)]
        d = Cascade("t", [
            Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor"),
            Stage("tfidf", fb, always_accepts, "no_answer"),
        ]).run(1)[0]
        assert d.abstained and d.department is None
        assert d.source == "owner_clarification"

    def test_raw_score_is_not_overwritten_by_the_calibrated_value(self):
        heur = [pred("sales", 0.8, score=8)]
        d = Cascade("t", [
            Stage("heuristic", heur, always_accepts, "n/a", calibrated=[0.42]),
        ]).run(1)[0]
        assert d.raw_score == 8.0, "the source's own scale must survive"
        assert d.calibrated_confidence == 0.42
        assert d.raw_score != d.calibrated_confidence

    def test_latency_accumulates_only_over_stages_actually_consulted(self):
        heur = [pred("sales", 0.8, score=8, latency=0.1), pred("sales", 0.1, score=1, latency=0.1)]
        fb = [pred("sales", 0.9, latency=5.0), pred("sales", 0.9, latency=5.0)]
        d = Cascade("t", [
            Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor"),
            Stage("tfidf", fb, always_accepts, "no_answer"),
        ]).run(2)
        assert d[0].latency_ms == pytest.approx(0.1)
        assert d[1].latency_ms == pytest.approx(5.1)

    def test_utilisation_separates_coverage_from_accuracy(self):
        heur = [pred("sales", 0.8, score=8), pred(None, 0.0), pred("people", 0.9, score=9)]
        d = Cascade("t", [Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor")]).run(3)
        u = utilisation(d, ["sales", "marketing", "sales"])
        # `utilisation` rounds to 4dp for readability in the artifacts, so the
        # tolerance here matches that rather than float precision.
        assert u["coverage"] == pytest.approx(2 / 3, abs=1e-4)
        assert u["owner_clarification_rate"] == pytest.approx(1 / 3, abs=1e-4)
        assert u["accuracy_on_routed"] == pytest.approx(0.5, abs=1e-4)  # sales right, people wrong
        assert u["end_to_end_accuracy"] == pytest.approx(1 / 3, abs=1e-4)

    def test_abstention_is_scored_as_an_error_not_silently_dropped(self):
        from evaluate import score
        heur = [pred(None, 0.0)]
        d = Cascade("t", [Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor")]).run(1)
        m = score("t", "s", ["sales"], to_predictions(d))
        assert m.accuracy == 0.0
        assert m.no_evidence_rate == 1.0


# --- Leakage -----------------------------------------------------------------

class TestLeakage:
    def _split(self, name, asks, groups=None):
        return Split(name, f"{name}-v", asks, ["sales"] * len(asks),
                     ids=[f"{name}_{i}" for i in range(len(asks))], groups=groups)

    def test_detects_punctuation_and_case_only_differences(self):
        train = self._split("train", ["Email Sarah about the brake quote."], groups=["t1"])
        other = self._split("eval", ["email sarah about the brake quote"])
        detectors = {c.detector for c in leakage.find_collisions(train, other)}
        assert "EXACT" in detectors or "NORMALISED" in detectors

    def test_ngram_detector_catches_a_reworded_template(self):
        # Same sentence with one morphological change: high character-n-gram
        # overlap, and the kind of near-copy a bag-of-words test can miss.
        train = self._split("train", ["Invoicing Wallace for the fleet servicing work"], groups=["t1"])
        other = self._split("eval", ["Invoice Wallace for the fleet servicing work"])
        detectors = {c.detector for c in leakage.find_collisions(train, other)}
        assert "NGRAM" in detectors

    def test_unrelated_sentences_do_not_collide(self):
        train = self._split("train", ["Book Priya in for a coolant flush Thursday"], groups=["t1"])
        other = self._split("eval", ["What did we spend on parts in July?"])
        assert leakage.find_collisions(train, other) == []

    def test_template_family_widens_a_single_row_collision(self):
        train = self._split(
            "train",
            ["Email Sarah about the brake quote", "Email Dana about the brake quote",
             "Book a slot on Tuesday"],
            groups=["tpl_email", "tpl_email", "tpl_book"],
        )
        other = self._split("eval", ["email sarah about the brake quote"])
        cols = leakage.find_collisions(train, other)
        fam = leakage.template_families(cols, train)
        assert fam["available"]
        assert fam["templates_implicated"] == 1
        # The whole family is exposed, not just the row that tripped the detector.
        assert fam["rows_exposed"] == 2

    def test_normalise_is_idempotent(self):
        for s in ["Email  Sarah — about the “brake” quote.", "  MIXED case\tand\ttabs  "]:
            assert leakage.normalise(leakage.normalise(s)) == leakage.normalise(s)


# --- The safety boundary -----------------------------------------------------

class TestSafetyBoundary:
    def test_router_decision_carries_no_policy_fields(self):
        from decision import RouterDecision
        d = RouterDecision(department="sales", source="ml", raw_score=1.0,
                           calibrated_confidence=1.0).to_dict()
        for forbidden in ("approval", "requires_approval", "risk_level", "tool",
                          "tenant_id", "can_execute", "verified", "policy"):
            assert forbidden not in d, f"routing output must not expose {forbidden!r}"

    def test_none_is_not_a_routable_class(self):
        # The orchestrator decides out-of-scope, destructive and system-meta asks
        # deterministically. A model able to predict "none" would be a model with
        # an opinion about policy.
        import datasets as ds
        assert "none" not in ds.DEPARTMENTS

    def test_maximum_confidence_does_not_change_the_decision_shape(self):
        certain = Cascade("t", [Stage("ml", [pred("sales", 1.0, score=999)], always_accepts, "n/a")]).run(1)[0]
        unsure = Cascade("t", [Stage("ml", [pred("sales", 0.01, score=0.01)], always_accepts, "n/a")]).run(1)[0]
        assert certain.to_dict().keys() == unsure.to_dict().keys()
        assert certain.department == unsure.department == "sales"


class TestConfidenceScales:
    """
    Regression tests for the evidence-vs-confidence conflation.

    The heuristic's `raw_score` is unbounded evidence (2, 8, 17...) while every
    other number in the pipeline is a probability in [0, 1]. Letting the former
    stand in for the latter sorts every heuristic-decided case above every other
    case in a risk/coverage curve, which would quietly invent a selective-routing
    result out of a unit mismatch.
    """

    def test_source_confidence_stays_in_unit_range_for_the_heuristic(self):
        heur = [pred("sales", 0.8, score=8)]
        d = Cascade("t", [Stage("heuristic", heur, always_accepts, "n/a")]).run(1)[0]
        assert d.raw_score == 8.0
        assert d.source_confidence == 0.8
        assert 0.0 <= d.source_confidence <= 1.0

    def test_uncalibrated_stage_never_exports_an_evidence_score_as_confidence(self):
        heur = [pred("sales", 0.8, score=8)]
        d = Cascade("t", [Stage("heuristic", heur, always_accepts, "n/a")]).run(1)
        exported = to_predictions(d)[0]
        assert exported.confidence == 0.8, "must be the confidence, not the evidence score"
        assert exported.confidence <= 1.0

    def test_calibrated_value_wins_when_present(self):
        heur = [pred("sales", 0.8, score=8)]
        d = Cascade("t", [Stage("heuristic", heur, always_accepts, "n/a", calibrated=[0.31])]).run(1)
        assert to_predictions(d)[0].confidence == 0.31

    def test_risk_coverage_ranking_is_not_dominated_by_heuristic_evidence(self):
        # A heuristic case with high evidence but LOW confidence must not outrank
        # a fallback case with high confidence.
        import policy
        heur = [pred("sales", 0.30, score=8), pred(None, 0.0, score=0)]
        fb = [pred("sales", 0.30), pred("people", 0.99)]
        d = Cascade("t", [
            Stage("heuristic", heur, heuristic_accepts(3.0), "below_floor"),
            Stage("tfidf", fb, always_accepts, "no_answer"),
        ]).run(2)
        preds = to_predictions(d)
        rows = policy.risk_coverage_table(["marketing", "people"], preds, coverages=(0.5,))
        # At 50% coverage the single kept prediction should be the 0.99 one,
        # which is correct — so accuracy is 1.0. If the evidence score leaked
        # through as confidence, the 8.0 case would rank first and accuracy 0.0.
        assert rows[0]["accuracy"] == 1.0
