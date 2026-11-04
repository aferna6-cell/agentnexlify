"""Voyage free-tier limits: token-sized batches, RPM pacing, 429 retries.

A 64-chunk request returns HTTP 429. A single input succeeds. Reindex must
still embed every chunk before it deletes the tenant's existing rows.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import pytest

import backend.services.embeddings as emb
from backend.services.embeddings import (
    EmbeddingUnavailable,
    embed_batch,
    estimate_tokens,
    pack_token_batches,
)
from backend.services.tenant_kb_index import reindex_tenant

TENANT = "00000000-0000-0000-0000-000000000001"


class _Limits:
    voyage_api_key = "voy-test"
    voyage_max_tokens_per_request = 8000
    voyage_rpm = 3


class _Response:
    def __init__(self, status, vectors=None, retry_after=None):
        self.status_code = status
        self.headers = {} if retry_after is None else {"Retry-After": str(retry_after)}
        self._vectors = vectors or []

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", emb.VOYAGE_API_URL)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"voyage {self.status_code}", request=request, response=response
            )

    def json(self):
        return {"data": [{"embedding": vector} for vector in self._vectors]}


def _vector(marker: float) -> list[float]:
    return [marker] * emb.EMBEDDING_DIM


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.inputs = []

    async def post(self, url, headers=None, json=None):
        self.inputs.append(list(json["input"]))
        if not self.responses:
            raise AssertionError("Voyage was called more times than scripted")
        return self.responses.pop(0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _install(monkeypatch, client, sleeps):
    monkeypatch.setattr(emb, "settings", _Limits())
    monkeypatch.setattr(emb, "_next_request_at", 0.0)
    monkeypatch.setattr(emb.httpx, "AsyncClient", lambda *args, **kwargs: client)

    async def _sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(emb, "_sleep", _sleep)


def test_pack_token_batches_stays_under_the_cap():
    chunk = "x" * 1000
    assert estimate_tokens(chunk) == 250
    batches = pack_token_batches([chunk] * 64, 8000)
    assert [len(batch) for batch in batches] == [32, 32]
    assert all(sum(estimate_tokens(text) for text in batch) <= 8000 for batch in batches)


def test_one_oversized_input_is_not_split():
    huge = "y" * 40000
    batches = pack_token_batches([huge], 8000)
    assert batches == [[huge]]
    assert estimate_tokens(huge) > 8000


def test_embed_batch_splits_64_chunks_and_keeps_order(monkeypatch):
    texts = [f"chunk-{i}-" + ("x" * 990) for i in range(64)]
    client = _Client([
        _Response(200, [_vector(float(i)) for i in range(32)]),
        _Response(200, [_vector(float(i)) for i in range(32, 64)]),
    ])
    _install(monkeypatch, client, [])
    vectors = asyncio.run(embed_batch(texts))
    assert [len(batch) for batch in client.inputs] == [32, 32]
    assert [vector[0] for vector in vectors] == [float(i) for i in range(64)]


def test_429_retries_honor_retry_after_then_succeed(monkeypatch):
    sleeps = []
    client = _Client([
        _Response(429, retry_after="7"),
        _Response(200, [_vector(1.0)]),
    ])
    _install(monkeypatch, client, sleeps)
    vectors = asyncio.run(embed_batch(["oil changes"]))
    assert sleeps == [7.0]
    assert client.inputs == [["oil changes"], ["oil changes"]]
    assert vectors[0][0] == 1.0


def test_5xx_uses_exponential_backoff(monkeypatch):
    sleeps = []
    client = _Client([
        _Response(503),
        _Response(502),
        _Response(200, [_vector(2.0)]),
    ])
    _install(monkeypatch, client, sleeps)
    vectors = asyncio.run(embed_batch(["brakes"]))
    assert sleeps == [1.0, 2.0]
    assert vectors[0][0] == 2.0


def test_retry_after_http_date_is_honored():
    when = datetime.now(timezone.utc) + timedelta(seconds=30)
    response = _Response(429, retry_after=format_datetime(when))
    delay = emb._retry_after_seconds(response)
    assert 25 <= delay <= 35


def test_400_is_not_retried(monkeypatch):
    sleeps = []
    client = _Client([_Response(400)])
    _install(monkeypatch, client, sleeps)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(embed_batch(["nope"]))
    assert sleeps == []
    assert len(client.inputs) == 1


def test_429_stops_after_six_attempts(monkeypatch):
    sleeps = []
    client = _Client([_Response(429, retry_after="0")] * 6)
    _install(monkeypatch, client, sleeps)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(embed_batch(["still limited"]))
    assert len(client.inputs) == 6
    assert sleeps == [0.0] * 5


def test_rpm_paces_between_batches(monkeypatch):
    now = {"t": 0.0}
    sleeps = []

    def _monotonic():
        return now["t"]

    async def _sleep(seconds):
        sleeps.append(seconds)
        now["t"] += seconds

    texts = ["A" * 12000, "B" * 12000, "C" * 12000]
    client = _Client([
        _Response(200, [_vector(1.0), _vector(2.0)]),
        _Response(200, [_vector(3.0)]),
    ])
    limits = _Limits()
    limits.voyage_rpm = 3
    monkeypatch.setattr(emb, "settings", limits)
    monkeypatch.setattr(emb, "_next_request_at", 0.0)
    monkeypatch.setattr(emb, "_pacing_enabled", lambda: True)
    monkeypatch.setattr(emb.time, "monotonic", _monotonic)
    monkeypatch.setattr(emb, "_sleep", _sleep)
    monkeypatch.setattr(emb.httpx, "AsyncClient", lambda *args, **kwargs: client)
    vectors = asyncio.run(embed_batch(texts))
    assert [len(batch) for batch in client.inputs] == [2, 1]
    assert sleeps == [20.0]
    assert [vector[0] for vector in vectors] == [1.0, 2.0, 3.0]


class _Docs:
    def __init__(self):
        self.name = ""
        self.deleted = False

    def table(self, name):
        self.name = name
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def delete(self):
        self.deleted = True
        return self

    def insert(self, rows):
        raise AssertionError("chunks were inserted after a Voyage failure")

    def execute(self):
        if self.name == "tenant_kb_documents":
            return SimpleNamespace(data=[{
                "id": "22222222-2222-2222-2222-222222222222",
                "filename": "Services.md",
                "content_md": "We offer oil changes and brake jobs for local drivers. " * 40,
                "source": "upload",
                "status": "active",
            }])
        return SimpleNamespace(data=[])


def test_reindex_keeps_chunks_when_voyage_keeps_returning_429(monkeypatch):
    db = _Docs()
    sleeps = []
    client = _Client([_Response(429, retry_after="0")] * 6)
    _install(monkeypatch, client, sleeps)
    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: db)
    with pytest.raises(EmbeddingUnavailable):
        asyncio.run(reindex_tenant(TENANT))
    assert db.deleted is False
    assert len(client.inputs) == 6
