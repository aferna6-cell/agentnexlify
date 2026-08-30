"""Retrieval bakeoff on rag-eval-validation-v1.

A. BM25  B. TF-IDF cosine  C. Hybrid RRF  D. Hybrid + overlap rerank

Dense Voyage is recorded as unmeasured when VOYAGE_API_KEY is absent.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from backend.services.business_retrieval import CorpusChunk
from backend.services.rag_bm25 import BM25, tokenize
from ml.rag.evaluate import DEFAULT_DATASET, load_dataset, ndcg_at_k, recall_at_k, mrr

REPO = Path(__file__).resolve().parents[2]


def _tfidf_rank(query: str, docs: list[str]) -> list[tuple[int, float]]:
    q = tokenize(query)
    if not q:
        return []
    n = len(docs)
    tokenized = [tokenize(d) for d in docs]
    df: Counter[str] = Counter()
    for doc in tokenized:
        df.update(set(doc))

    def idf(t: str) -> float:
        return math.log((n + 1) / (df.get(t, 0) + 1)) + 1

    q_tf = Counter(q)
    q_vec = {t: q_tf[t] * idf(t) for t in q_tf}
    qn = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
    scored = []
    for i, doc in enumerate(tokenized):
        tf = Counter(doc)
        d_vec = {t: tf[t] * idf(t) for t in tf}
        dn = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0
        dot = sum(q_vec[t] * d_vec.get(t, 0.0) for t in q_vec)
        s = dot / (qn * dn)
        if s > 0:
            scored.append((i, s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def _rrf(rank_lists: list[list[int]], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + r + 1)
    return [i for i, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def _rerank(query: str, docs: list[str], order: list[int]) -> list[int]:
    q = set(tokenize(query))

    def ov(i: int) -> tuple[int, int]:
        return (len(q & set(tokenize(docs[i]))), -i)

    return sorted(order, key=ov, reverse=True)


def _score_method(dataset: dict, method: str) -> dict:
    rec1 = rec3 = rec5 = mrrs = ndcgs = 0.0
    n = 0
    for c in dataset["cases"]:
        chunks = [CorpusChunk(**row) for row in dataset["tenants"][c["accountId"]]["chunks"] if row["status"] == "active"]
        docs = [f"{x.title} {x.section} {x.content}" for x in chunks]
        if method == "bm25":
            order = [h.index for h in BM25(docs).score(c["ask"])]
        elif method == "tfidf":
            order = [i for i, _ in _tfidf_rank(c["ask"], docs)]
        elif method == "hybrid":
            a = [h.index for h in BM25(docs).score(c["ask"])]
            b = [i for i, _ in _tfidf_rank(c["ask"], docs)]
            order = _rrf([a, b])
        elif method == "hybrid_rerank":
            a = [h.index for h in BM25(docs).score(c["ask"])]
            b = [i for i, _ in _tfidf_rank(c["ask"], docs)]
            order = _rerank(c["ask"], docs, _rrf([a, b])[:12])
        else:
            raise ValueError(method)
        got = [chunks[i].chunk_id for i in order[:5]]
        expected = c.get("expected_chunk_ids") or []
        if not expected:
            continue
        rec1 += recall_at_k(expected, got, 1)
        rec3 += recall_at_k(expected, got, 3)
        rec5 += recall_at_k(expected, got, 5)
        mrrs += mrr(expected, got)
        ndcgs += ndcg_at_k(expected, got, 5)
        n += 1
    return {
        "recall_at_1": round(rec1 / n, 4) if n else None,
        "recall_at_3": round(rec3 / n, 4) if n else None,
        "recall_at_5": round(rec5 / n, 4) if n else None,
        "mrr": round(mrrs / n, 4) if n else None,
        "ndcg_at_5": round(ndcgs / n, 4) if n else None,
        "labelled_cases": n,
    }


def main() -> None:
    dataset = load_dataset(DEFAULT_DATASET)
    methods = ["bm25", "tfidf", "hybrid", "hybrid_rerank"]
    results = {m: _score_method(dataset, m) for m in methods}
    winner = max(results, key=lambda m: (results[m]["mrr"], results[m]["recall_at_5"]))
    payload = {
        "dataset_version": dataset["dataset_version"],
        "dense_voyage": "unmeasured (no VOYAGE_API_KEY in this environment)",
        "methods": results,
        "selected": winner,
        "note": (
            "Retrieval-only pick on labelled cases. Production still uses BM25 "
            "via retrieve_business_context until Voyage dense is measured. "
            "TF-IDF is not promoted (same M6 downstream+ops rule)."
        ),
    }
    out = REPO / "ml/rag/artifacts/rag-bakeoff-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
