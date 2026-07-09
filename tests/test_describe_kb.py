"""Tests for POST /api/v1/onboarding/{tenant_id}/describe-kb.

Offline — mocks call_claude_messages and the Supabase client.
Three cases:
  1. Happy path: valid description returns parsed KB + FAQs from mocked Claude.
  2. Too-short description (< 20 chars) → 422 from Pydantic validation.
  3. Unsafe gbp_url → 400 (SSRF prevention mirrors auto-kb behavior).
"""

import asyncio
import os
import sys
from pathlib import Path

# Must be set before any backend import.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("ADMIN_API_SECRET_KEY", "test-admin-secret-key-for-jwt")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import httpx
import pytest

import backend.models.database as _db_module

_REAL_ASGI_TRANSPORT = httpx.ASGITransport
_REAL_ASYNC_CLIENT = httpx.AsyncClient


class _SyncASGITestClient:
    """Minimal sync ASGI client that avoids Starlette TestClient lifespan stalls."""

    __test__ = False

    def __init__(self, asgi_app):
        self._app = asgi_app

    async def _request(self, method, url, **kwargs):
        transport = _REAL_ASGI_TRANSPORT(app=self._app, raise_app_exceptions=False)
        async with _REAL_ASYNC_CLIENT(transport=transport, base_url="http://testserver") as c:
            return await c.request(method, url, **kwargs)

    def request(self, method, url, **kwargs):
        return asyncio.run(self._request(method, url, **kwargs))

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def close(self):
        return None


@pytest.fixture()
def client():
    from backend.main import app
    c = _SyncASGITestClient(app)
    yield c
    c.close()


@pytest.fixture()
def mock_supabase():
    mock = MagicMock()
    prev_service = _db_module._service_client
    prev_public = _db_module._public_client
    _db_module._service_client = mock
    _db_module._public_client = mock
    try:
        yield mock
    finally:
        _db_module._service_client = prev_service
        _db_module._public_client = prev_public


