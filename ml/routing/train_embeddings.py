"""
Model C — frozen sentence embeddings + logistic regression.

The embedding model is NOT fine-tuned. That is deliberate for this milestone:
the question is whether pretrained semantic representation beats a bag of
n-grams on this task, and fine-tuning would answer a different, later question
while making the result harder to attribute.

Runs locally on CPU. `all-MiniLM-L6-v2` is 384-dimensional, ~90 MB on disk, and
needs no API key, no network at inference time and no per-request cost — which
matters more than a fraction of a point of F1 for a router that sits in the hot
path of every owner request.

Same grouped cross-validation as the TF-IDF model, for the same reason.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score

import datasets
from evaluate import Prediction, confidence_analysis, print_confusion, risk_coverage, score

SEED = 20260828
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CACHE = ARTIFACTS / "embeddings-cache.npz"

C_GRID = [0.5, 1.0, 4.0, 10.0]


def _encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def embed(model, texts: list[str]) -> np.ndarray:
    return np.asarray(model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True))


def predictions_from(clf, model, asks: list[str]) -> list[Prediction]:
    classes = list(clf.classes_)
    out: list[Prediction] = []
    for ask in asks:
        t0 = time.perf_counter()
        vec = embed(model, [ask])
        embed_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        proba = clf.predict_proba(vec)[0]
        clf_ms = (time.perf_counter() - t1) * 1000
        order = np.argsort(-proba)
        p = Prediction(
            predicted=classes[order[0]],
            confidence=float(proba[order[0]]),
            ranked=[classes[i] for i in order],
            latency_ms=embed_ms + clf_ms,
            proba={classes[i]: round(float(proba[i]), 6) for i in order[:8]},
        )
        p.proba["_embed_ms"] = round(embed_ms, 4)
        p.proba["_clf_ms"] = round(clf_ms, 4)
        out.append(p)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ARTIFACTS / "embedding_lr.joblib"))
    parser.add_argument("--report", default=str(ARTIFACTS / "embeddings-validation.json"))
    args = parser.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    train = datasets.load_train()
    validation = datasets.load_validation()

    print(f"loading {EMBED_MODEL} (CPU) ...")
    t0 = time.perf_counter()
    model = _encoder()
    load_s = time.perf_counter() - t0
    dim = model.get_sentence_embedding_dimension()
    print(f"loaded in {load_s:.1f}s, dim={dim}")

    t0 = time.perf_counter()
    Xtr = embed(model, train.asks)
    encode_s = time.perf_counter() - t0
    print(f"encoded {len(train)} training asks in {encode_s:.1f}s "
          f"({encode_s / len(train) * 1000:.2f} ms/ask batched)")

    groups = train.groups
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    print(f"\n5-fold GROUPED cross-validation ({len({g for g in groups})} templates):")
    results = []
    for C in C_GRID:
        clf = LogisticRegression(C=C, max_iter=3000, random_state=SEED)
        s = cross_val_score(clf, Xtr, train.labels, groups=groups, cv=cv, scoring="f1_macro", n_jobs=-1)
        results.append((float(s.mean()), float(s.std()), C))
        print(f"  macro-F1 {s.mean():.4f} +/- {s.std():.4f}   C={C}")

    best_mean, best_std, best_C = max(results, key=lambda r: r[0])
    print(f"\nselected: C={best_C}  (grouped CV macro-F1 {best_mean:.4f})")

    clf = LogisticRegression(C=best_C, max_iter=3000, random_state=SEED)
    clf.fit(Xtr, train.labels)
    joblib.dump(clf, args.out)
    head_kb = Path(args.out).stat().st_size / 1024

    preds = predictions_from(clf, model, validation.asks)
    m = score("Embedding + LR", "validation", validation.labels, preds)
    print(f"\n{m.model} on {m.split}: acc {m.accuracy:.4f} | macroF1 {m.macro_f1:.4f} "
          f"| top2 {m.top2_accuracy:.4f} | p50 {m.latency_p50_ms:.3f}ms | p95 {m.latency_p95_ms:.3f}ms")
    print_confusion(m)

    embed_ms = [p.proba["_embed_ms"] for p in preds]
    clf_ms = [p.proba["_clf_ms"] for p in preds]
    report = {
        "model": "embedding_lr",
        "embedding_model": EMBED_MODEL,
        "embedding_dim": dim,
        "fine_tuned": False,
        "runs_locally": True,
        "api_cost_per_1k": 0.0,
        "cv_scheme": "StratifiedGroupKFold(5) grouped by template_id",
        "cv_macro_f1_mean": round(best_mean, 4),
        "cv_macro_f1_std": round(best_std, 4),
        "cv_grid": [{"C": C, "mean": round(mn, 4), "std": round(sd, 4)} for mn, sd, C in results],
        "classifier_head_kb": round(head_kb, 1),
        "encoder_load_seconds": round(load_s, 2),
        "latency_breakdown_ms": {
            "embed_p50": round(float(np.percentile(embed_ms, 50)), 3),
            "embed_p95": round(float(np.percentile(embed_ms, 95)), 3),
            "classifier_p50": round(float(np.percentile(clf_ms, 50)), 4),
            "classifier_p95": round(float(np.percentile(clf_ms, 95)), 4),
        },
        "validation": m.__dict__,
        "risk_coverage": risk_coverage(validation.labels, preds),
        "confidence": confidence_analysis(validation.labels, preds),
        "seed": SEED,
        "train_version": train.version,
        "validation_version": validation.version,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\nclassifier head {head_kb:.1f} KB -> {args.out}\nreport -> {args.report}")


if __name__ == "__main__":
    main()
