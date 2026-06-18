"""Tests for the content repurposer service."""

import os

os.environ["TESTING"] = "1"

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.content_repurposer import (
    connect_outputs,
    extract_source,
    repurpose,
)


# ---------- extract_source ----------


@pytest.mark.asyncio
async def test_extract_source_text():
    """Plain text source returns content as-is with word count."""
    result = await extract_source("text", "Hello world this is a test")
    assert result["content"] == "Hello world this is a test"
    assert result["word_count"] == 6
    assert result["source_url"] is None


@pytest.mark.asyncio
async def test_extract_source_text_strips_html():
    """HTML tags are stripped from text/podcast sources."""
    html_input = "<p>Hello <b>world</b></p><script>alert('x')</script>"
    result = await extract_source("text", html_input)
    assert "<" not in result["content"]
    assert "alert" not in result["content"]
    assert "Hello" in result["content"]
    assert "world" in result["content"]


@pytest.mark.asyncio
async def test_extract_source_url_validates():
    """Localhost and private URLs are rejected with ValueError."""
    with pytest.raises(ValueError, match="unsafe URL"):
        await extract_source("url", "http://localhost/admin")

    with pytest.raises(ValueError, match="unsafe URL"):
        await extract_source("url", "http://127.0.0.1:8000/secret")

    with pytest.raises(ValueError, match="unsafe URL"):
        await extract_source("url", "http://192.168.1.1/config")


@pytest.mark.asyncio
async def test_extract_source_url_blocks_redirect_to_internal():
    """A safe initial URL that 302s to an internal address is rejected.

    Guards against SSRF via redirect: the up-front is_safe_url check passes,
    but the redirect hop must be re-validated.
    """
    redirect_resp = MagicMock()
    redirect_resp.is_redirect = True
    redirect_resp.next_request = MagicMock()
    redirect_resp.next_request.url = "http://169.254.169.254/latest/meta-data/"

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=redirect_resp)
    acm = MagicMock()
    acm.__aenter__ = AsyncMock(return_value=mock_client)
    acm.__aexit__ = AsyncMock(return_value=False)

    # Initial host is "safe", the metadata redirect target is not.
    def fake_is_safe(url):
        return "169.254" not in url

    with patch("backend.services.content_repurposer.httpx.AsyncClient", return_value=acm), patch(
        "backend.services.content_repurposer.is_safe_url", side_effect=fake_is_safe
    ):
        with pytest.raises(ValueError, match="unsafe URL"):
            await extract_source("url", "https://safe.example.com/post")


@pytest.mark.asyncio
async def test_extract_source_youtube():
    """YouTube extraction mocks the transcript API and joins text entries."""

    class FakeSnippet:
        def __init__(self, text):
            self.text = text

    fake_transcript = [FakeSnippet("Hello"), FakeSnippet("world"), FakeSnippet("test")]

    with patch("backend.services.content_repurposer.YouTubeTranscriptApi") as MockApi:
        instance = MagicMock()
        MockApi.return_value = instance
        instance.fetch.return_value = fake_transcript

        result = await extract_source("youtube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert result["content"] == "Hello world test"
    assert result["word_count"] == 3
    assert "dQw4w9WgXcQ" in result["source_url"]
    instance.fetch.assert_called_once_with("dQw4w9WgXcQ")


# ---------- repurpose ----------


@pytest.mark.asyncio
async def test_repurpose_returns_all_formats():
    """When no format filter is given, all 5 format keys are present."""
    fake_response = {
        "x_thread": ["tweet1", "tweet2"],
        "linkedin_carousel": {"slides": []},
        "email_sequence": [{"subject": "Hi", "body": "Content", "send_day": 1}],
        "tiktok_scripts": [{"hook": "Hey", "body": "Main", "cta": "Follow"}],
        "social_posts": {"facebook": "FB post", "instagram": "IG post", "google_business": "GB post"},
    }

    with patch("backend.services.content_repurposer.call_claude_messages", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = MagicMock(text=json.dumps(fake_response))

        result = await repurpose(
            source_content="Some long article content here.",
            title="Test Article",
            tenant_id="tenant-123",
            tone="engaging",
        )

    assert set(result.keys()) == {"x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"}


@pytest.mark.asyncio
async def test_repurpose_respects_format_filter():
    """Only requested formats are returned."""
    fake_response = {
        "x_thread": ["tweet1", "tweet2"],
        "social_posts": {"facebook": "FB post"},
    }

    with patch("backend.services.content_repurposer.call_claude_messages", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = MagicMock(text=json.dumps(fake_response))

        result = await repurpose(
            source_content="Content here.",
            title="Test",
            tenant_id="tenant-123",
            formats=["x_thread", "social_posts"],
        )

    assert "x_thread" in result
    assert "social_posts" in result
    # Formats not requested should not appear even if Claude returned them
    assert "linkedin_carousel" not in result
    assert "email_sequence" not in result
    assert "tiktok_scripts" not in result
