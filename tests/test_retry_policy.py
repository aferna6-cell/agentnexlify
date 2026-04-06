"""Tests for selective retry adoption in non-latency-critical AI paths."""

import os
os.environ["TESTING"] = "1"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("backend.services.llm_runtime.call_claude_messages", new_callable=AsyncMock)
async def test_generate_ai_email_uses_single_retry(mock_call):
    from backend.services.automation_engine import _generate_ai_email

    mock_call.return_value = MagicMock(text="Hello there")
    db = MagicMock()
    faq_table = MagicMock(); faq_table.select.return_value = faq_table; faq_table.eq.return_value = faq_table; faq_table.execute.return_value = MagicMock(data=[])
    conv_table = MagicMock(); conv_table.select.return_value = conv_table; conv_table.eq.return_value = conv_table; conv_table.order.return_value = conv_table; conv_table.limit.return_value = conv_table; conv_table.execute.return_value = MagicMock(data=[])
    leads_table = MagicMock(); leads_table.select.return_value = leads_table; leads_table.eq.return_value = leads_table; leads_table.limit.return_value = leads_table; leads_table.execute.return_value = MagicMock(data=[{"name": "Aidan"}])

    def table(name):
        if name == "faq_entries": return faq_table
        if name == "chat_messages": return conv_table
        if name == "leads": return leads_table
        raise AssertionError(name)
    db.table.side_effect = table

    body = await _generate_ai_email(db, "tenant-1", "lead-1", "Test Biz", None)

    assert body == "Hello there"
    assert mock_call.await_args.kwargs["max_retries"] == 1


@pytest.mark.asyncio
@patch("backend.routers.local_seo.call_claude_messages", new_callable=AsyncMock)
async def test_run_geo_score_ai_uses_single_retry(mock_call):
    from backend.routers.local_seo import _run_geo_score_ai

    mock_call.return_value = MagicMock(text='{"overall_score": 42, "platform_scores": {}, "visibility_factors": [], "recommendations": []}')
    result = await _run_geo_score_ai("Test Biz", "plumbing", "Miami", "https://example.com")

    assert result["overall_score"] == 42
    assert mock_call.await_args.kwargs["max_retries"] == 1


def test_content_repurposer_sync_path_uses_single_retry():
    from backend.services.content_repurposer import repurpose

    with patch("backend.services.content_repurposer.call_claude_messages_sync") as mock_call:
        mock_call.return_value = MagicMock(text='{"x_thread": []}')

        import asyncio
        result = asyncio.run(repurpose("source", "title", "tenant-1", formats=["x_thread"]))

        assert result == {"x_thread": []}
        assert mock_call.call_args.kwargs["max_retries"] == 1
