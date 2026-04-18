"""Embedding service for knowledge base semantic search.

Uses Voyage AI (voyage-3-lite, 512 dimensions) as primary provider.
Shared utility — available for KB and future product features.
"""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3-lite"
EMBEDDING_DIM = 512
MAX_EMBED_CHARS = 32000  # ~8K tokens, safe limit for embedding input


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns 512-dim vector."""
    truncated = text[:MAX_EMBED_CHARS]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": [truncated],
                "input_type": "document",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [float(x) for x in data["data"][0]["embedding"]]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one API call. Returns list of 512-dim vectors."""
    truncated = [t[:MAX_EMBED_CHARS] for t in texts]
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": truncated,
                "input_type": "document",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [[float(x) for x in item["embedding"]] for item in data["data"]]


async def embed_query(text: str) -> list[float]:
    """Embed a search query. Uses input_type='query' for better retrieval."""
    truncated = text[:MAX_EMBED_CHARS]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": [truncated],
                "input_type": "query",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [float(x) for x in data["data"][0]["embedding"]]
