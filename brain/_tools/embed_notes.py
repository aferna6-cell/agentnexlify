#!/usr/bin/env python3
"""Build a local semantic index over the vault notes (for natural-language recall).

Uses Voyage embeddings (voyage-3-lite, 512d — matches the product's os_memory_entries stack)
and writes a LOCAL index to _index/embeddings.json. No Supabase/DB writes, no external
mutations. stdlib only (urllib).

Env: VOYAGE_API_KEY (required). Missing → prints how to set it and exits 0 (graceful).
Run: python3 _tools/embed_notes.py    then query with: python3 _tools/ask.py "your question"
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
OUT = VAULT / "_index" / "embeddings.json"
MODEL = "voyage-3-lite"
BATCH = 64


def md_files():
    skip = {"_tools", "_index"}
    return [p for p in VAULT.rglob("*.md") if not skip & set(p.parts)]


def embed(texts, key, input_type):
    body = json.dumps({"input": texts, "model": MODEL, "input_type": input_type}).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return [d["embedding"] for d in json.loads(r.read())["data"]]


def main():
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        print("VOYAGE_API_KEY not set — skipping. Set it, then re-run to build the index.")
        return 0
    files = md_files()
    chunks = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        chunks.append({"id": str(p.relative_to(VAULT)), "title": p.stem,
                       "text": text[:4000]})
    vecs = []
    for i in range(0, len(chunks), BATCH):
        batch = [c["text"] for c in chunks[i:i + BATCH]]
        vecs.extend(embed(batch, key, "document"))
    for c, v in zip(chunks, vecs):
        c["embedding"] = v
        c.pop("text")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"model": MODEL, "items": chunks}), encoding="utf-8")
    print(f"Embedded {len(chunks)} notes → {OUT.relative_to(VAULT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
