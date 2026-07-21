"""Conversation memory tier for widget chat (issue #69).

Long widget conversations currently send the last N messages every turn — a
lost-in-the-middle problem and unbounded context growth. This module adds a
MemGPT-style tier: keep a short recent window verbatim, and pull the most
relevant OLDER messages by a hybrid score instead of dumping the whole history.

  hybrid_score = 0.4 * cosine + 0.3 * recency + 0.3 * confidence

SCHEMA (contract §7 — applied schema wins over the issue text):
  Scores live on `chat_messages` (the canonical store — `conversations.messages`
  was dropped), keyed by `session_id` (TEXT), scoped by `tenant_id`. See
  migration 182. The issue's `conversations.messages` / `conversation_id` /
  `client_id` wording is corrected here.

Everything is fail-open and the widget wiring is opt-in
(`widget_conversation_memory_tier_enabled`, default 0) — with the flag off,
widget chat behaviour is unchanged.
"""

import logging
import math
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Hybrid-score weights (issue #69).
W_COSINE = 0.4
W_RECENCY = 0.3
W_CONFIDENCE = 0.3

# Messages at or below this confidence are excluded from retrieval (matches the
# migration-182 partial index predicate).
CONFIDENCE_FLOOR = 0.3

# Defaults for the tier.
DEFAULT_RECENT_WINDOW = 10
DEFAULT_TOP_K = 5
DEFAULT_THRESHOLD = 20          # only engage the tier past this many messages
DEFAULT_CANDIDATE_CAP = 40      # cap embeds per turn (cost guard)

EmbedFn = Callable[[Sequence[str]], Awaitable[List[List[float]]]]
LoaderFn = Callable[[Any, str, str, int], List[Dict[str, Any]]]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def cosine_similarity(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> float:
    """Cosine similarity clamped to [0, 1]; 0 when either vector is missing/degenerate."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _clamp01(dot / (na * nb))


def hybrid_score(cosine: float, recency: float, confidence: float) -> float:
    """Weighted blend of relevance, recency, and confidence — all inputs clamped."""
    return (
        W_COSINE * _clamp01(cosine)
        + W_RECENCY * _clamp01(recency)
        + W_CONFIDENCE * _clamp01(confidence)
    )


def rank_messages(
    query_embedding: Optional[Sequence[float]],
    candidates: List[Dict[str, Any]],
    top_k: int = DEFAULT_TOP_K,
) -> List[Dict[str, Any]]:
    """Rank older-message candidates by hybrid score, filtering low confidence.

    ``candidates`` are dicts ordered oldest→newest, each with an optional
    ``embedding`` and a ``message_confidence``. Returns the top ``top_k`` dicts
    sorted by score descending, each annotated with ``memory_score``. Messages
    with confidence <= CONFIDENCE_FLOOR are dropped (mirrors the mig-182 index).
    """
    usable = [
        c for c in candidates
        if (c.get("message_confidence") if c.get("message_confidence") is not None else 0.8)
        > CONFIDENCE_FLOOR
    ]
    if not usable:
        return []
    n = len(usable)
    for position, cand in enumerate(usable):
        # Newer candidates (later in oldest→newest order) get higher recency.
        recency = (position + 1) / n if n > 1 else 1.0
        confidence = (
            cand.get("message_confidence")
            if cand.get("message_confidence") is not None
            else 0.8
        )
        cosine = cosine_similarity(query_embedding, cand.get("embedding"))
        cand["memory_score"] = hybrid_score(cosine, recency, confidence)
    return sorted(usable, key=lambda c: c["memory_score"], reverse=True)[:top_k]


def update_confidence(db, tenant_id: str, message_id: str, delta: float) -> Optional[float]:
    """Clamp-adjust a message's confidence in [0, 1]; tenant-scoped. Fail-open."""
    try:
        result = (
            db.table("chat_messages")
            .select("message_confidence")
            .eq("id", message_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        current = rows[0].get("message_confidence")
        if current is None:
            current = 0.8
        new_value = _clamp01(current + delta)
        (
            db.table("chat_messages")
            .update({"message_confidence": new_value})
            .eq("id", message_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return new_value
    except Exception:
        logger.warning(
            "conversation_memory: update_confidence failed (msg=%s)",
            message_id,
            exc_info=True,
        )
        return None


def _default_loader(db, tenant_id: str, session_id: str, limit: int) -> List[Dict[str, Any]]:
    """Load the most recent ``limit`` messages for a session, oldest→newest."""
    result = (
        db.table("chat_messages")
        .select("id, role, content, message_confidence, created_at")
        .eq("tenant_id", tenant_id)
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    rows.reverse()  # DB gave newest→oldest; the tier reasons oldest→newest
    return rows


async def _default_embed(texts: Sequence[str]) -> List[List[float]]:
    from backend.services.embeddings import embed_query

    return [await embed_query(text) for text in texts]


async def build_tiered_history(
    db,
    tenant_id: str,
    session_id: str,
    query: str,
    *,
    recent_window: int = DEFAULT_RECENT_WINDOW,
    top_k: int = DEFAULT_TOP_K,
    threshold: int = DEFAULT_THRESHOLD,
    candidate_cap: int = DEFAULT_CANDIDATE_CAP,
    loader: Optional[LoaderFn] = None,
    embed_fn: Optional[EmbedFn] = None,
) -> Optional[List[Dict[str, str]]]:
    """Return ``{role, content}`` history as recent window + top-k older, else None.

    Returns ``None`` (caller keeps its default history) when the conversation is
    at or below ``threshold`` messages, or on any failure — the widget path must
    never break because of the memory tier.
    """
    loader = loader or _default_loader
    embed_fn = embed_fn or _default_embed
    try:
        window = max(threshold + 1, recent_window + candidate_cap)
        messages = loader(db, tenant_id, session_id, window)
        if len(messages) <= threshold:
            return None

        recent = messages[-recent_window:] if recent_window > 0 else []
        older = messages[:-recent_window] if recent_window > 0 else list(messages)
        older = [
            m for m in older
            if (m.get("message_confidence") if m.get("message_confidence") is not None else 0.8)
            > CONFIDENCE_FLOOR
        ]
        if older:
            older = older[-candidate_cap:]  # cap embeds to the newest candidates
            embeddings = await embed_fn([query] + [m.get("content") or "" for m in older])
            query_embedding = embeddings[0] if embeddings else None
            for msg, emb in zip(older, embeddings[1:]):
                msg["embedding"] = emb
            ranked = rank_messages(query_embedding, older, top_k=top_k)
        else:
            ranked = []

        # Present the selected older messages in chronological order, then recent.
        order = {id(m): i for i, m in enumerate(messages)}
        ranked_chrono = sorted(ranked, key=lambda m: order.get(id(m), 0))
        selected = ranked_chrono + recent
        return [
            {"role": m.get("role") or "user", "content": m.get("content") or ""}
            for m in selected
        ]
    except Exception:
        logger.warning(
            "conversation_memory: build_tiered_history failed (session=%s) — "
            "caller keeps default history",
            session_id,
            exc_info=True,
        )
        return None
