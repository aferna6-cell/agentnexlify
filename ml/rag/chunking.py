"""Chunk strategies for Milestone 7. Measure; do not pick a magic number."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    section: str
    content: str


_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.M)


def chunk_paragraphs(text: str, min_chars: int = 40) -> list[Chunk]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[Chunk] = []
    for i, p in enumerate(parts):
        if len(p) < min_chars:
            continue
        out.append(Chunk(i, "", p))
    return out or [Chunk(0, "", text.strip())]


def chunk_fixed(text: str, window: int = 400, overlap: int = 80) -> list[Chunk]:
    body = re.sub(r"\s+", " ", text).strip()
    if not body:
        return []
    step = max(1, window - overlap)
    out: list[Chunk] = []
    i = 0
    idx = 0
    while i < len(body):
        piece = body[i : i + window].strip()
        if piece:
            out.append(Chunk(idx, "", piece))
            idx += 1
        i += step
    return out


def chunk_sections(text: str) -> list[Chunk]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return chunk_paragraphs(text)
    out: list[Chunk] = []
    idx = 0
    for n, m in enumerate(matches):
        start = m.end()
        end = matches[n + 1].start() if n + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        out.append(Chunk(idx, m.group(2).strip(), body))
        idx += 1
    return out or chunk_paragraphs(text)


STRATEGIES = {
    "paragraph": chunk_paragraphs,
    "fixed": chunk_fixed,
    "section": chunk_sections,
}
