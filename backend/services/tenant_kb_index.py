"""Index approved tenant documents into retrievable chunks.

Called after compile_tenant_kb. Fail-open: compile never fails because
indexing failed. If tenant_kb_chunks is missing (migration not applied),
request-time retrieval still chunks documents in memory.
"""

import asyncio
import hashlib
import logging
import re
from typing import Any

from backend.services.business_retrieval import CorpusChunk

_CHUNK_MIN = 500
_CHUNK_MAX = 1000
_CHUNK_OVERLAP = 120
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def pack_text(text: str) -> list[str]:
    """Pack a document into ~500-1000 character windows with overlap.

    A document shorter than the max stays one chunk. Tiny heading bodies are
    merged instead of stored as their own 30-character rows.
    """
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    if len(text) <= _CHUNK_MAX:
        return [text]

    pieces = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks: list[str] = []
    buf = ""

    def _hard_split(block: str) -> None:
        start = 0
        while start < len(block):
            end = min(len(block), start + _CHUNK_MAX)
            piece = block[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(block):
                break
            start = max(end - _CHUNK_OVERLAP, start + 1)

    for piece in pieces:
        if len(piece) > _CHUNK_MAX:
            if buf:
                chunks.append(buf)
                buf = ""
            _hard_split(piece)
            continue
        candidate = f"{buf} {piece}".strip() if buf else piece
        if len(candidate) <= _CHUNK_MAX:
            buf = candidate
            continue
        chunks.append(buf)
        tail = buf[-_CHUNK_OVERLAP:].strip()
        room = _CHUNK_MAX - len(piece) - 1
        if room > 0 and tail:
            buf = f"{tail[-room:]} {piece}".strip()
        else:
            buf = piece
    if buf:
        chunks.append(buf)
    if (
        len(chunks) >= 2
        and len(chunks[-1]) < _CHUNK_MIN
        and len(chunks[-2]) + 1 + len(chunks[-1]) <= _CHUNK_MAX
    ):
        chunks[-2] = f"{chunks[-2]} {chunks[-1]}".strip()
        chunks.pop()
    return [c for c in chunks if c]

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
        for idx, content in enumerate(pack_text(body)):
            out.append(
                CorpusChunk(
                    chunk_id=f"{doc_id}#{idx}",
                    document_id=doc_id,
                    account_id=client_id,
                    title=title,
                    section="",
                    content=content,
                    source_type=source,
                    citation_label=f"{title} §{idx}",
                    status="active",
                )
            )
    return out


def faq_rows_to_chunks(client_id: str, faqs: list[dict[str, Any]]) -> list[CorpusChunk]:
    """In-memory chunks for FAQ rows that are not yet a KB document.

    document_id is intentionally not a UUID so replace_chunks_for_tenant
    does not try to insert them against tenant_kb_documents (FK). Compile
    persists FAQs by syncing a real document first.
    """
    out: list[CorpusChunk] = []
    for i, faq in enumerate(faqs):
        if faq.get("is_active") is False:
            continue
        question = (faq.get("question") or "").strip()
        answer = (faq.get("answer") or "").strip()
        if not question or not answer:
            continue
        out.append(
            CorpusChunk(
                chunk_id=f"faq-{i}",
                document_id=f"faq-{i}",
                account_id=client_id,
                title=question[:160],
                section="faq",
                content=f"{question}\n{answer}",
                source_type="faqs",
                citation_label=f"FAQ: {question[:80]}",
                status="active",
            )
        )
    return out


def _load_faq_chunks(db: Any, client_id: str) -> list[CorpusChunk]:
    try:
        result = (
            db.table("faq_entries")
            .select("question, answer, is_active")
            .eq("tenant_id", client_id)
            .execute()
        )
        return faq_rows_to_chunks(client_id, result.data or [])
    except Exception:
        logger.warning("tenant_kb_index: faq load failed client_id=%s", client_id, exc_info=True)
        return []


def load_corpus_from_documents(db: Any, client_id: str) -> list[CorpusChunk]:
    """Request-time fallback: chunk active tenant_kb_documents in memory.

    FAQ entries are included. When compile has already projected them into
    a source='faq' document they ride along with the documents; otherwise
    they are appended from faq_entries so retrieval still sees them.
    """
    try:
        result = (
            db.table("tenant_kb_documents")
            .select("id, filename, content_md, source, status")
            .eq("client_id", client_id)
            .eq("status", "active")
            .execute()
        )
        docs = result.data or []
    except Exception:
        logger.warning("tenant_kb_index: document load failed client_id=%s", client_id, exc_info=True)
        return _load_faq_chunks(db, client_id)

    chunks = documents_to_chunks(client_id, docs)
    if any((doc.get("source") == "faq") for doc in docs):
        return chunks
    return chunks + _load_faq_chunks(db, client_id)


def replace_chunks_for_tenant(
    db: Any,
    client_id: str,
    chunks: list[CorpusChunk],
    embeddings: list[list[float] | None] | None = None,
) -> int:
    """Delete + insert tenant_kb_chunks. Fail-open if table missing."""
    try:
        db.table("tenant_kb_chunks").delete().eq("client_id", client_id).execute()
        if not chunks:
            return 0
        rows = []
        for i, c in enumerate(chunks):
            row = {
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
            if embeddings and i < len(embeddings) and embeddings[i]:
                row["embedding"] = embeddings[i]
            rows.append(row)
        # document_id is uuid in schema — skip persist when ids are eval strings
        persistable = [r for r in rows if r["document_id"]]
        for start in range(0, len(persistable), 40):
            db.table("tenant_kb_chunks").insert(persistable[start : start + 40]).execute()
        return len(persistable)
    except Exception:
        logger.warning("tenant_kb_index: persist skipped client_id=%s", client_id, exc_info=True)
        return 0


def _looks_uuid(value: str) -> bool:
    return len(value) == 36 and value.count("-") == 4


async def embed_chunk_texts(texts: list[str]) -> list[list[float]]:
    """Voyage embeddings for chunk bodies. Raises EmbeddingUnavailable if unset.

    ``embed_batch`` splits the list so each HTTP call stays under the token
    cap and waits for VOYAGE_RPM. Callers still embed every chunk before any
    existing rows are deleted.
    """
    from backend.services.embeddings import embed_batch

    if not texts:
        return []
    vectors = await embed_batch(texts)
    if len(vectors) != len(texts):
        raise RuntimeError("Voyage returned a different number of embeddings than chunks")
    return vectors


async def reindex_tenant(client_id: str) -> dict:
    """Rebuild one tenant's chunks and embeddings. Does not touch other tenants.

    Embeddings are computed before the old rows are deleted. A Voyage failure
    leaves the existing index in place.
    """
    if not _UUID.match(client_id or ""):
        raise ValueError("client_id must be a UUID")

    from backend.models.database import get_service_supabase
    from backend.services.embeddings import EmbeddingUnavailable

    db = get_service_supabase()
    chunks = load_corpus_from_documents(db, client_id)
    try:
        vectors = await embed_chunk_texts([c.content for c in chunks])
    except EmbeddingUnavailable:
        raise
    except Exception as exc:
        logger.warning("tenant_kb_index: reindex embed failed client_id=%s", client_id, exc_info=True)
        raise EmbeddingUnavailable("Voyage embeddings failed; existing chunks were kept") from exc

    written = replace_chunks_for_tenant(db, client_id, chunks, embeddings=vectors)
    return {
        "client_id": client_id,
        "chunks": written,
        "embedded": len(vectors),
        "with_embeddings": sum(1 for v in vectors if v),
    }


def index_after_compile(client_id: str) -> None:
    from backend.models.database import get_service_supabase

    try:
        db = get_service_supabase()
        chunks = load_corpus_from_documents(db, client_id)
        embeddings = None
        try:
            embeddings = asyncio.run(embed_chunk_texts([c.content for c in chunks]))
        except Exception:
            logger.warning(
                "tenant_kb_index: embeddings skipped client_id=%s", client_id, exc_info=True
            )
        replace_chunks_for_tenant(db, client_id, chunks, embeddings=embeddings)
    except Exception:
        logger.warning("tenant_kb_index: index_after_compile failed", exc_info=True)
