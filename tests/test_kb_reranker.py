"""KB retrieval upgrade (#F10 reranker + #F12 hybrid) — unit tests.

Contracts:
  - rerank_kb_articles reorders by the Haiku judge's `ranked_indices`, truncates
    to top_k, and is FAIL-OPEN: <2 articles, empty query, LLM error, unparseable
    / non-dict / missing-indices / no-valid-index responses all return the input
    order unchanged (a reranker failure is invisible to the widget reply).
  - hybrid_merge_kb_articles appends FTS-only matches to the semantic rows,
    dedupes by id, and is fail-open on empty input or RPC failure.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import backend.services.kb_reranker as kb_reranker
import backend.services.kb_hybrid_retrieval as kb_hybrid
from backend.services.kb_reranker import rerank_kb_articles
from backend.services.kb_hybrid_retrieval import hybrid_merge_kb_articles


def _arts(*ids):
    return [{"id": i, "title": f"t{i}", "content": f"body {i}"} for i in ids]


def _llm(text):
    r = MagicMock()
    r.text = text
    return r


# ---------------------------------------------------------------------------
# rerank_kb_articles
# ---------------------------------------------------------------------------


def test_rerank_reorders_by_ranked_indices():
    arts = _arts("a", "b", "c")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(return_value=_llm('{"ranked_indices": [2, 0, 1]}'))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=5))
    assert [a["id"] for a in out] == ["c", "a", "b"]


def test_rerank_truncates_to_top_k():
    arts = _arts("a", "b", "c", "d")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(return_value=_llm('{"ranked_indices": [3, 2, 1, 0]}'))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=2))
    assert [a["id"] for a in out] == ["d", "c"]


def test_rerank_skips_out_of_range_and_dupes():
    arts = _arts("a", "b")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(return_value=_llm('{"ranked_indices": [9, 1, 1, 0]}'))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=5))
    assert [a["id"] for a in out] == ["b", "a"]


def test_rerank_under_two_articles_no_llm_call():
    call = AsyncMock()
    with patch.object(kb_reranker, "call_claude_messages", new=call):
        out = asyncio.run(rerank_kb_articles("q", _arts("a"), top_k=5))
    assert [a["id"] for a in out] == ["a"]
    call.assert_not_awaited()


def test_rerank_empty_query_returns_unchanged():
    arts = _arts("a", "b")
    out = asyncio.run(rerank_kb_articles("   ", arts, top_k=5))
    assert out == arts


def test_rerank_llm_error_returns_original_order():
    arts = _arts("a", "b", "c")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(side_effect=RuntimeError("boom"))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=5))
    assert [a["id"] for a in out] == ["a", "b", "c"]


def test_rerank_unparseable_returns_original_order():
    arts = _arts("a", "b")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(return_value=_llm("not json"))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=5))
    assert out == arts


def test_rerank_missing_indices_returns_original_order():
    arts = _arts("a", "b")
    with patch.object(kb_reranker, "call_claude_messages",
                      new=AsyncMock(return_value=_llm('{"other": [0]}'))):
        out = asyncio.run(rerank_kb_articles("q", arts, top_k=5))
    assert out == arts


# ---------------------------------------------------------------------------
# hybrid_merge_kb_articles
# ---------------------------------------------------------------------------


def _db_with_fts(rows):
    db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=rows)
    db.rpc.return_value = chain
    return db


def test_hybrid_appends_fts_only_matches_deduped():
    semantic = _arts("a", "b")
    db = _db_with_fts([{"id": "b"}, {"id": "c"}])  # b is dupe, c is new
    out = asyncio.run(hybrid_merge_kb_articles(db, "q", semantic, match_count=5))
    ids = [a["id"] for a in out]
    assert ids[:2] == ["a", "b"]  # semantic order preserved first
    assert "c" in ids and ids.count("b") == 1  # deduped, FTS-only appended


def test_hybrid_truncates_to_match_count():
    semantic = _arts("a", "b")
    db = _db_with_fts([{"id": "c"}, {"id": "d"}])
    out = asyncio.run(hybrid_merge_kb_articles(db, "q", semantic, match_count=3))
    assert len(out) == 3


def test_hybrid_empty_semantic_returns_unchanged():
    db = _db_with_fts([{"id": "c"}])
    out = asyncio.run(hybrid_merge_kb_articles(db, "q", [], match_count=5))
    assert out == []


def test_hybrid_rpc_error_returns_semantic_rows():
    semantic = _arts("a", "b")
    db = MagicMock()
    db.rpc.side_effect = RuntimeError("rpc down")
    out = asyncio.run(hybrid_merge_kb_articles(db, "q", semantic, match_count=5))
    assert out == semantic
