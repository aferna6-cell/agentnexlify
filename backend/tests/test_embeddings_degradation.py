"""Tests for embeddings.py graceful degradation when VOYAGE_API_KEY is absent.

Covers:
- Missing key raises EmbeddingUnavailable with no HTTP call (all three functions).
- EmbeddingUnavailable is a subclass of RuntimeError and Exception (catchable).
- Happy path with a present key uses the mocked HTTP response and returns a vector.
- Existing callers' bare ``except Exception`` pattern catches EmbeddingUnavailable.

NO live Voyage AI calls are made.  All HTTP is mocked via unittest.mock.patch.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Isolate settings from the real environment before importing embeddings.
# The key check happens at call time (not import time), so patching
# settings.voyage_api_key on the imported module is sufficient.
# ---------------------------------------------------------------------------

os.environ.setdefault("TESTING", "1")

import backend.services.embeddings as emb_module
from backend.services.embeddings import (
    EmbeddingUnavailable,
    EMBEDDING_DIM,
    embed_batch,
    embed_query,
    embed_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_voyage_response(vectors: list[list[float]]) -> MagicMock:
    """Build a fake httpx.Response whose .json() matches Voyage API shape."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "data": [{"embedding": v} for v in vectors]
    }
    return mock_resp


def _fake_vector(dim: int = EMBEDDING_DIM) -> list[float]:
    return [float(i) / dim for i in range(dim)]


# ---------------------------------------------------------------------------
# Missing-key tests — no HTTP call must be attempted
# ---------------------------------------------------------------------------

class TestMissingKeyRaisesEmbeddingUnavailable:
    """When VOYAGE_API_KEY is empty, all embed functions must raise
    EmbeddingUnavailable *before* opening any HTTP connection."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch.object(emb_module, "settings")
    def test_embed_text_no_http_call(self, mock_settings):
        mock_settings.voyage_api_key = ""

        with patch("httpx.AsyncClient") as mock_client_cls:
            with pytest.raises(EmbeddingUnavailable):
                self._run(embed_text("hello"))

        mock_client_cls.assert_not_called()

    @patch.object(emb_module, "settings")
    def test_embed_batch_no_http_call(self, mock_settings):
        mock_settings.voyage_api_key = ""

        with patch("httpx.AsyncClient") as mock_client_cls:
            with pytest.raises(EmbeddingUnavailable):
                self._run(embed_batch(["hello", "world"]))

        mock_client_cls.assert_not_called()

    @patch.object(emb_module, "settings")
    def test_embed_query_no_http_call(self, mock_settings):
        mock_settings.voyage_api_key = ""

        with patch("httpx.AsyncClient") as mock_client_cls:
            with pytest.raises(EmbeddingUnavailable):
                self._run(embed_query("search term"))

        mock_client_cls.assert_not_called()

    @patch.object(emb_module, "settings")
    def test_whitespace_only_key_raises(self, mock_settings):
        """A key that is only whitespace must be treated as missing."""
        mock_settings.voyage_api_key = "   "

        with pytest.raises(EmbeddingUnavailable):
            self._run(embed_text("hello"))

    @patch.object(emb_module, "settings")
    def test_none_key_raises(self, mock_settings):
        """None key (defensive) must also raise EmbeddingUnavailable."""
        mock_settings.voyage_api_key = None

        with pytest.raises(EmbeddingUnavailable):
            self._run(embed_text("hello"))


# ---------------------------------------------------------------------------
# Exception hierarchy — catchable as Exception
# ---------------------------------------------------------------------------

class TestEmbeddingUnavailableIsCatchable:
    """EmbeddingUnavailable must be catchable via RuntimeError and Exception."""

    def test_is_runtime_error(self):
        err = EmbeddingUnavailable("test")
        assert isinstance(err, RuntimeError)

    def test_is_exception(self):
        err = EmbeddingUnavailable("test")
        assert isinstance(err, Exception)

    def test_bare_except_exception_catches_it(self):
        """Simulate the existing caller pattern: except Exception → skip."""
        caught = False
        try:
            raise EmbeddingUnavailable("missing key")
        except Exception:
            caught = True
        assert caught, "EmbeddingUnavailable must be caught by bare except Exception"

    @patch.object(emb_module, "settings")
    def test_caller_degrades_gracefully(self, mock_settings):
        """Mimic os_memory.py caller pattern: exception → embedding=None."""
        mock_settings.voyage_api_key = ""

        embedding = None
        try:
            embedding = asyncio.get_event_loop().run_until_complete(
                embed_text("some content")
            )
        except Exception:
            pass  # caller stores None and continues

        assert embedding is None


# ---------------------------------------------------------------------------
# Happy path — present key, mocked HTTP
# ---------------------------------------------------------------------------

class TestHappyPathWithPresentKey:
    """When the key is set, HTTP is called once and the vector is returned."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch.object(emb_module, "settings")
    def test_embed_text_returns_vector(self, mock_settings):
        mock_settings.voyage_api_key = "voy-test-key-abc123"
        expected = _fake_vector()

        mock_resp = _make_voyage_response([expected])
        mock_post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = mock_post
            mock_cls.return_value = mock_ctx

            result = self._run(embed_text("test document"))

        assert len(result) == EMBEDDING_DIM
        assert result == [float(i) / EMBEDDING_DIM for i in range(EMBEDDING_DIM)]
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "Bearer voy-test-key-abc123" in str(call_kwargs)

    @patch.object(emb_module, "settings")
    def test_embed_batch_returns_vectors(self, mock_settings):
        mock_settings.voyage_api_key = "voy-test-key-abc123"
        texts = ["doc one", "doc two"]
        vectors = [_fake_vector(), _fake_vector()]

        mock_resp = _make_voyage_response(vectors)
        mock_post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = mock_post
            mock_cls.return_value = mock_ctx

            result = self._run(embed_batch(texts))

        assert len(result) == 2
        assert all(len(v) == EMBEDDING_DIM for v in result)
        mock_post.assert_called_once()

    @patch.object(emb_module, "settings")
    def test_embed_query_uses_query_input_type(self, mock_settings):
        mock_settings.voyage_api_key = "voy-test-key-abc123"
        expected = _fake_vector()

        mock_resp = _make_voyage_response([expected])
        mock_post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = mock_post
            mock_cls.return_value = mock_ctx

            result = self._run(embed_query("search term"))

        assert len(result) == EMBEDDING_DIM
        # Verify the payload used input_type="query"
        payload = mock_post.call_args[1]["json"]
        assert payload["input_type"] == "query"

    @patch.object(emb_module, "settings")
    def test_no_network_call_when_key_missing_even_after_happy_path(
        self, mock_settings
    ):
        """Key going missing mid-run raises immediately — no leftover state from
        previous call with valid key."""
        mock_settings.voyage_api_key = ""

        with patch("httpx.AsyncClient") as mock_cls:
            with pytest.raises(EmbeddingUnavailable):
                asyncio.get_event_loop().run_until_complete(embed_text("hi"))

        mock_cls.assert_not_called()
