"""
Confidence calibration for the routing experiment.

Milestone 5 measured calibration and deliberately did not fix it. This module is
the fix, and it exists because of one specific hazard the brief names:

    Heuristic confidence  =  score / (score + 2)
    TF-IDF confidence     =  a logistic-regression class probability
    LLM confidence        =  a number the model wrote about itself

These live on three different scales and mean three different things. A cascade
rule of the form `if tfidf_conf > heuristic_conf: use tfidf` is therefore not a
comparison — it is a coincidence of arithmetic. Calibration is what makes the
comparison legitimate: after it, every source's number answers the same
question, *"what fraction of predictions I make at this confidence are right?"*,
and only then can two of them be put on the same axis.

Three calibrators, in increasing order of how much they can overfit:

  IdentityCalibrator   the null hypothesis. Always fitted and always reported,
                       because "the raw number was already fine" has to be a
                       possible outcome or the comparison is rigged.
  PlattCalibrator      one-dimensional logistic regression on the raw
                       confidence. Two parameters. Monotone, so it cannot
                       change the RANKING of predictions — which means it
                       cannot change a risk-coverage curve, only the threshold
                       that indexes it.
  IsotonicCalibrator   non-parametric monotone fit. Strictly more expressive
                       and, on 184 validation points, the one most likely to
                       memorise its own fold.
  TemperatureCalibrator  a single scalar dividing a score/logit VECTOR before
                       the softmax. Only defined where a full per-class vector
                       exists, which is why it is offered for TF-IDF and for
                       the heuristic's raw evidence scores and refused
                       elsewhere rather than faked.

Cross-fitting is not optional here. A calibrator scored on the points it was
fitted on reports the calibration of its own training set, which is always
excellent and never transfers. `cross_fitted` fits on K-1 folds and predicts the
held-out one, so every calibrated confidence in the output was produced by a
model that had not seen that case. The gap between in-fold and out-of-fold ECE
is then a direct measurement of overfitting, and `select_calibrator` refuses a
method whose gap is large — a rule that can actually reject isotonic, and on a
split this size usually should.

Nothing in this module may see the frozen test split. It takes a validation
split and returns fitted objects; `milestone6.py` owns the single application of
those objects to the test set at the end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

SEED = 20260829
EPS = 1e-12


# --- Metrics -----------------------------------------------------------------

def brier(conf: np.ndarray, correct: np.ndarray) -> float:
    """Mean squared error of the confidence treated as P(correct)."""
    return float(np.mean((conf - correct) ** 2))


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    """
    Equal-width-bin ECE: the average gap between stated confidence and observed
    accuracy, weighted by how much traffic sits in each bin.
    """
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf >= lo) & (conf < hi if hi < 1.0 else conf <= 1.0)
        n = int(mask.sum())
        if n == 0:
            continue
        total += (n / len(conf)) * abs(float(correct[mask].mean()) - float(conf[mask].mean()))
    return float(total)


def maximum_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    """The worst single bin. ECE can look fine while one bin is badly wrong."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    worst = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf >= lo) & (conf < hi if hi < 1.0 else conf <= 1.0)
        if not mask.any():
            continue
        worst = max(worst, abs(float(correct[mask].mean()) - float(conf[mask].mean())))
    return float(worst)


