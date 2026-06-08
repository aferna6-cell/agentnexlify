"""Agent OS semantic memory — P0 (semantic layer only).

Durable facts/preferences/decisions stored as voyage-3-lite 512d embeddings.
Retrieval is cosine ANN via the match_os_memory SQL function. The Karpathy
graph layer (entity pages/edges) is deferred past P0 — it costs an LLM call
per write; the semantic layer costs one embedding per write.

Owner-only edit/delete is enforced at the router layer, not here.
"""

import logging
from datetime import datetime, timezone

from backend.services.embeddings import embed_query, embed_text
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

VALID_KINDS = {"fact", "preference", "decision", "conversation_summary", "outcome"}

# embedding is excluded — 512 floats never need to reach the client.
_PUBLIC_COLUMNS = (
    "id, kind, content, source, created_by, is_pinned, created_at, updated_at"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def write_memory(
    db,
    client_id: str,
    content: str,
    kind: str = "fact",
    source: str | None = None,
    created_by: str | None = None,
) -> dict:
    """Embed and store one memory entry. Stores without a vector if embedding fails."""
    kind = kind if kind in VALID_KINDS else "fact"
    embedding = None
    try:
        embedding = await embed_text(content)
    except Exception:
        logger.warning(
            "os_memory.write embed failed; storing without vector", exc_info=True
        )

    created = (
        tenant_table(db, "os_memory_entries", client_id)
        .insert(
            {
                "kind": kind,
                "content": content,
                "embedding": embedding,
                "source": source,
                "created_by": created_by,
            }
        )
        .execute()
    )
    return created.data[0]


async def search_memory(
    db, client_id: str, query: str, match_count: int = 8
) -> list[dict]:
    """Cosine-similarity retrieval scoped to one client. Returns [] on any failure."""
    try:
        query_embedding = await embed_query(query)
    except Exception:
        logger.warning(
            "os_memory.search query embed failed; returning []", exc_info=True
        )
        return []
    try:
        result = db.rpc(
            "match_os_memory",
            {
                "p_client_id": client_id,
                "p_query_embedding": query_embedding,
                "p_match_count": match_count,
            },
        ).execute()
        return result.data or []
    except Exception:
        logger.warning("os_memory.search match_os_memory rpc failed", exc_info=True)
        return []


def list_memory(db, client_id: str) -> list[dict]:
    result = (
        tenant_select(db, "os_memory_entries", client_id, _PUBLIC_COLUMNS)
        .order("is_pinned", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


async def update_memory(
    db,
    client_id: str,
    memory_id: str,
    content: str | None = None,
    kind: str | None = None,
    is_pinned: bool | None = None,
) -> dict | None:
    patch: dict = {}
    if content is not None:
        patch["content"] = content
        try:
            patch["embedding"] = await embed_text(content)
        except Exception:
            logger.warning("os_memory.update re-embed failed", exc_info=True)
    if kind is not None and kind in VALID_KINDS:
        patch["kind"] = kind
    if is_pinned is not None:
        patch["is_pinned"] = is_pinned
    if not patch:
        return None
    patch["updated_at"] = _now()
    updated = (
        tenant_table(db, "os_memory_entries", client_id)
        .update(patch)
        .eq("id", memory_id)
        .execute()
    )
    return updated.data[0] if updated.data else None


def delete_memory(db, client_id: str, memory_id: str) -> bool:
    result = (
        tenant_table(db, "os_memory_entries", client_id)
        .delete()
        .eq("id", memory_id)
        .execute()
    )
    return bool(result.data)
