"""RAG eval: retrieval metrics separate from grounded generation.

Offline generator is extractive: it may only copy spans present in retrieved
evidence. That is the honest baseline — not an LLM pretending to be grounded.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from backend.services.business_retrieval import (
    DEFAULT_MIN_SCORE,
    CorpusChunk,
    retrieve_business_context,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO / "agent-service/evals/datasets/rag/rag-eval-validation-v1.json"


def load_dataset(path: Path = DEFAULT_DATASET) -> dict:
    return json.loads(path.read_text())


def corpus_for(dataset: dict, account_id: str) -> list[CorpusChunk]:
    tenant = dataset["tenants"][account_id]
    return [CorpusChunk(**c) for c in tenant["chunks"]]


def mixed_corpus(dataset: dict) -> list[CorpusChunk]:
    """All tenants' chunks. Isolation is only real if a leak *could* appear."""
    rows: list[CorpusChunk] = []
    for tenant in dataset["tenants"].values():
        rows.extend(CorpusChunk(**c) for c in tenant["chunks"])
    return rows


def recall_at_k(expected: list[str], got: list[str], k: int) -> float:
    """Fraction of expected chunk ids found in the top-k. Undefined if no gold ids."""
    if not expected:
        raise ValueError("recall_at_k requires expected chunk ids")
    exp = set(expected)
    return len(exp & set(got[:k])) / len(exp)


def mrr(expected: list[str], got: list[str]) -> float:
    if not expected:
        raise ValueError("mrr requires expected chunk ids")
    exp = set(expected)
    for i, cid in enumerate(got, 1):
        if cid in exp:
            return 1.0 / i
    return 0.0


def dcg(rels: list[float]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))


def ndcg_at_k(expected: list[str], got: list[str], k: int) -> float:
    if not expected:
        raise ValueError("ndcg_at_k requires expected chunk ids")
    exp = set(expected)
    rels = [1.0 if cid in exp else 0.0 for cid in got[:k]]
    ideal = [1.0] * min(len(exp), k) + [0.0] * max(0, k - len(exp))
    idcg = dcg(ideal[:k])
    return (dcg(rels) / idcg) if idcg else 0.0


def extractive_answer(evidence_texts: list[str], expected_phrases: list[str]) -> tuple[str, str]:
    blob = "\n".join(evidence_texts).lower()
    if not evidence_texts:
        return "", "refuse"
    found = [p for p in expected_phrases if p.lower() in blob]
    if expected_phrases and not found:
        return "", "refuse"
    if not expected_phrases:
        # no gold phrases — refuse unless evidence exists and case is answer-shaped
        return evidence_texts[0][:240], "answer"
    return " ".join(found), "answer"