@pytest.fixture()
def auth_headers():
    from jose import jwt
    from backend.config import settings

    payload = {
        "tenant_id": TENANT_ID,
        "email": "owner@test.com",
        "plan": "growth",
        "business_name": "Downtown Dental",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.api_secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


TENANT_ID = "00000000-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/onboarding/{TENANT_ID}/describe-kb"

# ---------------------------------------------------------------------------
# Minimal Claude response reused across tests
# ---------------------------------------------------------------------------

_CLAUDE_RAW = """===KNOWLEDGE_BASE===
## About
Downtown Dental is a full-service dental clinic in Chicago serving patients since 2010.
## Services
- General checkups
- Teeth whitening
- Invisalign
===CUSTOM_INSTRUCTIONS===
You are the Downtown Dental Assistant.
- Family-friendly dental clinic in Chicago
- Scheduling: ask for preferred day and time
NEVER mention AgentNexLiFy.
===FAQ_START===
Q: Do you accept insurance?
A: Yes, we accept most PPO plans.
C: billing
Q: How do I book an appointment?
A: Call us or use the online booking link.
C: scheduling
Q: Do you offer emergency dental?
A: Yes, same-day slots for emergencies.
C: emergency
Q: Do you see children?
A: Yes, we welcome patients 3 and up.
C: scope
Q: Is parking available?
A: Free parking in the lot behind the building.
C: location
===FAQ_END===
"""


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi limiter so the 5/hour cap does not collide across tests."""
    from backend.limiter import limiter

    try:
        limiter.reset()
    except Exception:
        try:
            limiter._storage.storage.clear()
        except Exception:
            pass
    yield


def _setup_db(mock_supabase):
    """Seed the Supabase mock to return a minimal tenant row."""
    tenant = MagicMock()
    tenant.data = {
        "business_name": "Downtown Dental",
        "business_type": "dental",
        "city": "Chicago",
        "phone": "312-555-0100",
    }
    # .table("tenants").select(...).eq(...).single().execute()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = tenant
    # .table("widget_configs").update(...).eq(...).execute()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # .table("faq_entries").insert(...).execute()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()


def _patch_claude(monkeypatch):
    """Replace call_claude_messages with a coroutine returning _CLAUDE_RAW."""
    fake = MagicMock()
    fake.text = _CLAUDE_RAW

    async def _fake_call(**kwargs):
        return fake

    monkeypatch.setattr(
        "backend.services.kb_from_text.call_claude_messages", _fake_call
    )


# ---------------------------------------------------------------------------
# Test 1 — happy path
# ---------------------------------------------------------------------------


def test_describe_kb_happy_path_returns_parsed_kb_and_faqs(
    client, auth_headers, mock_supabase, monkeypatch
):
    """Valid description → 200 with non-empty KB, custom_instructions, and FAQs."""
    _setup_db(mock_supabase)
    _patch_claude(monkeypatch)

    resp = client.post(
        ENDPOINT,
        headers=auth_headers,
        json={
            "description": (
                "Downtown Dental is a family dental clinic in Chicago. "
                "We offer general checkups, teeth whitening, and Invisalign. "
                "Open Monday through Friday 9am to 5pm. "
                "We accept most PPO insurance plans and offer same-day emergencies."
            )
        },
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()

    # KB content
    assert "knowledge_base" in body
    assert len(body["knowledge_base"]) > 50, "knowledge_base should not be empty"

    # Custom instructions
    assert "custom_instructions" in body
    assert len(body["custom_instructions"]) > 10, "custom_instructions should not be empty"

    # FAQs parsed from Claude response
    assert "faqs" in body
    assert len(body["faqs"]) >= 3, f"Expected >= 3 FAQs, got {len(body['faqs'])}"
    faq_questions = {f["question"] for f in body["faqs"]}
    assert "Do you accept insurance?" in faq_questions

    # pages_crawled must be 0 (no website was crawled)
    assert body["pages_crawled"] == 0

    # chars_extracted == len(description)
    assert body["chars_extracted"] > 0

    # Supabase persistence was called for both widget_configs and faq_entries
    calls = [str(c) for c in mock_supabase.table.call_args_list]
    table_names_used = {c[0][0] for c in mock_supabase.table.call_args_list}
    assert "widget_configs" in table_names_used, (
        f"widget_configs not written. tables used: {table_names_used}"
    )
    assert "faq_entries" in table_names_used, (
        f"faq_entries not written. tables used: {table_names_used}"
    )


# ---------------------------------------------------------------------------
# Test 2 — too-short description → 422
# ---------------------------------------------------------------------------


def test_describe_kb_too_short_description_returns_422(
    client, auth_headers, mock_supabase
):
    """Description shorter than 20 chars must be rejected by Pydantic with 422."""
    resp = client.post(
        ENDPOINT,
        headers=auth_headers,
        json={"description": "Too short"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for too-short description, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Test 3 — unsafe gbp_url → 400
# ---------------------------------------------------------------------------


def test_describe_kb_unsafe_gbp_url_returns_400(
    client, auth_headers, mock_supabase, monkeypatch
):
    """A localhost/private-IP gbp_url must be rejected with 400 (SSRF guard)."""
    _setup_db(mock_supabase)
    _patch_claude(monkeypatch)

    resp = client.post(
        ENDPOINT,
        headers=auth_headers,
        json={
            "description": "We are a great dental clinic in Chicago offering all dental services.",
            "gbp_url": "http://localhost:8080/admin",
        },
    )
    assert resp.status_code == 400, (
        f"Expected 400 for unsafe gbp_url, got {resp.status_code}: {resp.text}"
    )
    assert "gbp_url" in resp.json().get("detail", ""), (
        f"Error detail should mention 'gbp_url'. Got: {resp.json()}"
    )
