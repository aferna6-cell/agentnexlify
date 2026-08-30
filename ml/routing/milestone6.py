"""
Milestone 6 driver: calibration, cascades, risk/coverage, and one frozen run.

    python ml/routing/milestone6.py --split validation     # iterate here
    python ml/routing/milestone6.py --split test           # ONCE, at the end

What it does, in order:

  1. Score every required base router on the split (heuristic, TF-IDF, and
     Haiku where a credential exists).
  2. Cross-fit calibrators for the two statistical routers and choose the
     simplest one the data supports. Never on the frozen split — the chosen
     calibrators are loaded from the validation run when scoring test.
  3. Assemble architectures A-F and measure stage utilisation, coverage, owner
     clarification rate, cost and latency for each.
  4. Risk/coverage curves, the low-evidence region, the evidence-floor sweep,
     and accuracy by stress axis.
  5. Write a reproducibility manifest alongside the results.

Model D and every cascade containing it are measured only when
ANTHROPIC_API_KEY is set. Where it is not, this records the escalation RATE —
which is deterministic, comes from the preceding stages, and is the number that
drives the bill — and records the accuracy as unmeasured. It does not
substitute the heuristic's answers, and it does not present an estimate as a
measurement.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn

import calibration
import datasets
import heuristic as heuristic_router
import policy
from decision import (MIN_BUSINESS_EVIDENCE, Cascade, Stage, always_accepts,
                      confidence_accepts, heuristic_accepts, to_predictions,
                      utilisation)
from evaluate import Prediction, metrics_to_dict, score

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
REPO = Path(__file__).resolve().parents[2]
SEED = 20260829


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def tfidf_predictions(asks: list[str]) -> list[Prediction]:
    from train_tfidf import predictions_from
    return predictions_from(joblib.load(ARTIFACTS / "tfidf.joblib"), asks)


def llm_predictions(asks: list[str]) -> tuple[list[Prediction] | None, dict]:
    """Live Haiku predictions, or None plus the reason and the cost estimate."""
    payload = "\n".join(json.dumps({"ask": a}) for a in asks) + "\n"
    proc = subprocess.run(
        ["node", "--experimental-strip-types", "evals/export-llm-predictions.ts"],
        input=payload, capture_output=True, text=True, cwd=REPO / "agent-service", check=True,
    )
    if proc.stdout.lstrip()[:1] == "{":  # estimate object: no credential
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


# --- Calibration -------------------------------------------------------------

def calibrate_router(name: str, labels: list[str], preds: list[Prediction],
                     use_vectors: bool) -> dict:
    """
    Cross-fit every calibrator for one router and pick the simplest that holds.

    `use_vectors` says whether a per-class score vector exists. Where it does
    not, temperature scaling is reported as not applicable rather than
    approximated with the top-1 scalar — a scalar carries no distribution for a
    temperature to act on, and pretending otherwise would produce a number with
    no meaning.
    """
    conf = np.array([p.confidence for p in preds], dtype=float)
    correct = np.array([1 if p.predicted == y else 0 for y, p in zip(labels, preds)], dtype=int)
    vectors = None
    if use_vectors:
        vectors = [{k: v for k, v in p.proba.items() if not k.startswith("_")} for p in preds]
        if not any(vectors):
            vectors = None

    results = {m: calibration.cross_fitted(m, conf, correct, vectors)
               for m in ("identity", "platt", "isotonic", "temperature")}
    chosen, reason = calibration.select_calibrator(results)
    return {
        "router": name,
        "n": len(preds),
        "accuracy": round(float(correct.mean()), 4),
        "chosen_method": chosen,
        "selection_reason": reason,
        "selection_rule": {
            "min_ece_improvement": calibration.MIN_ECE_IMPROVEMENT,
            "max_overfit_gap": calibration.MAX_OVERFIT_GAP,
            "preference_order": ["identity", "platt", "temperature", "isotonic"],
        },
        "methods": {m: r.to_dict() for m, r in results.items()},
        "_calibrated_values": results[chosen].calibrated.tolist(),
        "_vectors_available": vectors is not None,
    }


# --- Architectures -----------------------------------------------------------

#: Confidence bar the TF-IDF stage must clear inside cascade F before it is
#: allowed to answer instead of escalating. Set at the base rate of a uniform
#: 8-way guess (1/8 = 0.125) rounded up to 0.4 — high enough to mean "the model
#: has a real opinion", low enough that it is not silently doing the abstention
#: work the cascade's own owner-clarification arm exists to do. It is swept in
#: the artifacts rather than asserted.
TFIDF_ESCALATION_CONFIDENCE = 0.40

#: Calibrated confidence below which architecture G stops routing and asks the
#: owner instead. Chosen from the validation risk/coverage curve rather than
#: picked in advance, and swept in the artifacts so the reader can see what a
#: different choice would have bought.
ABSTAIN_BELOW_CALIBRATED = 0.55


def _tfidf_gate(calibrated: list[float] | None):
    """Cascade F's middle gate, on the calibrated scale where one exists."""
    return confidence_accepts(TFIDF_ESCALATION_CONFIDENCE, calibrated)