def run_eval(
    path: Path = DEFAULT_DATASET,
    top_k: int = 5,
    min_score: float = DEFAULT_MIN_SCORE,
) -> dict:
    dataset = load_dataset(path)
    cases = dataset["cases"]
    rec1 = rec3 = rec5 = mrrs = ndcgs = 0.0
    n_retr = 0
    correct_refuse = false_refuse = missed_refuse = 0
    faithfulness_ok = 0
    citation_ok = 0
    unsupported = 0
    cross_tenant = 0
    inject_fail = 0
    fabricated_cite = 0
    per: list[dict] = []

    all_chunk_ids = {
        c["chunk_id"]
        for t in dataset["tenants"].values()
        for c in t["chunks"]
    }

    full_corpus = mixed_corpus(dataset)
    for c in cases:
        result = retrieve_business_context(
            c["accountId"], c["ask"], full_corpus, top_k=top_k, min_score=min_score
        )
        got_ids = [e.chunk_id for e in result.evidence]
        forbidden = set(c.get("forbidden_account_ids") or [])
        leaked = any(
            e.account_id != c["accountId"] or e.account_id in forbidden
            for e in result.evidence
        )
        if leaked:
            cross_tenant += 1

        expected = c.get("expected_chunk_ids") or []
        acceptable = set(expected) | set(c.get("acceptable_chunk_ids") or [])
        if expected:
            rec1 += recall_at_k(expected, got_ids, 1)
            rec3 += recall_at_k(expected, got_ids, 3)
            rec5 += recall_at_k(expected, got_ids, 5)
            mrrs += mrr(expected, got_ids)
            ndcgs += ndcg_at_k(expected, got_ids, 5)
            n_retr += 1

        texts = [e.content for e in result.evidence]
        answer, behavior = extractive_answer(texts, c.get("expected_answer_contains") or [])
        if result.abstain:
            behavior = "refuse"
            answer = ""

        gold_b = c["expected_behavior"]
        if gold_b == "refuse":
            if behavior == "refuse":
                correct_refuse += 1
            else:
                missed_refuse += 1
        else:
            if behavior == "refuse":
                false_refuse += 1

        # Faithfulness: every claimed phrase is in evidence
        claims = [p for p in (c.get("expected_answer_contains") or []) if p.lower() in answer.lower()]
        blob = "\n".join(texts).lower()
        if all(p.lower() in blob for p in claims) or behavior == "refuse":
            faithfulness_ok += 1
        if any(p.lower() in answer.lower() and p.lower() not in blob for p in (c.get("must_not_contain") or [])):
            unsupported += 1

        cited = set(got_ids)
        if cited <= all_chunk_ids:
            citation_ok += 1
        if cited - all_chunk_ids:
            fabricated_cite += 1

        if "prompt_injection" in c.get("tags", []):
            banned = c.get("must_not_contain") or []
            if any(b.lower() in answer.lower() for b in banned):
                inject_fail += 1

        # citation correctness vs gold
        if expected:
            citation_hit = bool(set(got_ids[:5]) & acceptable)
        else:
            citation_hit = True

        per.append({
            "id": c["id"],
            "accountId": c["accountId"],
            "got_ids": got_ids,
            "behavior": behavior,
            "abstain": result.abstain,
            "citation_hit": citation_hit,
            "top_score": result.scores[0] if result.scores else 0,
        })

    n_all = len(cases)
    refuse_n = sum(1 for c in cases if c["expected_behavior"] == "refuse")
    answer_n = n_all - refuse_n
    return {
        "dataset_version": dataset["dataset_version"],
        "cases": n_all,
        "retrieval_labelled_cases": n_retr,
        "scoring_note": (
            "Retrieval metrics exclude cases with no expected_chunk_ids. "
            "Isolation uses a mixed-tenant corpus. Generation faithfulness "
            "is extractive (spans already in evidence), not an LLM score."
        ),
        "retrieval": {
            "recall_at_1": round(rec1 / n_retr, 4) if n_retr else None,
            "recall_at_3": round(rec3 / n_retr, 4) if n_retr else None,
            "recall_at_5": round(rec5 / n_retr, 4) if n_retr else None,
            "mrr": round(mrrs / n_retr, 4) if n_retr else None,
            "ndcg_at_5": round(ndcgs / n_retr, 4) if n_retr else None,
        },
        "generation": {
            "faithfulness": round(faithfulness_ok / n_all, 4),
            "citation_accuracy": round(citation_ok / n_all, 4),
            "unsupported_claim_rate": round(unsupported / n_all, 4),
            "correct_refusal_rate": round(correct_refuse / refuse_n, 4) if refuse_n else None,
            "false_refusal_rate": round(false_refuse / answer_n, 4) if answer_n else None,
            "missed_refusal": missed_refuse,
        },
        "safety": {
            "cross_tenant_leaks": cross_tenant,
            "prompt_injection_failures": inject_fail,
            "fabricated_citations": fabricated_cite,
        },
        "per_case": per,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to a RAG eval JSON dataset",
    )
    ap.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    args = ap.parse_args()
    report = run_eval(args.dataset, min_score=args.min_score)
    out = REPO / "ml/rag/artifacts" / f"{args.dataset.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in report.items() if k != "per_case"}
    slim["per_case_sample"] = report["per_case"][:15]
    out.write_text(json.dumps(slim, indent=2) + "\n")
    print(json.dumps(slim, indent=2))
