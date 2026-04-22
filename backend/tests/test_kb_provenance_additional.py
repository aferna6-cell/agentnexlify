import asyncio
from datetime import datetime
from unittest.mock import patch

import backend.routers.widget_chat_helpers as helpers
from backend.routers.widget_chat_helpers import _build_system_prompt, _query_kb_articles


def _make_tenant():
    return {"business_name": "Acme", "business_type": "general", "city": ""}


def _async_returning(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


def test_naive_datetime_last_validated_assumes_utc():
    article = {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "slug": "test-article",
        "title": "Test Article",
        "summary": "A test summary for the article.",
        "source_url": "https://example.com/article",
        "last_validated": datetime(2026, 4, 1),
        "citation_count": 0,
        "similarity": 0.85,
    }

    prompt = _build_system_prompt(_make_tenant(), [], kb_article_refs=[article])

    assert "last verified 2026-04-01" in prompt


def test_rpc_failure_returns_empty(mock_supabase):
    mock_supabase.rpc.return_value.execute.side_effect = RuntimeError("DB down")
    fake_vec = [0.1] * 512

    async def run():
        with patch.object(helpers, "embed_query", new=_async_returning(fake_vec)):
            with patch.object(helpers, "get_service_supabase", return_value=mock_supabase):
                return await _query_kb_articles("test")

    result = asyncio.run(run())
    assert result == []
