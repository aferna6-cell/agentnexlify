#!/usr/bin/env python3
"""Ask the brain a natural-language question (semantic search over the local index).

Loads _index/embeddings.json (built by embed_notes.py), embeds the query with Voyage, and
prints the top-k most relevant notes by cosine similarity. Read-only.

Env: VOYAGE_API_KEY. Usage: python3 _tools/ask.py "how is billing priced?" [k]
"""
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
IDX = VAULT / "_index" / "embeddings.json"


def embed_query(text, key, model):
    body = json.dumps({"input": [text], "model": model, "input_type": "query"}).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["data"][0]["embedding"]


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def main():
    if len(sys.argv) < 2:
        print('usage: python3 _tools/ask.py "your question" [k]')
        return 2
    q = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    if not IDX.exists():
        print("No index. Run: python3 _tools/embed_notes.py")
        return 1
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        print("VOYAGE_API_KEY not set.")
        return 1
    data = json.loads(IDX.read_text())
    qv = embed_query(q, key, data.get("model", "voyage-3-lite"))
    scored = sorted(((cos(qv, it["embedding"]), it) for it in data["items"]),
                    key=lambda x: x[0], reverse=True)
    print(f"Top {k} for: {q}\n")
    for score, it in scored[:k]:
        print(f"  {score:.3f}  {it['title']}  ({it['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
