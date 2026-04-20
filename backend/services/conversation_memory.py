"""Conversation memory tier for widget chat.

MemGPT-style retrieval: when a session exceeds 20 messages, older messages
are scored by a hybrid formula and the top-k are returned to the caller
instead of relying solely on recency compaction.

Hybrid score = 0.4 * cosine_similarity + 0.3 * recency + 0.3 * confidence

Embeddings are lazy: computed on first retrieval and stored in chat_messages
for reuse. No embedding at write time.

Public API:
    retrieve_relevant(session_id, tenant_id, query_embedding, top_k=5)
    update_confidence(message_id, delta)

WARNING: No 'from __future__ import annotations' — FastAPI files in this
project cannot use PEP 563 deferred annotations.
"""

import logging
import math
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.embeddings import embed_text

logger = logging.getLogger(__name__)

MEMORY_THRESHOLD = 20   # activate memory tier when session has > this many messages
RECENT_WINDOW = 10      # always pass the last N messages verbatim to Claude
TOP_K_DEFAULT = 5       # max older messages to retrieve via hybrid scoring
CONFIDENCE_FLOOR = 0.3  # messages at or below this confidence are excluded


def _cosine_similarity(a: list, b: list) -> float:
    """Cosine similarity between two equal-length vectors. Returns 0.0 on bad input."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (mag_a * mag_b)))


async def retrieve_relevant(
    session_id: str,
    tenant_id: str,
    query_embedding: list,
    top_k: int = TOP_K_DEFAULT,
) -> list:
    """Return top-k older messages ranked by hybrid relevance score.

    The caller is responsible for passing the last RECENT_WINDOW messages
    verbatim — this function only returns candidates from the older portion
    of the session history.

    Args:
        session_id: Widget session identifier (used as conversation key).
        tenant_id: Tenant UUID — scopes all DB queries for RLS isolation.
        query_embedding: 512-dim Voyage AI embedding of the current user message.
        top_k: Maximum number of older messages to return (default 5).

    Returns:
        List of {role, content} dicts ordered best-score-first.
        Empty list if fewer than RECENT_WINDOW + 1 messages in history.
    """
    db = get_service_supabase()
    try:
        result = (
            db.table("chat_messages")
            .select("id, role, content, message_confidence, embedding, created_at")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .gt("message_confidence", CONFIDENCE_FLOOR)
            .order("created_at")
            .execute()
        )
    except Exception:
        logger.warning(
            "conversation_memory: DB fetch failed session=%s", session_id, exc_info=True
        )
        return []

    rows = result.data or []
    if len(rows) <= RECENT_WINDOW:
        return []

    # Older candidates: everything except the last RECENT_WINDOW messages
    older = rows[:-RECENT_WINDOW]
    if not older:
        return []

    def _parse_ts(ts_str: str) -> datetime:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    oldest_ts = _parse_ts(older[0]["created_at"])
    newest_ts = _parse_ts(older[-1]["created_at"])
    time_span_s = max(1.0, (newest_ts - oldest_ts).total_seconds())

    # Collect embeddings that need to be written back (lazy embed results)
    embed_writes: list = []
    scored: list = []

    for row in older:
        emb = row.get("embedding")
        if emb is None:
            try:
                emb = await embed_text(row["content"])
                embed_writes.append((row["id"], emb))
            except Exception:
                logger.warning(
                    "conversation_memory: embed failed for msg %s", row["id"]
                )

        cosine = _cosine_similarity(query_embedding, emb) if emb else 0.0

        msg_ts = _parse_ts(row["created_at"])
        recency = (msg_ts - oldest_ts).total_seconds() / time_span_s

        confidence = float(row.get("message_confidence") or 0.8)
        hybrid = 0.4 * cosine + 0.3 * recency + 0.3 * confidence

        scored.append((hybrid, row))

    # Flush new embeddings to DB (best-effort — never block the response)
    for msg_id, emb_vec in embed_writes:
        try:
            db.table("chat_messages").update({"embedding": emb_vec}).eq(
                "id", msg_id
            ).execute()
        except Exception:
            logger.debug("conversation_memory: embedding store failed for %s", msg_id)

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"role": r["role"], "content": r["content"]} for _, r in scored[:top_k]]


def update_confidence(message_id: str, delta: float) -> None:
    """Adjust message_confidence by delta, clamped to [0.0, 1.0].

    Args:
        message_id: UUID of the chat_messages row to update.
        delta: Signed float. Positive increases confidence, negative decreases.
    """
    db = get_service_supabase()
    try:
        result = (
            db.table("chat_messages")
            .select("message_confidence")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.warning("update_confidence: message %s not found", message_id)
            return
        current = float(result.data[0].get("message_confidence") or 0.8)
        new_val = max(0.0, min(1.0, current + delta))
        db.table("chat_messages").update({"message_confidence": new_val}).eq(
            "id", message_id
        ).execute()
    except Exception:
        logger.warning(
            "update_confidence: failed for %s delta=%s", message_id, delta, exc_info=True
        )
