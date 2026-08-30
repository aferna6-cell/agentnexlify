"""
Export a candidate router's predictions in the shape the TypeScript harness
consumes, so the action benchmark can be replayed end to end behind it.

    { "<ask>": [ {"agentId": "sales", "confidence": 0.91, "score": 9.1}, ... ] }

`score` is carried because the orchestrator's ambiguity test prefers raw
evidence over saturated confidence (see `isAmbiguous`). For a probabilistic
model there is no natural "evidence" scale, so probability is scaled to the
range the heuristic produces. That is a modelling choice with a consequence —
a probability of 0.4 and a keyword score of 4 are not the same kind of number —
and it is written down here rather than buried.

This is deployment Option C from the milestone (precomputed classifier output
consumed by JS). It is used for the EXPERIMENT only. Nothing here is wired into
production routing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

import datasets
import heuristic
from evaluate import Prediction

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
#: Heuristic scores in this corpus run roughly 2-20; probabilities are mapped
#: onto that range so the ambiguity margin behaves comparably for both.
SCORE_SCALE = 12.0


def _table(asks: list[str], preds: list[Prediction], top_k: int = 4) -> dict:
    out: dict[str, list[dict]] = {}
    for ask, p in zip(asks, preds):
        if p.predicted is None:
            continue
        ranked = p.ranked[:top_k] or [p.predicted]
        cands = []
        for i, dept in enumerate(ranked):
            prob = p.proba.get(dept) if p.proba else None
            conf = float(prob) if isinstance(prob, (int, float)) else (p.confidence if i == 0 else 0.0)
            cands.append({"agentId": dept, "confidence": round(conf, 4), "score": round(conf * SCORE_SCALE, 4)})
        out[ask] = cands
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["tfidf", "hybrid_tfidf"], required=True)
    ap.add_argument("--split", choices=["validation", "test"], default="test")
    ap.add_argument("--validation-version", default=datasets.DEFAULT_VALIDATION, choices=["v3"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # The harness replays EVERY case in the dataset, including the `none`-labelled
    # ones the classifier is not scored on, so the table must cover them too or
    # those asks silently fall back to the shipped router mid-run.
    path = (datasets.VALIDATION_PATHS[args.validation_version] if args.split == "validation"
            else datasets.TEST_PATH)
    raw = json.loads(path.read_text())
    asks = [c["ask"] for c in raw["cases"]]

    from train_tfidf import predictions_from
    ml = predictions_from(joblib.load(ARTIFACTS / "tfidf.joblib"), asks)

    if args.model.startswith("hybrid"):
        base = heuristic.predict(asks)
        # Fall through wherever the shipped orchestrator would decline to route
        # on evidence (score below MIN_BUSINESS_EVIDENCE), not merely where the
        # classifier returned nothing at all.
        MIN_BUSINESS_EVIDENCE = 3.0
        preds = [
            h if (h.predicted is not None and h.proba.get("_score", 0.0) >= MIN_BUSINESS_EVIDENCE) else m
            for h, m in zip(base, ml)
        ]
        # The hybrid must express the heuristic's own scores where it fired, or
        # the substitution would also be changing the ambiguity behaviour.
        table = {}
        for ask, h, chosen in zip(asks, base, preds):
            if chosen is h:
                table[ask] = None
                continue
            table.update(_table([ask], [chosen]))
    else:
        preds = ml
        table = _table(asks, preds)

    out = Path(args.out) if args.out else ARTIFACTS / f"router-{args.model}-{args.split}.json"
    out.write_text(json.dumps(table, indent=2) + "\n")
    print(f"{len(table)} asks -> {out}")
    if args.model.startswith("hybrid"):
        print(f"  (hybrid: {len(asks) - len(table)} asks left to the shipped router, "
              f"{len(table)} filled by {args.model.split('_')[1]})")


if __name__ == "__main__":
    main()