def build_architectures(
    labels: list[str],
    heur: list[Prediction],
    tfidf: list[Prediction],
    llm: list[Prediction] | None,
    cal: dict[str, list[float] | None],
    usd_per_llm_call: float,
    floor: float = MIN_BUSINESS_EVIDENCE,
    abstain_below: float = ABSTAIN_BELOW_CALIBRATED,
) -> tuple[dict[str, dict], list[policy.CostProfile]]:
    """
    A-F from the brief. Each returns its utilisation report and cost profile.

    Cascades containing the LLM are still ASSEMBLED when no credential exists,
    because the escalation rate — the share of traffic that would reach the LLM
    — is fixed by the preceding deterministic stages and is therefore measurable
    without calling anything. That rate is the cost driver. What cannot be
    measured without a credential is what the LLM would then answer, and that is
    reported as unmeasured rather than filled in.
    """
    n = len(labels)
    reports: dict[str, dict] = {}
    profiles: list[policy.CostProfile] = []

    def record(key: str, title: str, cascade: Cascade, complete: bool = True, note: str = "") -> None:
        decisions = cascade.run(n)
        u = utilisation(decisions, labels)
        preds = to_predictions(decisions)
        m = score(title, "split", labels, preds)
        reports[key] = {
            "architecture": title,
            "measured": complete,
            "note": note,
            "utilisation": u,
            "metrics": metrics_to_dict(m),
            "risk_coverage": policy.risk_coverage_table(labels, preds),
            "_predictions": preds,
            "_decisions": decisions,
        }
        profiles.append(policy.cost_profile(title, decisions, labels,
                                            usd_per_llm_call=usd_per_llm_call,
                                            complete=complete, note=note))

    # A — heuristic only. The shipped offline baseline.
    record("A", "A: heuristic only",
           Cascade("A", [Stage("heuristic", heur, always_accepts, "n/a",
                               calibrated=cal.get("heuristic"))]))

    # B — TF-IDF only. Replaces the heuristic outright rather than backing it up.
    record("B", "B: TF-IDF only",
           Cascade("B", [Stage("tfidf", tfidf, always_accepts, "n/a",
                               calibrated=cal.get("tfidf"))]))

    # C — Milestone 5's recommendation: deterministic where evidence is strong,
    # statistical where it is not.
    record("C", "C: heuristic -> TF-IDF",
           Cascade("C", [
               Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor",
                     calibrated=cal.get("heuristic")),
               Stage("tfidf", tfidf, always_accepts, "tfidf_had_no_answer",
                     calibrated=cal.get("tfidf")),
           ]))

    # G — C with an abstention arm. A, B, C all answer whenever anything scores;
    # none of them can say "I do not know, ask the owner". That makes the
    # milestone's central question unanswerable from them, because three of its
    # four options are about WHEN to stop routing. G supplies the fourth option
    # so the trade between coverage and risk is a measurement rather than an
    # assumption.
    record("G", "G: heuristic -> TF-IDF -> ask owner",
           Cascade("G", [
               Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor",
                     calibrated=cal.get("heuristic")),
               Stage("tfidf", tfidf, confidence_accepts(abstain_below, cal.get("tfidf")),
                     "tfidf_below_abstention_threshold", calibrated=cal.get("tfidf")),
           ]))

    llm_note = ("no ANTHROPIC_API_KEY in this environment: the LLM stage was not called. "
                "Escalation rate and cost are measured (they follow from the deterministic "
                "stages ahead of it); routing accuracy through the LLM is NOT.")

    if llm is not None:
        record("D", "D: LLM only",
               Cascade("D", [Stage("llm", llm, always_accepts, "n/a", cost_per_call_usd=usd_per_llm_call)]))
        record("E", "E: heuristic -> LLM",
               Cascade("E", [
                   Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor",
                         calibrated=cal.get("heuristic")),
                   Stage("llm", llm, always_accepts, "llm_had_no_answer",
                         cost_per_call_usd=usd_per_llm_call),
               ]))
        record("F", "F: heuristic -> TF-IDF -> LLM",
               Cascade("F", [
                   Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor",
                         calibrated=cal.get("heuristic")),
                   Stage("tfidf", tfidf, _tfidf_gate(cal.get("tfidf")), "tfidf_below_confidence",
                         calibrated=cal.get("tfidf")),
                   Stage("llm", llm, always_accepts, "llm_had_no_answer",
                         cost_per_call_usd=usd_per_llm_call),
               ]))
    else:
        for key, title, prefix in (
            ("D", "D: LLM only", []),
            ("E", "E: heuristic -> LLM",
             [Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor")]),
            ("F", "F: heuristic -> TF-IDF -> LLM",
             [Stage("heuristic", heur, heuristic_accepts(floor), "heuristic_below_floor"),
              Stage("tfidf", tfidf, _tfidf_gate(cal.get("tfidf")), "tfidf_below_confidence")]),
        ):
            esc = _escalation_rate(prefix, n)
            reports[key] = {
                "architecture": title,
                "measured": False,
                "note": llm_note,
                "escalation_to_llm_rate": round(esc, 4),
                "llm_calls_per_1k": round(1000 * esc, 1),
                "usd_per_1k": round(1000 * esc * usd_per_llm_call, 4),
                "utilisation": None,
                "metrics": None,
                "risk_coverage": None,
            }
            profiles.append(policy.CostProfile(
                name=title, llm_calls_per_1k=1000 * esc, usd_per_1k=1000 * esc * usd_per_llm_call,
                clarifications_per_1k=float("nan"), routing_error_per_1k=float("nan"),
                latency_p50_ms=float("nan"), latency_p95_ms=float("nan"),
                complete=False, note=llm_note,
            ))
    return reports, profiles


def _escalation_rate(prefix: list[Stage], n: int) -> float:
    """Share of traffic that no stage in `prefix` accepts, i.e. reaches the LLM."""
    if not prefix:
        return 1.0
    reached = 0
    for i in range(n):
        if not any(s.accepts(s.predictions[i], i) for s in prefix):
            reached += 1
    return reached / n


# --- Driver ------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test"], default="validation")
    ap.add_argument("--validation-version", default="v3", choices=["v3"])
    ap.add_argument("--calibrators-from", default=None,
                    help="validation artifact to take fitted calibrator choices from (required for --split test)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.split == "test":
        print("!! FROZEN TEST SPLIT — this is the final measurement, not an iteration step.\n")
        split = datasets.load_test()
    else:
        split = datasets.load_validation(args.validation_version)
    labels = split.labels
    print(f"split: {split.name} ({split.version}), {len(split)} cases with a department label\n")

    t0 = time.perf_counter(); heur = heuristic_router.predict(split.asks)
    print(f"heuristic   {time.perf_counter() - t0:5.1f}s")
    t0 = time.perf_counter(); tfidf = tfidf_predictions(split.asks)
    print(f"tfidf       {time.perf_counter() - t0:5.1f}s")
    llm, llm_info = llm_predictions(split.asks)
    usd_per_call = float(llm_info.get("approx_cost_usd_per_call", 0.0))
    if llm is None:
        print(f"llm         NOT MEASURED (no credential); est ${llm_info['approx_cost_usd_per_1k_calls']}/1k calls")
    else:
        print(f"llm         measured, malformed/unmapped {llm_info.get('malformed_or_unmapped')}")

    base = {"heuristic": heur, "tfidf": tfidf}
    if llm is not None:
        base["llm"] = llm

    # --- Calibration -------------------------------------------------------
    print("\nCalibration (cross-fitted, 5-fold, out-of-fold reported):")
    calib: dict[str, dict] = {}
    chosen_values: dict[str, list[float] | None] = {}
    if args.split == "validation":
        for name, use_vec in (("heuristic", True), ("tfidf", True)):
            calib[name] = calibrate_router(name, labels, base[name], use_vec)
            chosen_values[name] = calib[name]["_calibrated_values"]
            r = calib[name]
            print(f"  {name:<10} chosen={r['chosen_method']:<12} "
                  f"ECE raw {r['methods']['identity']['ece_raw']:.3f} -> "
                  f"{r['methods'][r['chosen_method']]['ece_out_of_fold']:.3f}")
        if llm is not None:
            calib["llm"] = calibrate_router("llm", labels, llm, use_vec=False)
            chosen_values["llm"] = calib["llm"]["_calibrated_values"]
            print(f"  {'llm':<10} chosen={calib['llm']['chosen_method']}")
    else:
        # The frozen run must not fit anything. Load the methods chosen on
        # validation, refit them on validation, and APPLY them here.
        src = Path(args.calibrators_from or (ARTIFACTS / f"milestone6-validation-{args.validation_version}.json"))
        prior = json.loads(src.read_text())
        vsplit = datasets.load_validation(args.validation_version)
        vheur = heuristic_router.predict(vsplit.asks)
        vtfidf = tfidf_predictions(vsplit.asks)
        for name, vpreds, tpreds in (("heuristic", vheur, heur), ("tfidf", vtfidf, tfidf)):
            method = prior["calibration"][name]["chosen_method"]
            vconf = np.array([p.confidence for p in vpreds])
            vcorrect = np.array([1 if p.predicted == y else 0 for y, p in zip(vsplit.labels, vpreds)])
            vvec = [{k: v for k, v in p.proba.items() if not k.startswith("_")} for p in vpreds]
            cal_obj = calibration.fit_final(method, vconf, vcorrect, vvec)
            tvec = [{k: v for k, v in p.proba.items() if not k.startswith("_")} for p in tpreds]
            tconf = np.array([p.confidence for p in tpreds])
            chosen_values[name] = np.clip(cal_obj.transform(tconf, tvec), 0, 1).tolist()
            calib[name] = {"router": name, "chosen_method": method,
                           "fitted_on": f"validation {vsplit.version} (n={len(vsplit)})",
                           "applied_to": split.version,
                           "params": cal_obj.params(),
                           "note": "method selected on validation; refitted on all of validation; applied once here"}
            print(f"  {name:<10} applied {method} fitted on validation")

    # --- Base router metrics ----------------------------------------------
    print(f"\n{'router':<14} {'acc':>7}  {'macroF1':>8}  {'top2':>7}  {'p50ms':>8}  {'p95ms':>8}")
    base_metrics = {}
    for name, preds in base.items():
        m = score(name, split.name, labels, preds)
        base_metrics[name] = metrics_to_dict(m)
        print(f"{name:<14} {m.accuracy*100:6.1f}%  {m.macro_f1:8.4f}  {m.top2_accuracy*100:6.1f}%  "
              f"{m.latency_p50_ms:8.2f}  {m.latency_p95_ms:8.2f}")

    # --- Architectures ------------------------------------------------------
    reports, profiles = build_architectures(labels, heur, tfidf, llm, chosen_values, usd_per_call)
    print(f"\n{'architecture':<30} {'acc':>7}  {'cov':>7}  {'clarify':>8}  {'llm/1k':>7}  {'p95ms':>8}")
    for key in sorted(reports):
        r = reports[key]
        if not r["measured"]:
            print(f"{r['architecture']:<30} {'—':>7}  {'—':>7}  {'—':>8}  "
                  f"{r['llm_calls_per_1k']:7.0f}  {'—':>8}   (LLM unmeasured)")
            continue
        u = r["utilisation"]
        print(f"{r['architecture']:<30} {u['end_to_end_accuracy']*100:6.1f}%  "
              f"{u['coverage']*100:6.1f}%  {u['owner_clarification_rate']*100:7.1f}%  "
              f"{0:7.0f}  {u['latency_p95_ms']:8.3f}")

    # --- Analyses -----------------------------------------------------------
    low_ev = policy.low_evidence_report(labels, base, heur, MIN_BUSINESS_EVIDENCE)
    sweep = policy.evidence_floor_sweep(labels, heur, tfidf)
    front = policy.pareto_front(profiles)
    abstention_sweep = policy.abstention_sweep(
        labels, heur, tfidf, chosen_values.get("tfidf"), MIN_BUSINESS_EVIDENCE)
    stress = ({name: policy.stress_breakdown(labels, preds, split.stress)
               for name, preds in base.items()} if split.stress else None)

    print(f"\nLow-evidence region: {low_ev['n_low_evidence']}/{low_ev['n_total']} cases "
          f"({low_ev['share_low_evidence']*100:.1f}%), of which "
          f"{low_ev['n_no_candidate_at_all']} had no candidate at all")
    for name, m in low_ev["models"].items():
        print(f"  {name:<14} acc {m['accuracy']*100:5.1f}%   macroF1 {m['macro_f1']:.3f}")

    payload = {
        "milestone": 6,
        "split": split.name,
        "split_version": split.version,
        "cases": len(split),
        "git_sha": git_sha(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reproducibility": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "seed": SEED,
            "train_version": datasets.TRAIN_VERSION,
            "validation_version": datasets.VALIDATION_VERSIONS[args.validation_version],
            "test_version": datasets.TEST_VERSION,
            "min_business_evidence": MIN_BUSINESS_EVIDENCE,
            "tfidf_escalation_confidence": TFIDF_ESCALATION_CONFIDENCE,
            "abstain_below_calibrated": ABSTAIN_BELOW_CALIBRATED,
            "calibration_folds": 5,
            "llm_model": llm_info.get("model"),
            "platform": platform.platform(),
        },
        "llm": ({"measured": True, **llm_info} if llm is not None
                else {"measured": False,
                      "reason": "no ANTHROPIC_API_KEY in this environment",
                      **llm_info}),
        "base_routers": base_metrics,
        "calibration": calib,
        "architectures": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                          for k, v in reports.items()},
        "pareto": front,
        "low_evidence": low_ev,
        "evidence_floor_sweep": sweep,
        "abstention_threshold_sweep": abstention_sweep,
        "stress_breakdown": stress,
        "per_case": [
            {"id": (split.ids[i] if split.ids else None), "ask": split.asks[i],
             "expected": labels[i],
             "stress": (split.stress[i] if split.stress else None),
             **{name: {"predicted": p[i].predicted, "confidence": round(p[i].confidence, 4)}
                for name, p in base.items()},
             **{f"arch_{k}": (reports[k]["_decisions"][i].to_dict() if reports[k]["measured"] else None)
                for k in sorted(reports)}}
            for i in range(len(split))
        ],
    }
    out = Path(args.out) if args.out else ARTIFACTS / f"milestone6-{split.name}.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"\nwritten -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
