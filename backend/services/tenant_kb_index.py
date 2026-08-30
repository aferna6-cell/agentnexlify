"""Index approved tenant documents into retrievable chunks.

Called after compile_tenant_kb. Fail-open: compile never fails because
indexing failed. If tenant_kb_chunks is missing (migration not applied),
request-time retrieval still chunks documents in memory.
"""

import hashlib
import logging
from typing import Any

import re

from backend.services.business_retrieval import CorpusChunk

_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.M)


def _chunk_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return [(i, "", p) for i, p in enumerate(parts)] or [(0, "", text.strip())]
    out: list[tuple[int, str, str]] = []
    idx = 0
    for n, m in enumerate(matches):
        start = m.end()
        end = matches[n + 1].start() if n + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        out.append((idx, m.group(2).strip(), body))
        idx += 1
    return out or [(0, "", text.strip())]

logger = logging.getLogger(__name__)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def documents_to_chunks(client_id: str, docs: list[dict[str, Any]]) -> list[CorpusChunk]:
    out: list[CorpusChunk] = []
    for doc in docs:
        if (doc.get("status") or "active") != "active":
            continue
        doc_id = str(doc.get("id") or doc.get("external_id") or doc.get("filename"))
        title = doc.get("filename") or doc.get("title") or "document"
        body = (doc.get("content_md") or doc.get("content") or "").strip()
        if not body:
            continue
        source = doc.get("source") or "upload"
        for idx, section, content in _chunk_sections(body):
            out.append(
                CorpusChunk(
                    chunk_id=f"{doc_id}#{idx}",
                    document_id=doc_id,
                    account_id=client_id,
                    title=title,
                    section=section,
                    content=content,
                    source_type=source,
                    citation_label=f"{title} §{section or idx}",
                    status="active",
                )
            )
    return out


def load_corpus_from_documents(db: Any, client_id: str) -> list[CorpusChunk]:
    """Request-time fallback: chunk active tenant_kb_documents in memory."""
    try:
        result = (
            db.table("tenant_kb_documents")
            .select("id, filename, content_md, source, status")
            .eq("client_id", client_id)
            .eq("status", "active")
            .execute()
        )
        return documents_to_chunks(client_id, result.data or [])
    except Exception:
        logger.warning("tenant_kb_index: document load failed client_id=%s", client_id, exc_info=True)
        return []


def replace_chunks_for_tenant(db: Any, client_id: str, chunks: list[CorpusChunk]) -> int:
    """Delete + insert tenant_kb_chunks. Fail-open if table missing."""
    try:
        db.table("tenant_kb_chunks").delete().eq("client_id", client_id).execute()
        if not chunks:
            return 0
        rows = []
        for c in chunks:
            rows.append(
                {
                    "client_id": client_id,
                    "document_id": c.document_id if _looks_uuid(c.document_id) else None,
                    "chunk_index": int(c.chunk_id.rsplit("#", 1)[-1] or 0),
                    "source_type": c.source_type,
                    "title": c.title,
                    "section": c.section,
                    "content": c.content,
                    "content_sha256": _sha(c.content),
                    "status": "active",
                    "citation_label": c.citation_label,
                }
            )
        # document_id is uuid in schema — skip persist when ids are eval strings
        persistable = [r for r in rows if r["document_id"]]
        if persistable:
            db.table("tenant_kb_chunks").insert(persistable).execute()
        return len(persistable)
    except Exception:
        logger.warning("tenant_kb_index: persist skipped client_id=%s", client_id, exc_info=True)
        return 0


def _looks_uuid(value: str) -> bool:
    return len(value) == 36 and value.count("-") == 4


def index_after_compile(client_id: str) -> None:
    from backend.database import get_service_supabase

    try:
        db = get_service_supabase()
        chunks = load_corpus_from_documents(db, client_id)
        replace_chunks_for_tenant(db, client_id, chunks)
    except Exception:
        logger.warning("tenant_kb_index: index_after_compile failed", exc_info=True)
