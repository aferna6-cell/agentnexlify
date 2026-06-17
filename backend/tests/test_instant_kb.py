"""Tests for Instant KB from website URL (service + endpoints).

Web fetch (httpx) and the LLM call (call_claude_messages) are mocked. Covers
the success path and every failure mode so onboarding never crashes.
"""

import asyncio

import pytest

from backend.services import instant_kb
from backend.services.instant_kb import (
    InstantKbError,
    _parse_faq_json,
    draft_faq_entries,
    fetch_website_text,
    persist_faq_entries,
)


# --- httpx response/client doubles -----------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, content=b"", content_type="text/html", encoding="utf-8"):
        self.status_code = status_code
        self.content = content
        self.encoding = encoding
        self.headers = {"content-type": content_type}


class _FakeClient:
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise = raise_exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        if self._raise is not None:
            raise self._raise
        return self._response


def _patch_httpx(monkeypatch, response=None, raise_exc=None):
    monkeypatch.setattr(
        instant_kb.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeClient(response=response, raise_exc=raise_exc),
    )


def _allow_url(monkeypatch, allowed=True):
    monkeypatch.setattr(instant_kb, "is_safe_url", lambda _u: allowed)


# --- fetch_website_text ----------------------------------------------------


def test_fetch_success_strips_html_and_truncates(monkeypatch):
    _allow_url(monkeypatch)
    html = b"<html><head><style>x{}</style></head><body><h1>Acme Plumbing</h1>" \
           b"<script>bad()</script><p>We fix drains, water heaters, and sewer lines " \
           b"across the greater Austin area every day.</p></body></html>"
    _patch_httpx(monkeypatch, _FakeResponse(content=html))
    text = asyncio.run(fetch_website_text("acme.com"))
    assert "Acme Plumbing" in text
    assert "We fix drains" in text
    assert "bad()" not in text  # script stripped
    assert "x{}" not in text  # style stripped


def test_fetch_unsafe_url_raises(monkeypatch):
    _allow_url(monkeypatch, allowed=False)
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(fetch_website_text("http://169.254.169.254/"))
    assert ei.value.code == "unsafe_url"


def test_fetch_network_failure_raises(monkeypatch):
    _allow_url(monkeypatch)
    _patch_httpx(monkeypatch, raise_exc=instant_kb.httpx.ConnectError("boom"))
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(fetch_website_text("acme.com"))
    assert ei.value.code == "fetch_failed"


def test_fetch_http_error_status_raises(monkeypatch):
    _allow_url(monkeypatch)
    _patch_httpx(monkeypatch, _FakeResponse(status_code=503, content=b"down"))
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(fetch_website_text("acme.com"))
    assert ei.value.code == "fetch_failed"


def test_fetch_non_html_raises(monkeypatch):
    _allow_url(monkeypatch)
    _patch_httpx(monkeypatch, _FakeResponse(content=b"%PDF-1.7", content_type="application/pdf"))
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(fetch_website_text("acme.com/brochure.pdf"))
    assert ei.value.code == "not_html"


def test_fetch_empty_page_raises(monkeypatch):
    _allow_url(monkeypatch)
    _patch_httpx(monkeypatch, _FakeResponse(content=b"<html><body>  </body></html>"))
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(fetch_website_text("acme.com"))
    assert ei.value.code == "empty_page"


def test_fetch_huge_page_truncated(monkeypatch):
    _allow_url(monkeypatch)
    body = b"<html><body>" + (b"word " * 200000) + b"</body></html>"
    _patch_httpx(monkeypatch, _FakeResponse(content=body))
    text = asyncio.run(fetch_website_text("acme.com"))
    assert len(text) <= instant_kb._MAX_TEXT_CHARS


# --- _parse_faq_json -------------------------------------------------------


def test_parse_plain_json_array():
    raw = '[{"question":"Hours?","answer":"9-5","category":"hours"}]'
    out = _parse_faq_json(raw)
    assert out == [{"question": "Hours?", "answer": "9-5", "category": "hours"}]


def test_parse_strips_code_fence_and_normalizes_category():
    raw = '```json\n[{"question":"Q","answer":"A","category":"weird"}]\n```'
    out = _parse_faq_json(raw)
    assert out[0]["category"] == "general"  # unknown -> general


def test_parse_extracts_array_from_prose():
    raw = 'Here you go: [{"question":"Q","answer":"A"}] hope that helps'
    out = _parse_faq_json(raw)
    assert out == [{"question": "Q", "answer": "A", "category": "general"}]


def test_parse_drops_incomplete_and_handles_wrapper():
    raw = '{"faqs":[{"question":"Q","answer":"A"},{"question":"","answer":"x"}]}'
    out = _parse_faq_json(raw)
    assert len(out) == 1


def test_parse_unusable_returns_empty():
    assert _parse_faq_json("not json at all") == []
    assert _parse_faq_json("") == []


# --- draft_faq_entries -----------------------------------------------------


class _LLMResult:
    def __init__(self, text):
        self.text = text


def test_draft_success(monkeypatch):
    async def fake_call(**kwargs):
        return _LLMResult('[{"question":"Do you take walk-ins?","answer":"Yes","category":"booking"}]')

    monkeypatch.setattr(instant_kb, "call_claude_messages", fake_call)
    out = asyncio.run(draft_faq_entries("Acme", "salon", "lots of website text here"))
    assert out[0]["question"] == "Do you take walk-ins?"
    assert out[0]["category"] == "booking"


