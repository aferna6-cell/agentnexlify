"""Hybrid keyword+vector KB retrieval — optional additive merge (#F12).

`_query_kb_articles` in `backend/routers/widget_chat_helpers.py` already has
two RETRIEVAL paths that run one-at-a-time: semantic search
(`match_kb_articles` RPC, pgvector cosine) as primary, Postgres full-text
search (`match_kb_articles_fts` RPC, migration 155) as a FALLBACK only when
semantic is unavailable or empty. This module adds an opt-in HYBRID mode
that runs the FTS pass ALONGSIDE whichever rows the base retrieval already
returned and merges the two result sets, so an exact keyword match the
embedding missed can still surface even when semantic search returned
*something* (just not the best something).

No new migration is required: `content_tsv` (generated tsvector column),
its GIN index, and the `match_kb_articles_fts` RPC all already exist
(migration 155/163 — kb_articles FTS support). This module only calls that
existing RPC a second time; it does not create anything new. If a future
change needs additional hybrid signals (e.g. a dedicated hybrid RPC that
blends scores in SQL), that would be a new migration — not needed today.

FAIL-OPEN by design (mirrors `kb_reranker.py` / `widget_guard.py`): any
error in the FTS pass returns the caller's `semantic_rows` unchanged. A
broken hybrid merge must never break KB grounding on the widget chat path.

Opt-in only — this module has no side effect unless
`hybrid_merge_kb_articles()` is called. The caller (`_query_kb_articles`)
gates the call behind the `widget_kb_hybrid_enabled` setting (default off).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_KB_FTS_RPC = "match_kb_articles_fts"


async def hybrid_merge_kb_articles(
    db: Any,
    query: str,
    semantic_rows: list[dict[str, Any]],
    match_count: int = 5,
) -> list[dict[str, Any]]:
    """Merge *semantic_rows* (already fetched by the caller) with an FTS pass.

    `db` is a Supabase client (same shape as `get_service_supabase()` — a
    plain object exposing `.rpc(name, params).execute()`), passed in by the
    caller rather than fetched here so this function stays trivially
    testable and has no import-time dependency on the DB module.

    Dedupes by `id`, keeping the semantic ordering first (already the
    higher-signal path when embeddings are available) then appending any
    FTS-only matches not already present, truncated to `match_count`.

    On any error (RPC failure, malformed rows), or if `query`/
    `semantic_rows` is empty, returns `semantic_rows` unchanged — never
    raises.
    """
    if not semantic_rows:
        return semantic_rows
    if not query or not query.strip():
        return semantic_rows

    try:
        result = db.rpc(
            _KB_FTS_RPC,
            {"query_text": query.strip(), "match_count": match_count},
        ).execute()
        fts_rows = result.data or []
    except Exception:
        logger.warning(
            "kb_hybrid: FTS pass failed for query=%r — returning semantic-only rows",
            query[:60],
            exc_info=True,
        )
        return semantic_rows

    if not fts_rows:
        return semantic_rows

    seen_ids = {row.get("id") for row in semantic_rows if row.get("id") is not None}
    merged: list[dict[str, Any]] = list(semantic_rows)
    for row in fts_rows:
        row_id = row.get("id")
        if row_id is not None and row_id in seen_ids:
            continue
        merged.append(row)
        if row_id is not None:
            seen_ids.add(row_id)

    return merged[:match_count]
