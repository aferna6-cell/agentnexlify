"""Downstream BM25 vs TF-IDF after abstention (validation only).

Retrieval-only Recall@1 is not enough. Compare grounded answer/refusal
behavior under the same abstention contract. Dense/Voyage is recorded as
unmeasured when VOYAGE_API_KEY is absent — never fabricated.
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from pathlib import Path

from backend.services.business_retrieval import (
    DEFAULT_MIN_SCORE,
    CorpusChunk,
    Evidence,
    RetrievalResult,
    _expand_query,
    _has_injection,
    _has_money_signal,
    _looks_price_ask,
    _MASS_ACTION,
    _OUT_OF_SCOPE,
    _CREDENTIAL_OR_OVERRIDE,
    _UNSAFE_IMPERATIVE,
    _rerank_trusted,
    _significant_overlap,
    sanitize_evidence_text,
)
from backend.services.rag_bm25 import BM25, tokenize
from ml.rag.evaluate import DEFAULT_DATASET, extractive_answer, load_dataset, mrr, ndcg_at_k, recall_at_k

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "ml/rag/artifacts/rag-downstream-bakeoff-v1.json"


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


def _retrieve(method: str, account_id: str, ask: str, corpus: list[CorpusChunk], min_score: float) -> RetrievalResult:
    scoped = [c for c in corpus if c.account_id == account_id and c.status == "active"]
    if not scoped:
        return RetrievalResult([], True, "no_approved_knowledge")
    if _OUT_OF_SCOPE.search(ask) or _MASS_ACTION.search(ask) or _UNSAFE_IMPERATIVE.search(ask) or _CREDENTIAL_OR_OVERRIDE.search(ask):
        return RetrievalResult([], True, "insufficient_evidence")

    docs = [f"{c.title} {c.section} {c.content}" for c in scoped]
    expanded = _expand_query(ask)
    if method == "bm25":
        ranked = [(h.index, h.score) for h in BM25(docs).score(expanded)]
    elif method == "tfidf":
        ranked = _tfidf_rank(expanded, docs)
    else:
        raise ValueError(method)

    raw: list[Evidence] = []
    for idx, score in ranked[:10]:
        c = scoped[idx]
        raw.append(
            Evidence(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                account_id=c.account_id,
                title=c.title,
                section=c.section,
                content=sanitize_evidence_text(c.content),
                source_type=c.source_type,
                score=round(score, 4),
                citation_label=c.citation_label,
                status=c.status,
            )
        )
    trusted = [e for e in raw if not _has_injection(e.content)]
    untrusted = [e for e in raw if _has_injection(e.content)]
    primary = _rerank_trusted(ask, trusted) if trusted else untrusted
    picked = primary[:5]
    scores = [e.score for e in picked]
    if not picked or picked[0].score < min_score:
        # TF-IDF cosine scores are ~0–1; apply a relative floor for fairness.
        if method == "tfidf":
            floor = 0.05 if min_score >= 1.0 else min_score
            if not picked or picked[0].score < floor:
                return RetrievalResult(picked, True, "insufficient_evidence", scores)
        else:
            return RetrievalResult(picked, True, "insufficient_evidence", scores)
    if not trusted and untrusted:
        return RetrievalResult(picked, True, "untrusted_document", scores)
    top = picked[0]
    if _significant_overlap(ask, top.title, top.content) < 1:
        return RetrievalResult(picked, True, "low_overlap", scores)
    if _looks_price_ask(ask) and not _has_money_signal(top.content):
        return RetrievalResult(picked, True, "insufficient_evidence", scores)
    return RetrievalResult(picked, False, "ok", scores)


def eval_method(dataset: dict, method: str, min_score: float = DEFAULT_MIN_SCORE) -> dict:
    cases = dataset["cases"]
    full = [CorpusChunk(**c) for t in dataset["tenants"].values() for c in t["chunks"]]
    rec1 = mrrs = 0.0
    n_retr = 0
    correct_refuse = false_refuse = missed_refuse = 0
    unsupported = cross = inject = 0
    answered = 0
    answer_n = sum(1 for c in cases if c["expected_behavior"] == "answer")
    refuse_n = sum(1 for c in cases if c["expected_behavior"] == "refuse")

    for c in cases:
        result = _retrieve(method, c["accountId"], c["ask"], full, min_score)
        got = [e.chunk_id for e in result.evidence]
        if any(e.account_id != c["accountId"] for e in result.evidence):
            cross += 1
        expected = c.get("expected_chunk_ids") or []
        if expected:
            rec1 += recall_at_k(expected, got, 1)
            mrrs += mrr(expected, got)
            n_retr += 1
        texts = [e.content for e in result.evidence]
        answer, behavior = extractive_answer(texts, c.get("expected_answer_contains") or [])
        if result.abstain:
            behavior = "refuse"
            answer = ""
        else:
            answered += 1 if c["expected_behavior"] == "answer" else 0
        gold = c["expected_behavior"]
        if gold == "refuse":
            if behavior == "refuse":
                correct_refuse += 1
            else:
                missed_refuse += 1
        elif behavior == "refuse":
            false_refuse += 1
        blob = "\n".join(texts).lower()
        if any(p.lower() in answer.lower() and p.lower() not in blob for p in (c.get("must_not_contain") or [])):
            unsupported += 1
        if "prompt_injection" in c.get("tags", []):
            if any(b.lower() in answer.lower() for b in (c.get("must_not_contain") or [])):
                inject += 1

    return {
        "method": method,
        "retrieval_labelled_cases": n_retr,
        "recall_at_1": round(rec1 / n_retr, 4) if n_retr else None,
        "mrr": round(mrrs / n_retr, 4) if n_retr else None,
        "answered_coverage": round(answered / answer_n, 4) if answer_n else None,
        "correct_refusal_rate": round(correct_refuse / refuse_n, 4) if refuse_n else None,
        "false_refusal_rate": round(false_refuse / answer_n, 4) if answer_n else None,
        "missed_refusal": missed_refuse,
        "unsupported_claim_rate": round(unsupported / len(cases), 4),
        "cross_tenant_leaks": cross,
        "prompt_injection_failures": inject,
    }


def main() -> None:
    dataset = load_dataset(DEFAULT_DATASET)
    bm25 = eval_method(dataset, "bm25")
    tfidf = eval_method(dataset, "tfidf")
    voyage = {
        "method": "voyage_dense",
        "status": "unmeasured",
        "reason": "VOYAGE_API_KEY absent" if not os.environ.get("VOYAGE_API_KEY") else "not run in this bakeoff",
    }
    # Promote only if downstream refusal/answer quality is strictly better.
    promote_tfidf = (
        (tfidf["correct_refusal_rate"] or 0) >= (bm25["correct_refusal_rate"] or 0)
        and (tfidf["false_refusal_rate"] or 1) <= (bm25["false_refusal_rate"] or 1)
        and (tfidf["answered_coverage"] or 0) >= (bm25["answered_coverage"] or 0)
        and (tfidf["unsupported_claim_rate"] or 1) <= (bm25["unsupported_claim_rate"] or 1)
        and (tfidf["cross_tenant_leaks"] or 1) == 0
        and (
            (tfidf["answered_coverage"] or 0) > (bm25["answered_coverage"] or 0)
            or (tfidf["correct_refusal_rate"] or 0) > (bm25["correct_refusal_rate"] or 0)
            or (tfidf["false_refusal_rate"] or 1) < (bm25["false_refusal_rate"] or 1)
        )
    )
    report = {
        "dataset": "rag-eval-validation-v1",
        "principle": "downstream business correctness > isolated retrieval metric",
        "bm25": bm25,
        "tfidf": tfidf,
        "voyage": voyage,
        "production_candidate": "tfidf" if promote_tfidf else "bm25",
        "notes": [
            "TF-IDF may win isolated Recall@1; promotion requires better or equal "
            "grounded answer/refusal metrics under the same abstention contract.",
            "Voyage dense remains optional; absence alone does not block M7.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
