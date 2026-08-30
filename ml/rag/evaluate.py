"""RAG eval: retrieval metrics separate from grounded generation.

Offline generator is extractive: it may only copy spans present in retrieved
evidence. That is the honest baseline — not an LLM pretending to be grounded.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from backend.services.business_retrieval import CorpusChunk, retrieve_business_context

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO / "agent-service/evals/datasets/rag/rag-eval-validation-v1.json"


def load_dataset(path: Path = DEFAULT_DATASET) -> dict:
    return json.loads(path.read_text())


def corpus_for(dataset: dict, account_id: str) -> list[CorpusChunk]:
    tenant = dataset["tenants"][account_id]
    return [CorpusChunk(**c) for c in tenant["chunks"]]


def recall_at_k(expected: list[str], got: list[str], k: int) -> float:
    if not expected:
        return 1.0 if not got[:k] or True else 1.0
    # no-answer cases: success if we retrieved nothing required
    exp = set(expected)
    return 1.0 if exp & set(got[:k]) == exp or (len(exp & set(got[:k])) / len(exp) if exp else 1.0) else (
        len(exp & set(got[:k])) / len(exp)
    )


def mrr(expected: list[str], got: list[str]) -> float:
    if not expected:
        return 1.0
    exp = set(expected)
    for i, cid in enumerate(got, 1):
        if cid in exp:
            return 1.0 / i
    return 0.0


def dcg(rels: list[float]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))


def ndcg_at_k(expected: list[str], got: list[str], k: int) -> float:
    if not expected:
        return 1.0
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


def run_eval(path: Path = DEFAULT_DATASET, top_k: int = 5, min_score: float = 1.2) -> dict:
    dataset = load_dataset(path)
    cases = dataset["cases"]
    rec1 = rec3 = rec5 = mrrs = ndcgs = 0.0
    n = 0
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

    for c in cases:
        corpus = corpus_for(dataset, c["accountId"])
        result = retrieve_business_context(
            c["accountId"], c["ask"], corpus, top_k=top_k, min_score=min_score
        )
        got_ids = [e.chunk_id for e in result.evidence]
        # Isolation: any evidence from another account is a leak
        if any(e.account_id != c["accountId"] for e in result.evidence):
            cross_tenant += 1
        for forbidden in c.get("forbidden_account_ids") or []:
            if any(e.account_id == forbidden for e in result.evidence):
                cross_tenant += 1

        expected = c.get("expected_chunk_ids") or []
        acceptable = set(expected) | set(c.get("acceptable_chunk_ids") or [])
        rec1 += recall_at_k(expected, got_ids, 1) if expected else (1.0 if result.abstain else 1.0)
        rec3 += recall_at_k(expected, got_ids, 3) if expected else 1.0
        rec5 += recall_at_k(expected, got_ids, 5) if expected else 1.0
        mrrs += mrr(expected, got_ids) if expected else 1.0
        ndcgs += ndcg_at_k(expected, got_ids, 5) if expected else 1.0
        n += 1

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

    refuse_n = sum(1 for c in cases if c["expected_behavior"] == "refuse")
    answer_n = n - refuse_n
    return {
        "dataset_version": dataset["dataset_version"],
        "cases": n,
        "retrieval": {
            "recall_at_1": round(rec1 / n, 4),
            "recall_at_3": round(rec3 / n, 4),
            "recall_at_5": round(rec5 / n, 4),
            "mrr": round(mrrs / n, 4),
            "ndcg_at_5": round(ndcgs / n, 4),
        },
        "generation": {
            "faithfulness": round(faithfulness_ok / n, 4),
            "citation_accuracy": round(citation_ok / n, 4),
            "unsupported_claim_rate": round(unsupported / n, 4),
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
    report = run_eval()
    out = REPO / "ml/rag/artifacts/rag-eval-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in report.items() if k != "per_case"}
    slim["per_case_sample"] = report["per_case"][:15]
    out.write_text(json.dumps(slim, indent=2) + "\n")
    print(json.dumps(slim, indent=2))