def test_draft_llm_failure_raises(monkeypatch):
    async def fake_call(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(instant_kb, "call_claude_messages", fake_call)
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(draft_faq_entries("Acme", "salon", "text"))
    assert ei.value.code == "llm_failed"


def test_draft_no_usable_entries_raises(monkeypatch):
    async def fake_call(**kwargs):
        return _LLMResult("I cannot help with that.")

    monkeypatch.setattr(instant_kb, "call_claude_messages", fake_call)
    with pytest.raises(InstantKbError) as ei:
        asyncio.run(draft_faq_entries("Acme", "salon", "text"))
    assert ei.value.code == "no_entries"


# --- persist_faq_entries ---------------------------------------------------


class _InsertChain:
    def __init__(self, sink, raise_exc=None):
        self._sink = sink
        self._raise = raise_exc

    def insert(self, rows):
        if self._raise is not None:
            raise self._raise
        self._sink.append(rows)
        return self

    def execute(self):
        return self


class _FakeDB:
    def __init__(self, raise_exc=None):
        self.inserted = []
        self._raise = raise_exc

    def table(self, _name):
        return _InsertChain(self.inserted, raise_exc=self._raise)


def test_persist_writes_tenant_scoped_rows():
    db = _FakeDB()
    saved = persist_faq_entries(
        db, "tenant-1",
        [{"question": "Q1", "answer": "A1", "category": "services"},
         {"question": "", "answer": "drop me"}],
    )
    assert saved == 1
    row = db.inserted[0][0]
    assert row["tenant_id"] == "tenant-1"
    assert row["is_active"] is True


def test_persist_db_failure_raises():
    db = _FakeDB(raise_exc=RuntimeError("db down"))
    with pytest.raises(InstantKbError) as ei:
        persist_faq_entries(db, "tenant-1", [{"question": "Q", "answer": "A"}])
    assert ei.value.code == "persist_failed"


# --- endpoint tests --------------------------------------------------------

TENANT = "00000000-0000-0000-0000-000000000001"


def _seed_tenant(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"business_name": "Acme", "business_type": "salon"}
    ]


def test_draft_endpoint_success(client, auth_headers, mock_supabase, monkeypatch):
    _seed_tenant(mock_supabase)

    async def fake_fetch(url):
        return "website text"

    async def fake_draft(**kwargs):
        return [{"question": "Q", "answer": "A", "category": "general"}]

    monkeypatch.setattr("backend.routers.instant_kb.fetch_website_text", fake_fetch)
    monkeypatch.setattr("backend.routers.instant_kb.draft_faq_entries", fake_draft)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/draft",
        headers=auth_headers,
        json={"url": "https://acme.com"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["faqs"][0]["question"] == "Q"
    assert body["chars_extracted"] == len("website text")


def test_draft_endpoint_fetch_failure_maps_502(client, auth_headers, mock_supabase, monkeypatch):
    _seed_tenant(mock_supabase)

    async def fake_fetch(url):
        raise InstantKbError("fetch_failed", "could not reach site")

    monkeypatch.setattr("backend.routers.instant_kb.fetch_website_text", fake_fetch)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/draft",
        headers=auth_headers,
        json={"url": "https://acme.com"},
    )
    assert resp.status_code == 502
    assert "could not reach" in resp.json()["detail"]


def test_draft_endpoint_empty_page_maps_422(client, auth_headers, mock_supabase, monkeypatch):
    _seed_tenant(mock_supabase)

    async def fake_fetch(url):
        raise InstantKbError("empty_page", "no readable text")

    monkeypatch.setattr("backend.routers.instant_kb.fetch_website_text", fake_fetch)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/draft",
        headers=auth_headers,
        json={"url": "https://acme.com"},
    )
    assert resp.status_code == 422


def test_draft_endpoint_llm_failure_maps_502(client, auth_headers, mock_supabase, monkeypatch):
    _seed_tenant(mock_supabase)

    async def fake_fetch(url):
        return "text"

    async def fake_draft(**kwargs):
        raise InstantKbError("llm_failed", "ai unavailable")

    monkeypatch.setattr("backend.routers.instant_kb.fetch_website_text", fake_fetch)
    monkeypatch.setattr("backend.routers.instant_kb.draft_faq_entries", fake_draft)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/draft",
        headers=auth_headers,
        json={"url": "https://acme.com"},
    )
    assert resp.status_code == 502


def test_draft_endpoint_wrong_tenant_403(client, auth_headers, mock_supabase, monkeypatch):
    resp = client.post(
        "/api/v1/instant-kb/99999999-9999-9999-9999-999999999999/draft",
        headers=auth_headers,
        json={"url": "https://acme.com"},
    )
    assert resp.status_code == 403


def test_confirm_endpoint_success(client, auth_headers, mock_supabase, monkeypatch):
    calls = {}

    def fake_persist(db, tenant_id, entries):
        calls["tenant_id"] = tenant_id
        calls["entries"] = entries
        return len(entries)

    monkeypatch.setattr("backend.routers.instant_kb.persist_faq_entries", fake_persist)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/confirm",
        headers=auth_headers,
        json={"faqs": [{"question": "Q", "answer": "A", "category": "general"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1
    assert calls["tenant_id"] == TENANT


def test_confirm_endpoint_empty_list_422(client, auth_headers, mock_supabase):
    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/confirm",
        headers=auth_headers,
        json={"faqs": []},
    )
    assert resp.status_code == 422  # pydantic min_length=1


def test_confirm_endpoint_persist_failure_maps_500(client, auth_headers, mock_supabase, monkeypatch):
    def fake_persist(db, tenant_id, entries):
        raise InstantKbError("persist_failed", "db down")

    monkeypatch.setattr("backend.routers.instant_kb.persist_faq_entries", fake_persist)

    resp = client.post(
        f"/api/v1/instant-kb/{TENANT}/confirm",
        headers=auth_headers,
        json={"faqs": [{"question": "Q", "answer": "A"}]},
    )
    assert resp.status_code == 500
