"""Embedding service for knowledge base semantic search.

Uses Voyage AI (voyage-3-lite, 512 dimensions) as primary provider.
Shared utility — available for KB and future product features.

Free-tier accounts reject large batches with HTTP 429 (about 3 requests per
minute and 10K tokens per minute). A single input still succeeds, so callers
send token-sized groups, wait between requests, and retry 429/5xx.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3-lite"
EMBEDDING_DIM = 512
MAX_EMBED_CHARS = 32000  # ~8K tokens, safe limit for one input
DEFAULT_MAX_TOKENS_PER_REQUEST = 8000
DEFAULT_RPM = 3
VOYAGE_MAX_ATTEMPTS = 6

_pace_lock = asyncio.Lock()
_next_request_at = 0.0


class EmbeddingUnavailable(RuntimeError):
    """Raised when embeddings cannot be produced (missing key / provider down).

    All callers that already catch ``Exception`` will catch this automatically.
    Callers that want to distinguish a missing-key skip from a real API error
    can catch ``EmbeddingUnavailable`` specifically.
    """


def _voyage_key() -> str:
    """Return the configured Voyage API key.

    Raises ``EmbeddingUnavailable`` immediately (no HTTP call) when the key is
    missing or empty so the caller gets a typed, loggable error rather than a
    doomed 401 round-trip.
    """
    key = (settings.voyage_api_key or "").strip()
    if not key:
        logger.warning(
            "embeddings: VOYAGE_API_KEY missing or empty — skipping embedding "
            "(vector will be None). Set VOYAGE_API_KEY in the backend env to "
            "enable semantic search."
        )
        raise EmbeddingUnavailable(
            "VOYAGE_API_KEY not configured — set it in the backend environment"
        )
    return key


def _int_setting(name: str, default: int) -> int:
    raw = getattr(settings, name, None)
    if isinstance(raw, bool) or raw is None:
        return default
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError:
            return default
    return default


def estimate_tokens(text: str) -> int:
    """Rough token count. Voyage is about 4 characters per token."""
    return max(1, (len(text) + 3) // 4)


def pack_token_batches(texts: list[str], max_tokens: int) -> list[list[str]]:
    """Group inputs so each request stays within ``max_tokens``.

    A single input that is already over the cap is sent alone. Splitting one
    string would embed something other than the chunk the caller stored.
    """
    limit = max(1, int(max_tokens))
    batches: list[list[str]] = []
    current: list[str] = []
    used = 0
    for text in texts:
        tokens = estimate_tokens(text)
        if current and used + tokens > limit:
            batches.append(current)
            current = []
            used = 0
        current.append(text)
        used += tokens
    if current:
        batches.append(current)
    return batches


def _retry_after_seconds(response) -> float | None:
    raw = ""
    headers = getattr(response, "headers", None)
    if headers is not None:
        raw = headers.get("Retry-After") or headers.get("retry-after") or ""
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _backoff_seconds(attempt: int, response) -> float:
    """Seconds to wait before the next try. Retry-After wins when present."""
    retry_after = _retry_after_seconds(response)
    if retry_after is not None:
        return retry_after
    return float(min(32, 2 ** max(0, attempt - 1)))


def _pacing_enabled() -> bool:
    """Pace in production. Pytest skips the wait unless VOYAGE_RPM is set."""
    if os.environ.get("VOYAGE_RPM") not in (None, ""):
        return _int_setting("voyage_rpm", DEFAULT_RPM) > 0
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return _int_setting("voyage_rpm", DEFAULT_RPM) > 0


async def _sleep(seconds: float) -> None:
    if seconds > 0:
        await asyncio.sleep(seconds)


async def _pace() -> None:
    """Leave at least 60/VOYAGE_RPM seconds between Voyage requests."""
    global _next_request_at
    if not _pacing_enabled():
        return
    rpm = _int_setting("voyage_rpm", DEFAULT_RPM)
    if rpm <= 0:
        return
    interval = 60.0 / rpm
    async with _pace_lock:
        now = time.monotonic()
        wait = _next_request_at - now
        if wait > 0:
            await _sleep(wait)
            now = time.monotonic()
        _next_request_at = now + interval


def _status_code(response) -> int | None:
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    return None


def _retryable(status: int | None) -> bool:
    return status == 429 or (status is not None and 500 <= status <= 599)


async def _post_embeddings(client, key: str, texts: list[str], input_type: str) -> dict:
    payload = {
        "model": VOYAGE_MODEL,
        "input": texts,
        "input_type": input_type,
    }
    response = None
    for attempt in range(1, VOYAGE_MAX_ATTEMPTS + 1):
        await _pace()
        response = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
        status = _status_code(response)
        if _retryable(status) and attempt < VOYAGE_MAX_ATTEMPTS:
            delay = _backoff_seconds(attempt, response)
            logger.warning(
                "embeddings: Voyage HTTP %s, attempt %s/%s, sleeping %.1fs",
                status,
                attempt,
                VOYAGE_MAX_ATTEMPTS,
                delay,
            )
            await _sleep(delay)
            continue
        response.raise_for_status()
        return response.json()


def _prepare(text: str) -> str:
    return (text or "")[:MAX_EMBED_CHARS]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns 512-dim vector.

    Raises:
        EmbeddingUnavailable: VOYAGE_API_KEY is missing/empty (no HTTP call made).
        httpx.HTTPStatusError: Voyage API returned a non-2xx status.
    """
    key = _voyage_key()
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _post_embeddings(client, key, [_prepare(text)], "document")
    return [float(x) for x in data["data"][0]["embedding"]]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed texts in token-sized requests. Returns one vector per input.

    Each request stays under ``VOYAGE_MAX_TOKENS_PER_REQUEST`` (default 8000).
    Requests are spaced by ``VOYAGE_RPM`` (default 3). HTTP 429 and 5xx are
    retried up to 6 times, waiting ``Retry-After`` when Voyage sends it.

    Raises:
        EmbeddingUnavailable: VOYAGE_API_KEY is missing/empty (no HTTP call made).
        httpx.HTTPStatusError: Voyage still failed after the retries.
    """
    key = _voyage_key()
    prepared = [_prepare(text) for text in texts]
    if not prepared:
        return []
    max_tokens = max(1, _int_setting("voyage_max_tokens_per_request", DEFAULT_MAX_TOKENS_PER_REQUEST))
    groups = pack_token_batches(prepared, max_tokens)
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for group in groups:
            data = await _post_embeddings(client, key, group, "document")
            got = [[float(x) for x in item["embedding"]] for item in data["data"]]
            if len(got) != len(group):
                raise RuntimeError(
                    "Voyage returned a different number of embeddings than inputs"
                )
            vectors.extend(got)
    return vectors


async def embed_query(text: str) -> list[float]:
    """Embed a search query. Uses input_type='query' for better retrieval.

    Raises:
        EmbeddingUnavailable: VOYAGE_API_KEY is missing/empty (no HTTP call made).
        httpx.HTTPStatusError: Voyage API returned a non-2xx status.
    """
    key = _voyage_key()
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _post_embeddings(client, key, [_prepare(text)], "query")
    return [float(x) for x in data["data"][0]["embedding"]]