def reliability_curve(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> list[dict]:
    """The reliability diagram as data: one row per bin, ready to plot or table."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf >= lo) & (conf < hi if hi < 1.0 else conf <= 1.0)
        n = int(mask.sum())
        rows.append({
            "bin": [round(float(lo), 2), round(float(hi), 2)],
            "count": n,
            "mean_confidence": (round(float(conf[mask].mean()), 4) if n else None),
            "accuracy": (round(float(correct[mask].mean()), 4) if n else None),
            "gap": (round(float(correct[mask].mean() - conf[mask].mean()), 4) if n else None),
        })
    return rows


# --- Calibrators -------------------------------------------------------------

class Calibrator:
    """A monotone map from a raw confidence to a probability of being correct."""

    name = "base"
    #: True when the calibrator consumes a full per-class vector rather than a
    #: scalar. Only temperature scaling does, and only where a vector exists.
    needs_vector = False

    def fit(self, conf: np.ndarray, correct: np.ndarray, vectors: list[dict] | None = None) -> "Calibrator":
        raise NotImplementedError

    def transform(self, conf: np.ndarray, vectors: list[dict] | None = None) -> np.ndarray:
        raise NotImplementedError

    def params(self) -> dict:
        return {}


class IdentityCalibrator(Calibrator):
    """No calibration. The null hypothesis every other method has to beat."""

    name = "identity"

    def fit(self, conf, correct, vectors=None):
        return self

    def transform(self, conf, vectors=None):
        return np.asarray(conf, dtype=float)


class PlattCalibrator(Calibrator):
    """
    Logistic regression of correctness on the raw confidence (Platt scaling).

    Two parameters, monotone in the input. It reshapes the confidence axis
    without reordering anything on it, which is exactly the property wanted from
    a calibrator: it changes what a number MEANS, never which prediction the
    router prefers.
    """

    name = "platt"

    def __init__(self) -> None:
        self._lr: LogisticRegression | None = None
        self._constant: float | None = None

    def fit(self, conf, correct, vectors=None):
        conf = np.asarray(conf, dtype=float).reshape(-1, 1)
        correct = np.asarray(correct, dtype=int)
        if len(np.unique(correct)) < 2:
            # A fold where everything was right (or everything wrong) carries no
            # gradient. Fall back to the base rate rather than fitting noise.
            self._constant = float(np.clip(correct.mean(), EPS, 1 - EPS))
            return self
        self._lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
        self._lr.fit(conf, correct)
        return self

    def transform(self, conf, vectors=None):
        conf = np.asarray(conf, dtype=float).reshape(-1, 1)
        if self._lr is None:
            return np.full(len(conf), self._constant if self._constant is not None else 0.5)
        return self._lr.predict_proba(conf)[:, 1]

    def params(self) -> dict:
        if self._lr is None:
            return {"degenerate_fold_constant": self._constant}
        return {"coef": float(self._lr.coef_[0][0]), "intercept": float(self._lr.intercept_[0])}


class IsotonicCalibrator(Calibrator):
    """
    Non-parametric monotone regression.

    More expressive than Platt and correspondingly easier to overfit: with 184
    points spread over a handful of distinct heuristic confidences it can fit
    the fold almost exactly. That is why every number this module reports is
    out-of-fold, and why `select_calibrator` compares the in-fold and
    out-of-fold gap before preferring it.
    """

    name = "isotonic"

    def __init__(self) -> None:
        self._iso: IsotonicRegression | None = None
        self._constant: float | None = None

    def fit(self, conf, correct, vectors=None):
        conf = np.asarray(conf, dtype=float)
        correct = np.asarray(correct, dtype=float)
        if len(np.unique(correct)) < 2 or len(np.unique(conf)) < 2:
            self._constant = float(np.clip(correct.mean(), EPS, 1 - EPS))
            return self
        self._iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self._iso.fit(conf, correct)
        return self

    def transform(self, conf, vectors=None):
        conf = np.asarray(conf, dtype=float)
        if self._iso is None:
            return np.full(len(conf), self._constant if self._constant is not None else 0.5)
        return np.asarray(self._iso.predict(conf), dtype=float)

    def params(self) -> dict:
        if self._iso is None:
            return {"degenerate_fold_constant": self._constant}
        return {"knots": int(len(self._iso.X_thresholds_))}


class TemperatureCalibrator(Calibrator):
    """
    One scalar T dividing a score vector before the softmax.

    Mathematically appropriate only where a per-class score or logit VECTOR
    exists: temperature acts on the whole distribution, sharpening or flattening
    it, and there is nothing for it to act on if all that survived is the
    top-1 scalar. TF-IDF supplies class log-probabilities; the heuristic
    supplies raw evidence scores per candidate, which are not logits but are a
    genuine per-class score vector, so a softmax over them is a defensible —
    and clearly labelled — construction rather than a borrowed one.

    T is fitted by minimising negative log-likelihood of the top-1 being correct
    over a coarse-then-fine grid. A grid rather than a gradient step because the
    objective is one-dimensional and smooth, and a grid cannot silently fail to
    converge.
    """

    name = "temperature"
    needs_vector = True

    def __init__(self) -> None:
        self.T: float = 1.0

    @staticmethod
    def _top1(vectors: list[dict], T: float) -> np.ndarray:
        out = np.empty(len(vectors), dtype=float)
        for i, vec in enumerate(vectors):
            v = np.array(list(vec.values()), dtype=float)
            if v.size == 0:
                out[i] = 0.0
                continue
            z = v / max(T, 1e-6)
            z -= z.max()
            p = np.exp(z)
            out[i] = float((p / p.sum()).max())
        return out

    def fit(self, conf, correct, vectors=None):
        if not vectors:
            raise ValueError("temperature scaling needs a per-class score vector")
        correct = np.asarray(correct, dtype=float)
        best, best_nll = 1.0, np.inf
        grid = np.concatenate([np.arange(0.05, 2.0, 0.05), np.arange(2.0, 20.1, 0.25)])
        for T in grid:
            p = np.clip(self._top1(vectors, float(T)), EPS, 1 - EPS)
            nll = float(-np.mean(correct * np.log(p) + (1 - correct) * np.log(1 - p)))
            if nll < best_nll:
                best, best_nll = float(T), nll
        self.T = best
        return self

    def transform(self, conf, vectors=None):
        if not vectors:
            raise ValueError("temperature scaling needs a per-class score vector")
        return self._top1(vectors, self.T)

    def params(self) -> dict:
        return {"temperature": round(self.T, 4)}


CALIBRATORS: dict[str, type[Calibrator]] = {
    "identity": IdentityCalibrator,
    "platt": PlattCalibrator,
    "isotonic": IsotonicCalibrator,
    "temperature": TemperatureCalibrator,
}


# --- Cross-fitting -----------------------------------------------------------

@dataclass
class CalibrationResult:
    method: str
    n: int
    folds: int
    #: Out-of-fold calibrated confidences, aligned with the input order. Every
    #: value here was produced by a calibrator that had not seen its own case.
    calibrated: np.ndarray = field(repr=False)
    ece_raw: float = 0.0
    ece_out_of_fold: float = 0.0
    ece_in_fold: float = 0.0
    mce_out_of_fold: float = 0.0
    brier_raw: float = 0.0
    brier_out_of_fold: float = 0.0
    reliability_raw: list[dict] = field(default_factory=list)
    reliability_calibrated: list[dict] = field(default_factory=list)
    fold_params: list[dict] = field(default_factory=list)
    #: in-fold minus out-of-fold ECE. Large and positive means the calibrator
    #: fitted its own fold and did not transfer.
    overfit_gap: float = 0.0
    usable: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method, "n": self.n, "folds": self.folds,
            "ece_raw": round(self.ece_raw, 4),
            "ece_out_of_fold": round(self.ece_out_of_fold, 4),
            "ece_in_fold": round(self.ece_in_fold, 4),
            "overfit_gap": round(self.overfit_gap, 4),
            "mce_out_of_fold": round(self.mce_out_of_fold, 4),
            "brier_raw": round(self.brier_raw, 4),
            "brier_out_of_fold": round(self.brier_out_of_fold, 4),
            "reliability_raw": self.reliability_raw,
            "reliability_calibrated": self.reliability_calibrated,
            "fold_params": self.fold_params,
            "usable": self.usable,
            "note": self.note,
        }


def cross_fitted(
    method: str,
    conf: Sequence[float],
    correct: Sequence[int],
    vectors: list[dict] | None = None,
    folds: int = 5,
    bins: int = 10,
) -> CalibrationResult:
    """
    Fit and evaluate one calibrator without letting it score its own fit.

    Returns out-of-fold calibrated confidences plus both the out-of-fold and
    in-fold ECE. Reporting both is the point: a method that looks superb
    in-fold and mediocre out-of-fold has told you it memorised, and that is a
    result, not a failure of the experiment.
    """
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=int)
    n = len(conf)
    cls = CALIBRATORS[method]

    if cls.needs_vector and not vectors:
        return CalibrationResult(
            method=method, n=n, folds=0, calibrated=conf.copy(),
            ece_raw=expected_calibration_error(conf, correct, bins),
            usable=False,
            note="no per-class score vector available for this router; temperature scaling is undefined here and was not faked",
        )

    if len(np.unique(correct)) < 2:
        return CalibrationResult(
            method=method, n=n, folds=0, calibrated=conf.copy(),
            ece_raw=expected_calibration_error(conf, correct, bins),
            usable=False, note="all predictions share one outcome; nothing to calibrate against",
        )

    k = min(folds, int(min(np.bincount(correct))))
    if k < 2:
        return CalibrationResult(
            method=method, n=n, folds=0, calibrated=conf.copy(),
            ece_raw=expected_calibration_error(conf, correct, bins),
            usable=False, note="minority outcome too small to stratify into folds",
        )

    out = np.empty(n, dtype=float)
    in_fold_conf: list[np.ndarray] = []
    in_fold_correct: list[np.ndarray] = []
    fold_params: list[dict] = []

    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEED)
    for train_idx, test_idx in skf.split(conf.reshape(-1, 1), correct):
        cal = cls()
        tr_vec = [vectors[i] for i in train_idx] if vectors else None
        te_vec = [vectors[i] for i in test_idx] if vectors else None
        cal.fit(conf[train_idx], correct[train_idx], tr_vec)
        out[test_idx] = np.clip(cal.transform(conf[test_idx], te_vec), 0.0, 1.0)
        in_fold_conf.append(np.clip(cal.transform(conf[train_idx], tr_vec), 0.0, 1.0))
        in_fold_correct.append(correct[train_idx])
        fold_params.append(cal.params())

    ece_in = float(np.mean([
        expected_calibration_error(c, y, bins) for c, y in zip(in_fold_conf, in_fold_correct)
    ]))
    ece_out = expected_calibration_error(out, correct, bins)

    return CalibrationResult(
        method=method, n=n, folds=k, calibrated=out,
        ece_raw=expected_calibration_error(conf, correct, bins),
        ece_out_of_fold=ece_out,
        ece_in_fold=ece_in,
        mce_out_of_fold=maximum_calibration_error(out, correct, bins),
        brier_raw=brier(conf, correct),
        brier_out_of_fold=brier(out, correct),
        reliability_raw=reliability_curve(conf, correct, bins),
        reliability_calibrated=reliability_curve(out, correct, bins),
        fold_params=fold_params,
        overfit_gap=ece_out - ece_in,
    )


#: How much better than the raw number a calibrator must be before it is worth
#: the extra machinery. Below this the honest answer is "the raw confidence was
#: already about right", and adding a fitted component buys complexity and a
#: dependency on 184 hand-written sentences for nothing.
MIN_ECE_IMPROVEMENT = 0.02
#: How much worse a calibrator may be out-of-fold than in-fold before it is
#: treated as having memorised its fit rather than learned the mapping.
MAX_OVERFIT_GAP = 0.05


def select_calibrator(results: dict[str, CalibrationResult]) -> tuple[str, str]:
    """
    Pick the simplest method the data actually supports.

    Order of preference is identity, then platt, then temperature, then
    isotonic — least expressive first. A method is only preferred over the
    incumbent when it improves out-of-fold ECE by more than MIN_ECE_IMPROVEMENT
    *and* does not show an overfit gap beyond MAX_OVERFIT_GAP. So a more
    powerful calibrator has to earn its place twice: once on accuracy of
    meaning, once on transfer.

    Returns (method, reason).
    """
    order = ["identity", "platt", "temperature", "isotonic"]
    usable = {m: r for m, r in results.items() if r.usable}
    if "identity" not in usable:
        return "identity", "no calibrator was usable on this split; raw confidence retained"

    best = "identity"
    best_ece = usable["identity"].ece_out_of_fold
    reasons: list[str] = []
    for m in order[1:]:
        r = usable.get(m)
        if r is None:
            continue
        if r.overfit_gap > MAX_OVERFIT_GAP:
            reasons.append(f"{m} rejected: out-of-fold ECE exceeds in-fold by {r.overfit_gap:.3f} (>{MAX_OVERFIT_GAP})")
            continue
        if best_ece - r.ece_out_of_fold > MIN_ECE_IMPROVEMENT:
            reasons.append(f"{m} improves ECE {best_ece:.3f} -> {r.ece_out_of_fold:.3f}")
            best, best_ece = m, r.ece_out_of_fold
        else:
            reasons.append(f"{m} kept out: ECE {r.ece_out_of_fold:.3f} vs incumbent {best_ece:.3f}, "
                           f"under the {MIN_ECE_IMPROVEMENT} improvement bar")
    return best, "; ".join(reasons) if reasons else "identity was not beaten"


def fit_final(method: str, conf: Sequence[float], correct: Sequence[int],
              vectors: list[dict] | None = None) -> Calibrator:
    """
    Fit the chosen calibrator on ALL of validation, for application to the test
    split. Cross-fitting established that the method transfers; this produces
    the single object that gets used once, at the end.
    """
    return CALIBRATORS[method]().fit(np.asarray(conf, dtype=float),
                                     np.asarray(correct, dtype=int), vectors)
