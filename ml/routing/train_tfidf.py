"""
Model B — TF-IDF + multinomial logistic regression.

The classical baseline, and the one worth beating before anything heavier is
justified. Word n-grams catch the vocabulary ("payroll", "invoice"); character
n-grams catch the parts of this corpus that words cannot — the typos, the
missing apostrophes, the shouty uppercase, and the fact that owners write
"apointment".

Model selection is 5-fold cross-validation on TRAIN, GROUPED BY TEMPLATE. The
grouping is the load-bearing detail. This corpus is generated from ~200 authored
templates, so ordinary k-fold puts different slot-fills of the same template in
both the fit fold and the scoring fold — and then reports memorisation as
generalisation. The first run of this experiment did exactly that: CV macro-F1
0.998 against 0.70 on the real validation split. Grouping by template makes the
CV number an estimate of performance on phrasings the model has never seen,
which is the only kind of estimate worth having.

The 30-case validation split is far too small to choose hyperparameters against
without fitting to noise; it is used afterwards as the out-of-distribution check
that the CV winner still behaves on real product data.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline

import datasets
from evaluate import Prediction, confidence_analysis, print_confusion, risk_coverage, score

SEED = 20260828
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


@dataclass(frozen=True)
class Config:
    name: str
    word_ngram: tuple[int, int]
    char_ngram: tuple[int, int] | None
    C: float
    min_df: int = 1
    class_weight: str | None = None


#: A deliberately small grid. The point of this milestone is to find out whether
#: a classical model is competitive, not to squeeze the last half-point out of
#: one — and a large search over 1,216 examples would mostly be fitting the
#: cross-validation folds.
GRID = [
    Config("word(1,1) C=1", (1, 1), None, 1.0),
    Config("word(1,2) C=1", (1, 2), None, 1.0),
    Config("word(1,2) C=4", (1, 2), None, 4.0),
    Config("word(1,2)+char(3,5) C=4", (1, 2), (3, 5), 4.0),
    Config("word(1,2)+char(3,5) C=10", (1, 2), (3, 5), 10.0),
    Config("word(1,2)+char(2,5) C=4 balanced", (1, 2), (2, 5), 4.0, class_weight="balanced"),
]


def build_pipeline(cfg: Config) -> Pipeline:
    word = TfidfVectorizer(
        analyzer="word", ngram_range=cfg.word_ngram, min_df=cfg.min_df,
        sublinear_tf=True, lowercase=True, strip_accents="unicode",
    )
    if cfg.char_ngram:
        char = TfidfVectorizer(
            analyzer="char_wb", ngram_range=cfg.char_ngram, min_df=2,
            sublinear_tf=True, lowercase=True, strip_accents="unicode",
        )
        features = FeatureUnion([("word", word), ("char", char)])
    else:
        features = FeatureUnion([("word", word)])
    return Pipeline([
        ("features", features),
        # scikit-learn 1.9 dropped `multi_class`; LogisticRegression is
        # multinomial by default for multi-class problems with lbfgs.
        ("clf", LogisticRegression(
            C=cfg.C, max_iter=2000, class_weight=cfg.class_weight, random_state=SEED,
        )),
    ])


def predictions_from(pipe: Pipeline, asks: list[str]) -> list[Prediction]:
    classes = list(pipe.named_steps["clf"].classes_)
    out: list[Prediction] = []
    for ask in asks:
        t0 = time.perf_counter()
        proba = pipe.predict_proba([ask])[0]
        elapsed = (time.perf_counter() - t0) * 1000
        order = np.argsort(-proba)
        out.append(Prediction(
            predicted=classes[order[0]],
            confidence=float(proba[order[0]]),
            ranked=[classes[i] for i in order],
            latency_ms=elapsed,
            proba={classes[i]: round(float(proba[i]), 6) for i in order[:8]},
        ))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ARTIFACTS / "tfidf.joblib"))
    parser.add_argument("--report", default=str(ARTIFACTS / "tfidf-validation.json"))
    args = parser.parse_args()

    train = datasets.load_train()
    validation = datasets.load_validation()
    X, y = train.asks, train.labels

    print(f"train {len(train)} | validation {len(validation)}\n")
    groups = train.groups
    n_templates = len({g for g in groups})
    print(f"5-fold GROUPED cross-validation on TRAIN ({n_templates} templates), model selection:")
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = []
    for cfg in GRID:
        scores = cross_val_score(build_pipeline(cfg), X, y, groups=groups, cv=cv, scoring="f1_macro", n_jobs=-1)
        results.append((float(scores.mean()), float(scores.std()), cfg))
        print(f"  macro-F1 {scores.mean():.4f} +/- {scores.std():.4f}   {cfg.name}")

    best_mean, best_std, best_cfg = max(results, key=lambda r: r[0])
    print(f"\nselected: {best_cfg.name}  (CV macro-F1 {best_mean:.4f})")

    pipe = build_pipeline(best_cfg)
    t0 = time.perf_counter()
    pipe.fit(X, y)
    fit_s = time.perf_counter() - t0

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, args.out)
    size_kb = Path(args.out).stat().st_size / 1024

    preds = predictions_from(pipe, validation.asks)
    m = score("TF-IDF + LR", "validation", validation.labels, preds)
    print(f"\n{m.model} on {m.split}: acc {m.accuracy:.4f} | macroF1 {m.macro_f1:.4f} "
          f"| top2 {m.top2_accuracy:.4f} | p50 {m.latency_p50_ms:.3f}ms | p95 {m.latency_p95_ms:.3f}ms")
    print_confusion(m)

    report = {
        "model": "tfidf_lr",
        "config": best_cfg.__dict__,
        "cv_scheme": "StratifiedGroupKFold(5) grouped by template_id",
        "cv_groups": n_templates,
        "cv_macro_f1_mean": round(best_mean, 4),
        "cv_macro_f1_std": round(best_std, 4),
        "cv_grid": [{"name": c.name, "mean": round(mn, 4), "std": round(sd, 4)} for mn, sd, c in results],
        "fit_seconds": round(fit_s, 3),
        "artifact_kb": round(size_kb, 1),
        "vocabulary_size": int(sum(
            len(v.vocabulary_) for _, v in pipe.named_steps["features"].transformer_list
        )),
        "validation": score("TF-IDF + LR", "validation", validation.labels, preds).__dict__,
        "risk_coverage": risk_coverage(validation.labels, preds),
        "confidence": confidence_analysis(validation.labels, preds),
        "seed": SEED,
        "train_version": train.version,
        "validation_version": validation.version,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\nartifact {size_kb:.1f} KB -> {args.out}\nreport -> {args.report}")


if __name__ == "__main__":
    main()
