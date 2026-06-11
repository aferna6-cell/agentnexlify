"""Tests for Agent OS file upload + image generation endpoints.

Covered:
  - 401 when no auth token
  - 415 when unsupported content type
  - 413 when file too large
  - 429 when daily upload cap exceeded
  - 200 with null vision_summary when vision call fails
  - 503 when image generation not configured
  - 429 when daily generation cap exceeded (provider configured + httpx mocked)
"""

import io
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.limiter import limiter

_TENANT_ID = "00000000-0000-0000-0000-000000000001"
_UPLOAD_URL = "/api/v1/os/uploads"
_GEN_URL = "/api/v1/os/images/generate"


# ── rate-limiter reset (mirrors test_admin_analytics_mrr.py) ─────────────────


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the shared in-memory limiter so IP-based limits don't bleed across tests."""
    limiter.reset()
    yield


# ── auth helpers ──────────────────────────────────────────────────────────────


def _auth_headers(tenant_id: str = _TENANT_ID) -> dict:
    from jose import jwt
    from backend.config import settings
    from datetime import datetime, timedelta, timezone

    payload = {
        "tenant_id": tenant_id,
        "email": "owner@test.com",
        "plan": "growth",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.api_secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ── common mock factories ─────────────────────────────────────────────────────


def _make_upload_db_mock(daily_count: int = 0):
    """Return a MagicMock supabase that returns *daily_count* rows for the daily-cap query
    and a successful insert for the metadata row."""
    db = MagicMock()

    # Chainable select result for daily-cap count
    count_chain = MagicMock()
    count_chain.select.return_value = count_chain
    count_chain.eq.return_value = count_chain
    count_chain.gte.return_value = count_chain
    count_chain.execute.return_value = MagicMock(data=[{"id": str(i)} for i in range(daily_count)])

    # Insert chain for metadata
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock(
        data=[{"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}]
    )

    # Storage upload
    storage = MagicMock()
    storage.from_.return_value.upload.return_value = None
    db.storage = storage

    # table() returns the count chain for select, insert chain for insert
    table_mock = MagicMock()
    table_mock.select.return_value = count_chain
    table_mock.insert.return_value = insert_chain
    db.table.return_value = table_mock

    return db


def _make_gen_db_mock(daily_gen_count: int = 0):
    """Mock for image generation — daily cap query + insert."""
    db = MagicMock()

    count_chain = MagicMock()
    count_chain.select.return_value = count_chain
    count_chain.eq.return_value = count_chain
    count_chain.gte.return_value = count_chain
    count_chain.execute.return_value = MagicMock(data=[{"id": str(i)} for i in range(daily_gen_count)])

    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock(
        data=[{"id": "aaaaaaaa-bbbb-cccc-dddd-ffffffffffff"}]
    )

    storage = MagicMock()
    storage.from_.return_value.upload.return_value = None
    db.storage = storage

    table_mock = MagicMock()
    table_mock.select.return_value = count_chain
    table_mock.insert.return_value = insert_chain
    db.table.return_value = table_mock

    return db


# ── 401: no auth ──────────────────────────────────────────────────────────────


def test_upload_requires_auth(client):
    """Upload endpoint must return 401 when no token is supplied."""
    resp = client.post(
        _UPLOAD_URL,
        files={"file": ("test.png", b"PNG", "image/png")},
    )
    assert resp.status_code == 401, resp.text


def test_generate_requires_auth(client):
    """Generate endpoint must return 401 when no token is supplied."""
    resp = client.post(_GEN_URL, json={"prompt": "a cat"})
    assert resp.status_code == 401, resp.text


# ── 415: bad content type ─────────────────────────────────────────────────────


def test_upload_rejects_bad_content_type(client, mock_supabase):
    """Content types outside the allowlist must be rejected."""
    db = _make_upload_db_mock(daily_count=0)
    mock_supabase.table.side_effect = db.table
    mock_supabase.storage = db.storage

    with patch("backend.routers.os_files.get_service_supabase", return_value=db):
        resp = client.post(
            _UPLOAD_URL,
            files={"file": ("script.js", b"alert(1)", "application/javascript")},
            headers=_auth_headers(),
        )
    assert resp.status_code == 415, resp.text


# ── 413: file too large ───────────────────────────────────────────────────────


def test_upload_rejects_oversize_file(client, mock_supabase):
    """Files over 10 MB must be rejected with 413."""
    big_data = b"x" * (10 * 1024 * 1024 + 1)
    db = _make_upload_db_mock(daily_count=0)

    with patch("backend.routers.os_files.get_service_supabase", return_value=db):
        resp = client.post(
            _UPLOAD_URL,
            files={"file": ("big.png", big_data, "image/png")},
            headers=_auth_headers(),
        )
    assert resp.status_code == 413, resp.text


# ── 429: daily upload cap ─────────────────────────────────────────────────────


def test_upload_daily_cap_429(client, mock_supabase):
    """When daily count >= 50 the endpoint must return 429."""
    db = _make_upload_db_mock(daily_count=50)

    with patch("backend.routers.os_files.get_service_supabase", return_value=db):
        resp = client.post(
            _UPLOAD_URL,
            files={"file": ("test.png", b"PNG", "image/png")},
            headers=_auth_headers(),
        )
    assert resp.status_code == 429, resp.text
    assert "50" in resp.text


# ── vision failure → 200 with null summary ────────────────────────────────────


def test_upload_vision_failure_still_200(client, mock_supabase):
    """Vision description failure must not fail the upload; summary stays null."""
    db = _make_upload_db_mock(daily_count=0)

    with (
        patch("backend.routers.os_files.get_service_supabase", return_value=db),
        patch(
            "backend.routers.os_files._vision_describe",
            new=AsyncMock(return_value=None),
        ),
    ):
        resp = client.post(
            _UPLOAD_URL,
            files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
            headers=_auth_headers(),
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["vision_summary"] is None
    assert body["public_url"].startswith("http")


# ── 503: generate not configured ─────────────────────────────────────────────


def test_generate_503_when_not_configured(client, mock_supabase):
    """When IMAGE_GEN_PROVIDER is empty the endpoint must return 503."""
    with patch("backend.routers.os_files.is_configured", return_value=False):
        resp = client.post(
            _GEN_URL,
            json={"prompt": "a mountain landscape"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["detail"]["error"] == "image_generation_not_configured"


# ── 429: daily generation cap ────────────────────────────────────────────────


def test_generate_daily_cap_429(client, mock_supabase):
    """When daily generated count >= 20 the endpoint must return 429."""
    db = _make_gen_db_mock(daily_gen_count=20)

    with (
        patch("backend.routers.os_files.is_configured", return_value=True),
        patch("backend.routers.os_files.get_service_supabase", return_value=db),
    ):
        resp = client.post(
            _GEN_URL,
            json={"prompt": "a robot"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 429, resp.text
    assert "20" in resp.text


# ── generate success path (provider + httpx mocked) ──────────────────────────


def test_generate_success(client, mock_supabase):
    """Happy-path: provider configured + httpx mocked → 201 with public_url."""
    import backend.services.image_gen as image_gen_module

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    db = _make_gen_db_mock(daily_gen_count=0)

    with (
        patch("backend.routers.os_files.is_configured", return_value=True),
        patch("backend.routers.os_files.get_service_supabase", return_value=db),
        patch.object(image_gen_module, "generate_image_png", return_value=fake_png),
        patch("backend.routers.os_files.generate_image_png", return_value=fake_png),
    ):
        resp = client.post(
            _GEN_URL,
            json={"prompt": "a sunny beach"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "public_url" in body
    assert "id" in body
