"""Chunking bakeoff: paragraph vs fixed vs section on the authored corpus."""

from __future__ import annotations

import json
from pathlib import Path

from backend.services.business_retrieval import CorpusChunk, retrieve_business_context
from ml.rag.chunking import STRATEGIES
from ml.rag.evaluate import DEFAULT_DATASET, load_dataset, recall_at_k

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    dataset = load_dataset(DEFAULT_DATASET)
    # Re-chunk each tenant's concatenated docs — only useful as a relative signal
    # because gold chunk ids are tied to the authored (section-like) split.
    report = {
        "note": (
            "Gold labels were authored against the curated chunks. "
            "Re-chunking changes ids, so this reports retrieval-of-phrase, not id recall."
        ),
        "strategies": {},
    }
    for name, fn in STRATEGIES.items():
        hits = 0
        n = 0
        for c in dataset["cases"]:
            if c["expected_behavior"] != "answer" or not c.get("expected_answer_contains"):
                continue
            raw = "\n\n".join(
                ch["content"] for ch in dataset["tenants"][c["accountId"]]["chunks"] if ch["status"] == "active"
            )
            pieces = fn(raw)
            corpus = [
                CorpusChunk(
                    f"{name}#{p.chunk_index}",
                    "doc",
                    c["accountId"],
                    "doc",
                    p.section,
                    p.content,
                    "prices",
                    f"doc §{p.chunk_index}",
                )
                for p in pieces
            ]
            result = retrieve_business_context(c["accountId"], c["ask"], corpus, min_score=0.5)
            blob = "\n".join(e.content for e in result.evidence).lower()
            if any(p.lower() in blob for p in c["expected_answer_contains"]):
                hits += 1
            n += 1
        report["strategies"][name] = {"phrase_hit_rate": round(hits / n, 4) if n else None, "n": n}
    out = REPO / "ml/rag/artifacts/rag-chunking-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
