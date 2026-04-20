"""Tests for KB article provenance — issue #70.

Unit test: retrieval increments citation_count
Integration test: stale article triggers warning in prompt
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Unit: _increment_kb_citation_counts
# ---------------------------------------------------------------------------


class TestIncrementKbCitationCounts:
    def test_calls_rpc_with_article_ids(self, mock_supabase):
        from backend.routers.widget_chat_helpers import _increment_kb_citation_counts

        article_ids = [
            "aaaaaaaa-0000-0000-0000-000000000001",
            "aaaaaaaa-0000-0000-0000-000000000002",
        ]
        result = _increment_kb_citation_counts(article_ids)

        # Returns None (fire-and-forget)
        assert result is None
        # RPC called with correct payload
        call_kwargs = mock_supabase.rpc.call_args
        assert call_kwargs[0][0] == "increment_kb_citations"
        assert call_kwargs[0][1]["article_ids"] == article_ids

    def test_empty_list_skips_rpc(self, mock_supabase):
        from backend.routers.widget_chat_helpers import _increment_kb_citation_counts

        result = _increment_kb_citation_counts([])

        # Returns without making any DB call
        assert result is None
        assert mock_supabase.rpc.call_count == 0

    def test_rpc_failure_does_not_raise(self, mock_supabase):
        from backend.routers.widget_chat_helpers import _increment_kb_citation_counts

        mock_supabase.rpc.return_value.execute.side_effect = RuntimeError("DB down")

        # Must not propagate — it is fire-and-forget
        _increment_kb_citation_counts(["aaaaaaaa-0000-0000-0000-000000000001"])


# ---------------------------------------------------------------------------
# Integration: stale warning appears in system prompt
# ---------------------------------------------------------------------------


def _make_article(*, days_old: int, source_url: str = "https://example.com/article") -> dict:
    validated_dt = datetime.now(timezone.utc) - timedelta(days=days_old)
    return {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "slug": "test-article",
        "title": "Test Article",
        "summary": "A test summary for the article.",
        "source_url": source_url,
        "last_validated": validated_dt.isoformat(),
        "citation_count": 0,
        "similarity": 0.85,
    }


class TestBuildSystemPromptWithKbArticles:
    """_build_system_prompt with kb_article_refs parameter."""

    def _make_tenant(self):
        return {"business_name": "Acme", "business_type": "general", "city": ""}

    def test_fresh_article_no_stale_warning(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        refs = [_make_article(days_old=10)]
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=refs)

        assert "Test Article" in prompt
        assert "Source: https://example.com/article" in prompt
        assert "⚠ KB article may be outdated" not in prompt

    def test_stale_article_shows_warning(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        refs = [_make_article(days_old=65)]
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=refs)

        assert "Test Article" in prompt
        assert "⚠ KB article may be outdated" in prompt

    def test_source_url_and_date_in_footer(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        refs = [_make_article(days_old=5, source_url="https://example.com/source")]
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=refs)

        assert "Source: https://example.com/source" in prompt
        assert "last verified" in prompt

    def test_no_kb_articles_no_block(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=None)

        assert "KB_ARTICLES" not in prompt

    def test_article_without_source_url_omits_source(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        article = _make_article(days_old=10, source_url="")
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=[article])

        assert "Test Article" in prompt
        assert "Source:" not in prompt

    def test_stale_boundary_exactly_60_days(self):
        """Article exactly at 60 days is NOT stale (threshold is strictly less-than)."""
        from backend.routers.widget_chat_helpers import _build_system_prompt

        refs = [_make_article(days_old=60)]
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=refs)

        assert "⚠ KB article may be outdated" not in prompt

    def test_stale_boundary_61_days(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        refs = [_make_article(days_old=61)]
        prompt = _build_system_prompt(self._make_tenant(), [], kb_article_refs=refs)

        assert "⚠ KB article may be outdated" in prompt


# ---------------------------------------------------------------------------
# Unit: _query_kb_articles — mocks embed_query + supabase rpc
# ---------------------------------------------------------------------------


class TestQueryKbArticles:
    def test_returns_rpc_data(self, mock_supabase):
        import backend.routers.widget_chat_helpers as helpers
        from backend.routers.widget_chat_helpers import _query_kb_articles

        fake_rows = [
            {
                "id": "aaaaaaaa-0000-0000-0000-000000000001",
                "slug": "test",
                "title": "Test",
                "summary": "Summary",
                "source_url": "https://example.com",
                "last_validated": "2026-04-01T00:00:00+00:00",
                "citation_count": 5,
                "similarity": 0.9,
            }
        ]
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=fake_rows)

        fake_vec = [0.1] * 512

        async def run():
            with patch.object(helpers, "embed_query", new=_async_returning(fake_vec)):
                with patch.object(helpers, "get_service_supabase", return_value=mock_supabase):
                    return await _query_kb_articles("What is Claude?")

        result = asyncio.run(run())
        assert result == fake_rows

    def test_embed_failure_returns_empty(self, mock_supabase):
        import backend.routers.widget_chat_helpers as helpers
        from backend.routers.widget_chat_helpers import _query_kb_articles

        async def run():
            with patch.object(helpers, "embed_query", new=_async_raising(RuntimeError("Voyage down"))):
                with patch.object(helpers, "get_service_supabase", return_value=mock_supabase):
                    return await _query_kb_articles("test")

        result = asyncio.run(run())
        assert result == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _async_returning(value):
    async def _fn(*args, **kwargs):
        return value
    return _fn


def _async_raising(exc):
    async def _fn(*args, **kwargs):
        raise exc
    return _fn
