"""Agent OS sync: kb — chunk the tenant's widget knowledge base into memory.

The widget's authoring surface (``widget_configs.knowledge_base`` +
``custom_instructions``) is one big markdown blob per tenant. To make it
retrievable in semantic memory we chunk it into ~1000-char segments and
embed each. Source ref pattern: ``kb:chunk:<index>``.

Change detection: there's no ``updated_at`` on ``widget_configs``, so we
hash the combined content and store that as ``last_seen_cursor``. If the
hash matches, the run no-ops. If it differs, we DELETE every prior
``kb:chunk:*`` row for the tenant and insert the fresh batch.

Note: ``widget_configs.tenant_id`` is the correct column. ``tenant_table``
handles the column-name shim; client_id == tenant_id in our schema.
"""

import hashlib
import logging
import re

from backend.services.embeddings import embed_batch
from backend.services.os_sync.base import SyncContext, SyncResult, SyncSpec, now_iso
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_CHUNK_TARGET_CHARS = 1000
_CHUNK_MAX_CHARS = 1400
_EMBED_BATCH_SIZE = 32


def _hash_content(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def _split_into_chunks(text: str) -> list[str]:
    """Greedy paragraph-aware chunker.

    Splits on blank lines first; if a single paragraph exceeds
    ``_CHUNK_MAX_CHARS`` we hard-split it on sentence boundaries, then on
    raw character windows as a last resort.
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            chunks.append("\n\n".join(buf).strip())
            buf = []
            buf_len = 0

    for para in paragraphs:
        if len(para) > _CHUNK_MAX_CHARS:
            flush()
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sb: list[str] = []
            sb_len = 0
            for s in sentences:
                if sb_len + len(s) + 1 > _CHUNK_TARGET_CHARS and sb:
                    chunks.append(" ".join(sb).strip())
                    sb, sb_len = [], 0
                if len(s) > _CHUNK_MAX_CHARS:
                    for i in range(0, len(s), _CHUNK_TARGET_CHARS):
                        chunks.append(s[i : i + _CHUNK_TARGET_CHARS].strip())
                    continue
                sb.append(s)
                sb_len += len(s) + 1
            if sb:
                chunks.append(" ".join(sb).strip())
            continue

        if buf_len + len(para) + 2 > _CHUNK_TARGET_CHARS and buf:
            flush()
        buf.append(para)
        buf_len += len(para) + 2

    flush()
    return [c for c in chunks if c]


def _load_widget_config(db, client_id: str) -> dict | None:
    rows = (
        tenant_table(db, "widget_configs", client_id)
        .select("knowledge_base, custom_instructions, bot_name")
        .limit(1)
        .execute()
    )
    if not rows.data:
        return None
    return rows.data[0]


def _delete_existing_chunks(db, client_id: str) -> None:
    tenant_table(db, "os_memory_entries", client_id).delete().like(
        "source_ref", "kb:chunk:%"
    ).execute()


async def _run(ctx: SyncContext) -> SyncResult:
    client_id = ctx.client_id
    db = ctx.db

    try:
        config = _load_widget_config(db, client_id)
    except Exception as e:
        logger.exception(
            "os_sync.kb: widget_configs lookup failed client_id=%s", client_id
        )
        return SyncResult(status="error", error_detail=str(e)[:300])

    if not config:
        return SyncResult(status="ok", rows_seen=0)

    knowledge_base = (config.get("knowledge_base") or "").strip()
    custom_instructions = (config.get("custom_instructions") or "").strip()
    bot_name = (config.get("bot_name") or "").strip()

    combined = "\n\n".join(p for p in (custom_instructions, knowledge_base) if p)
    if not combined:
        # KB cleared — drop any prior chunks so memory stays consistent
        if ctx.state_row.get("last_seen_cursor"):
            try:
                _delete_existing_chunks(db, client_id)
            except Exception:
                logger.exception(
                    "os_sync.kb: cleanup-on-empty failed client_id=%s", client_id
                )
        return SyncResult(status="ok", rows_seen=0, new_cursor="")

    new_hash = _hash_content(custom_instructions, knowledge_base)
    if not ctx.backfill and ctx.state_row.get("last_seen_cursor") == new_hash:
        return SyncResult(status="ok", rows_seen=0, new_cursor=new_hash)

    chunks = _split_into_chunks(combined)
    if not chunks:
        return SyncResult(status="ok", rows_seen=0, new_cursor=new_hash)

    embeddings: list[list[float] | None] = []
    for start in range(0, len(chunks), _EMBED_BATCH_SIZE):
        batch = chunks[start : start + _EMBED_BATCH_SIZE]
        try:
            vectors = await embed_batch(batch)
            embeddings.extend(vectors)
        except Exception:
            logger.warning(
                "os_sync.kb: embed_batch failed client_id=%s start=%d",
                client_id,
                start,
                exc_info=True,
            )
            embeddings.extend([None] * len(batch))

    try:
        _delete_existing_chunks(db, client_id)
    except Exception as e:
        logger.exception("os_sync.kb: chunk cleanup failed client_id=%s", client_id)
        return SyncResult(status="error", error_detail=str(e)[:300])

    label = bot_name or "widget"
    inserts: list[dict] = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        inserts.append(
            {
                "kind": "fact",
                "content": f"[{label} KB chunk {idx + 1}/{len(chunks)}]\n{chunk}",
                "embedding": embedding,
                "source": "sync:kb",
                "source_ref": f"kb:chunk:{idx}",
                "updated_at": now_iso(),
            }
        )

    try:
        tenant_table(db, "os_memory_entries", client_id).insert(inserts).execute()
    except Exception as e:
        logger.exception("os_sync.kb: insert failed client_id=%s", client_id)
        return SyncResult(status="error", error_detail=str(e)[:300])

    return SyncResult(status="ok", rows_seen=len(inserts), new_cursor=new_hash)


SPEC = SyncSpec(
    name="kb",
    run=_run,
    description=(
        "Chunk widget_configs.knowledge_base + custom_instructions into "
        "semantic memory; hash-cursored, rewrites on change."
    ),
    required_connectors=[],
)
