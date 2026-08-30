"""
Export a Milestone-6 cascade's decisions for end-to-end replay in the harness.

`ml/routing/export.py` exports a single MODEL's predictions. A cascade is not a
model: it is a decision procedure whose output includes an abstention, and an
abstention has no representation in a table of `{ask: [candidates]}`. This file
handles that difference rather than flattening it away.

Three cases, three encodings:

  routed by the heuristic   OMITTED from the table. `useRouterPredictions`
      returns null for an unlisted ask, and `classify()` then falls through to
      the shipped router — which, for these asks, is the heuristic that already
      chose them. Emitting a rescaled copy of the heuristic's own scores would
      change the orchestrator's ambiguity behaviour (`isAmbiguous` reads raw
      evidence) while claiming to change nothing.

  routed by a fallback      one candidate at the chosen department, with the
      cascade's calibrated confidence and a score above MIN_BUSINESS_EVIDENCE
      so the orchestrator routes on it.

  abstained                 TWO candidates at equal score. `isAmbiguous`
      compares `second.score / top.score >= RESOLUTION_RATIO`; at a ratio of
      exactly 1.0 the orchestrator returns `needs_clarification`, which is the
      production path for "ask the owner". This is a deliberate encoding of an
      abstention into the orchestrator's existing vocabulary, NOT a change to
      the orchestrator: nothing in the engine was modified to accept it.

The scale choice is the same one `export.py` documents and is worth repeating,
because it is the weakest link in the whole replay: a probability of 0.4 and a
keyword score of 4 are not the same kind of number, and mapping one onto the
other is a modelling decision made here, in the open, rather than a fact.

    python ml/routing/export_cascade.py --arch C2 --split test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

import datasets
import heuristic as heuristic_router
from decision import (MIN_BUSINESS_EVIDENCE, Cascade, Stage, always_accepts,
                      confidence_accepts, heuristic_accepts)
from evaluate import Prediction

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
REPO = Path(__file__).resolve().parents[2]

#: Heuristic evidence in this corpus runs roughly 2-20. A fallback's probability
#: is mapped onto that range so the orchestrator's ambiguity margin behaves
#: comparably for both. Same constant, and same caveat, as `export.py`.
SCORE_SCALE = 12.0
#: Score written for both halves of an abstention pair. Any value clearing
#: MIN_BUSINESS_EVIDENCE works; the ratio between the two is what matters.
ABSTAIN_SCORE = 6.0


def _tfidf(asks: list[str]) -> list[Prediction]:
    from train_tfidf import predictions_from
    return predictions_from(joblib.load(ARTIFACTS / "tfidf.joblib"), asks)


def _embedding(asks: list[str]) -> list[Prediction]:
    from train_embeddings import _encoder, predictions_from
    return predictions_from(joblib.load(ARTIFACTS / "embedding_lr.joblib"), _encoder(), asks)


def build(arch: str, asks: list[str], abstain_below: float) -> tuple[Cascade, list[Prediction]]:
    heur = heuristic_router.predict(asks)
    if arch == "C":
        fb = _tfidf(asks)
        return Cascade("C", [
            Stage("heuristic", heur, heuristic_accepts(MIN_BUSINESS_EVIDENCE), "heuristic_below_floor"),
            Stage("tfidf", fb, always_accepts, "tfidf_had_no_answer"),
        ]), heur
    if arch == "C2":
        fb = _embedding(asks)
        return Cascade("C2", [
            Stage("heuristic", heur, heuristic_accepts(MIN_BUSINESS_EVIDENCE), "heuristic_below_floor"),
            Stage("embedding", fb, always_accepts, "embedding_had_no_answer"),
        ]), heur
    if arch == "G":
        fb = _tfidf(asks)
        return Cascade("G", [
            Stage("heuristic", heur, heuristic_accepts(MIN_BUSINESS_EVIDENCE), "heuristic_below_floor"),
            Stage("tfidf", fb, confidence_accepts(abstain_below), "tfidf_below_abstention_threshold"),
        ]), heur
    raise ValueError(f"unknown architecture {arch!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", choices=["C", "C2", "G"], required=True)
    ap.add_argument("--split", choices=["validation", "test"], default="test")
    ap.add_argument("--validation-version", default=datasets.DEFAULT_VALIDATION, choices=["v1", "v2"])
    ap.add_argument("--abstain-below", type=float, default=0.55)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = (datasets.VALIDATION_PATHS[args.validation_version] if args.split == "validation"
            else datasets.TEST_PATH)
    # Every case in the file, including the `none`-labelled ones the classifier
    # is not scored on: an ask missing from the table silently reverts to the
    # shipped router mid-run, which would make the replay a blend.
    asks = [c["ask"] for c in json.loads(path.read_text())["cases"]]

    cascade, heur = build(args.arch, asks, args.abstain_below)
    decisions = cascade.run(len(asks))

    table: dict[str, list[dict]] = {}
    kept, filled, abstained = 0, 0, 0
    for ask, d in zip(asks, decisions):
        if d.source == "heuristic":
            kept += 1
            continue
        if d.abstained:
            abstained += 1
            pair = (d.alternates + ["operations", "sales"])[:2]
            table[ask] = [
                {"agentId": pair[0], "confidence": 0.5, "score": ABSTAIN_SCORE},
                {"agentId": pair[1], "confidence": 0.5, "score": ABSTAIN_SCORE},
            ]
            continue
        filled += 1
        conf = d.calibrated_confidence if d.calibrated_confidence is not None else (d.raw_score or 0.0)
        cands = [{"agentId": d.department, "confidence": round(float(conf), 4),
                  "score": round(float(conf) * SCORE_SCALE, 4)}]
        for alt in d.alternates[:2]:
            cands.append({"agentId": alt, "confidence": 0.0, "score": 0.0})
        table[ask] = cands

    out = Path(args.out) if args.out else ARTIFACTS / f"router-m6-{args.arch}-{args.split}.json"
    out.write_text(json.dumps(table, indent=2) + "\n")
    print(f"{args.arch} on {args.split}: {len(asks)} asks")
    print(f"  {kept} left to the shipped heuristic (identical behaviour, deliberately not rewritten)")
    print(f"  {filled} filled by the fallback")
    print(f"  {abstained} encoded as an owner clarification (tied pair -> isAmbiguous)")
    print(f"written -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
