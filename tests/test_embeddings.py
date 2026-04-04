"""Tests for the embedding service."""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_httpx_response():
    """Mock a successful Voyage AI embedding response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.1] * 1024}],
        "usage": {"total_tokens": 50}
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture
def mock_httpx_batch_response():
    """Mock a successful batch embedding response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"embedding": [0.1] * 1024},
            {"embedding": [0.2] * 1024},
        ],
        "usage": {"total_tokens": 100}
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_embed_text_returns_1024_dim_vector(mock_httpx_response):
    """embed_text returns a 1024-dimension float list."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_text
        result = await embed_text("test query about AI chatbots")

        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)


@pytest.mark.asyncio
async def test_embed_batch_returns_multiple_vectors(mock_httpx_batch_response):
    """embed_batch returns one vector per input text."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_batch_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_batch
        result = await embed_batch(["text one", "text two"])

        assert len(result) == 2
        assert all(len(v) == 1024 for v in result)


@pytest.mark.asyncio
async def test_embed_text_truncates_long_input(mock_httpx_response):
    """embed_text truncates input longer than MAX_EMBED_CHARS."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_text
        long_text = "word " * 10000  # ~50K chars
        result = await embed_text(long_text)

        assert len(result) == 1024
        # Verify the API was called with truncated text
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        sent_text = payload["input"][0]
        assert len(sent_text) <= 32001  # MAX_EMBED_CHARS + 1 for safety
