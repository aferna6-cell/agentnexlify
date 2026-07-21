"""Tests for _query_kb_articles FTS fallback in widget_chat_helpers.

Covers:
- Missing VOYAGE_API_KEY -> EmbeddingUnavailable -> FTS RPC called, results returned.
- Present VOYAGE_API_KEY -> semantic RPC called first, results returned (no FTS call).
- Both paths return the same dict shape (id, slug, title, summary, similarity).
- Any error in both paths returns [] without raising.

NO live DB or Voyage AI calls are made.  All external calls are mocked.

Run with:
    .venv/bin/python -m pytest backend/tests/test_kb_fts_fallback.py --noconftest -v
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure the project root is importable without a conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("TESTING", "1")
# Provide minimal env stubs so backend.config can be imported without crashing
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-anthropic-key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine in a fresh event loop (avoids pytest-asyncio dependency)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _fake_article(n: int = 1) -> dict:
    """Build a KB article dict matching the RPC return shape."""
    return {
        "id": f"00000000-0000-0000-0000-{n:012d}",
        "slug": f"article-{n}",
        "title": f"Test Article {n}",
        "summary": f"Summary of article {n}",
        "source_url": None,
        "last_validated": None,
        "citation_count": 0,
        "similarity": 0.85 / n,
    }


def _fake_rpc_chain(rows: list) -> MagicMock:
    """Build a Supabase RPC return-chain mock: rpc(...).execute() -> result."""
    result = MagicMock()
    result.data = rows
    chain = MagicMock()
    chain.execute.return_value = result
    return chain


# ---------------------------------------------------------------------------
# embed_query is imported locally inside _query_kb_articles, so we patch it
# at its definition site: backend.services.embeddings.embed_query.
# get_service_supabase is imported at module top in widget_chat_helpers, so
# we patch it at the reference site:
# backend.routers.widget_chat_helpers.get_service_supabase.
# ---------------------------------------------------------------------------

PATCH_DB = "backend.routers.widget_chat_helpers.get_service_supabase"
PATCH_EMBED = "backend.services.embeddings.embed_query"


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestQueryKbArticles(unittest.TestCase):
    """Unit tests for _query_kb_articles without any live network or DB calls."""

    # ------------------------------------------------------------------
    # 1. Missing VOYAGE_API_KEY -> FTS path
    # ------------------------------------------------------------------

    def test_missing_key_uses_fts_path(self):
        """EmbeddingUnavailable from embed_query should trigger the FTS fallback."""
        from backend.services.embeddings import EmbeddingUnavailable
        from backend.routers.widget_chat_helpers import _query_kb_articles

        fts_rows = [_fake_article(1), _fake_article(2)]

        mock_db = MagicMock()
        mock_db.rpc.return_value = _fake_rpc_chain(fts_rows)

        async def _raise_unavailable(_text):
            raise EmbeddingUnavailable("VOYAGE_API_KEY not configured")

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_raise_unavailable):
            result = _run(_query_kb_articles("plumbing services"))

        # FTS RPC must have been called. Since the kb-provenance change
        # (issue #70), retrieval also fires a fire-and-forget
        # increment_kb_citations RPC — filter to the retrieval call.
        retrieval_calls = [
            c for c in mock_db.rpc.call_args_list
            if c[0][0] == "match_kb_articles_fts"
        ]
        self.assertEqual(len(retrieval_calls), 1)
        self.assertEqual(
            retrieval_calls[0][0][1],
            {"query_text": "plumbing services", "match_count": 5},
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["slug"], "article-1")

    # ------------------------------------------------------------------
    # 2. Present VOYAGE_API_KEY -> semantic path
    # ------------------------------------------------------------------

    def test_present_key_uses_semantic_path(self):
        """When embed_query succeeds and the semantic RPC returns rows, use semantic."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        semantic_rows = [_fake_article(1)]
        mock_db = MagicMock()
        mock_db.rpc.return_value = _fake_rpc_chain(semantic_rows)

        fake_embedding = [0.1] * 512

        async def _fake_embed_query(_text):
            return fake_embedding

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_fake_embed_query):
            result = _run(_query_kb_articles("plumbing services"))

        # Semantic RPC must have been called with the embedding (a second
        # increment_kb_citations RPC is expected since issue #70 — filter).
        semantic_calls = [
            c for c in mock_db.rpc.call_args_list
            if c[0][0] == "match_kb_articles"
        ]
        self.assertEqual(len(semantic_calls), 1)
        rpc_params = semantic_calls[0][0][1]
        self.assertIn("query_embedding", rpc_params)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slug"], "article-1")

    # ------------------------------------------------------------------
    # 3. Same dict shape from both paths
    # ------------------------------------------------------------------

    def test_fts_returns_same_shape_as_semantic(self):
        """FTS result dict shape matches the semantic result shape."""
        from backend.services.embeddings import EmbeddingUnavailable
        from backend.routers.widget_chat_helpers import _query_kb_articles

        fts_row = _fake_article(1)
        mock_db = MagicMock()
        mock_db.rpc.return_value = _fake_rpc_chain([fts_row])

        async def _raise_unavailable(_text):
            raise EmbeddingUnavailable("no key")

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_raise_unavailable):
            result = _run(_query_kb_articles("test query"))

        self.assertEqual(len(result), 1)
        row = result[0]
        # Required keys that must exist in both paths
        for key in ("id", "slug", "title", "summary", "similarity"):
            self.assertIn(key, row, f"key '{key}' missing from FTS result")

    def test_semantic_returns_expected_shape(self):
        """Semantic result dict shape includes required keys."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        semantic_row = _fake_article(1)
        mock_db = MagicMock()
        mock_db.rpc.return_value = _fake_rpc_chain([semantic_row])

        async def _fake_embed_query(_text):
            return [0.0] * 512

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_fake_embed_query):
            result = _run(_query_kb_articles("test query"))

        row = result[0]
        for key in ("id", "slug", "title", "summary", "similarity"):
            self.assertIn(key, row, f"key '{key}' missing from semantic result")

    # ------------------------------------------------------------------
    # 4. Errors -> [] (non-blocking)
    # ------------------------------------------------------------------

    def test_both_paths_fail_returns_empty_list(self):
        """If both semantic and FTS paths raise, return [] without re-raising."""
        from backend.services.embeddings import EmbeddingUnavailable
        from backend.routers.widget_chat_helpers import _query_kb_articles

        mock_db = MagicMock()
        fts_chain = MagicMock()
        fts_chain.execute.side_effect = RuntimeError("DB unreachable")
        mock_db.rpc.return_value = fts_chain

        async def _raise_unavailable(_text):
            raise EmbeddingUnavailable("no key")

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_raise_unavailable):
            result = _run(_query_kb_articles("test query"))

        self.assertEqual(result, [])

    def test_semantic_error_falls_back_to_fts(self):
        """Non-EmbeddingUnavailable error in semantic path still falls back to FTS."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        fts_rows = [_fake_article(3)]
        fts_rpc_chain = _fake_rpc_chain(fts_rows)

        semantic_fail_chain = MagicMock()
        semantic_fail_chain.execute.side_effect = ConnectionError("timeout")

        def _rpc_dispatch(rpc_name, params):
            if rpc_name == "match_kb_articles":
                return semantic_fail_chain
            return fts_rpc_chain

        mock_db = MagicMock()
        mock_db.rpc.side_effect = _rpc_dispatch

        async def _fake_embed_query(_text):
            return [0.5] * 512

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_fake_embed_query):
            result = _run(_query_kb_articles("heating repair"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slug"], "article-3")

    def test_empty_query_returns_empty_list(self):
        """Empty query string must return [] without making any RPC call."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        mock_db = MagicMock()

        with patch(PATCH_DB, return_value=mock_db):
            result = _run(_query_kb_articles(""))

        mock_db.rpc.assert_not_called()
        self.assertEqual(result, [])

    def test_whitespace_query_returns_empty_list(self):
        """Whitespace-only query must return [] without any RPC call."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        mock_db = MagicMock()

        with patch(PATCH_DB, return_value=mock_db):
            result = _run(_query_kb_articles("   "))

        mock_db.rpc.assert_not_called()
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # 5. Semantic returns empty -> FTS fallback
    # ------------------------------------------------------------------

    def test_semantic_empty_falls_back_to_fts(self):
        """Semantic RPC returning 0 rows must trigger the FTS fallback."""
        from backend.routers.widget_chat_helpers import _query_kb_articles

        fts_rows = [_fake_article(7)]
        fts_rpc_chain = _fake_rpc_chain(fts_rows)
        semantic_rpc_chain = _fake_rpc_chain([])  # 0 rows from semantic

        def _rpc_dispatch(rpc_name, params):
            if rpc_name == "match_kb_articles":
                return semantic_rpc_chain
            return fts_rpc_chain

        mock_db = MagicMock()
        mock_db.rpc.side_effect = _rpc_dispatch

        async def _fake_embed_query(_text):
            return [0.2] * 512

        with patch(PATCH_DB, return_value=mock_db), \
             patch(PATCH_EMBED, side_effect=_fake_embed_query):
            result = _run(_query_kb_articles("drain cleaning"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slug"], "article-7")


if __name__ == "__main__":
    unittest.main(verbosity=2)
