"""Tests for the marketing-site support chatbot helpers."""

import base64
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import platform_support as ps

_SESSION = "sess-1"


def _table_mock(rows):
    """A Supabase table mock whose terminal .execute().data is `rows`."""
    t = MagicMock()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=rows)
    # Every builder method returns the same chain so any order resolves.
    for m in ("select", "eq", "order", "limit", "insert", "update", "upsert"):
        getattr(chain, m).return_value = chain
    t.select.return_value = chain
    t.insert.return_value = chain
    t.update.return_value = chain
    t.upsert.return_value = chain
    return t


def _db(table_rows):
    """table_rows: dict of table_name -> rows returned by .execute().data."""
    db = MagicMock()
    db.table.side_effect = lambda name: _table_mock(table_rows.get(name, []))
    return db


@pytest.mark.asyncio
async def test_generate_reply_uses_claude_text():
    fake = AsyncMock(return_value=MagicMock(text="Here is help."))
    with patch.object(ps, "call_claude_messages", fake):
        reply = await ps._generate_reply([{"role": "user", "content": "hi"}])
    assert reply == "Here is help."


@pytest.mark.asyncio
async def test_generate_reply_falls_back_on_error():
    with patch.object(ps, "call_claude_messages", AsyncMock(side_effect=RuntimeError())):
        reply = await ps._generate_reply([{"role": "user", "content": "hi"}])
    assert reply == ps._FALLBACK_REPLY


@pytest.mark.asyncio
async def test_email_transcript_once_sends_and_claims_slot():
    db = _db(
        {
            "platform_support_sessions": [
                {"session_id": _SESSION, "transcript_sent_at": None, "page_url": "/x"}
            ],
            "platform_support_messages": [
                {"role": "user", "content": "is it free?", "created_at": "t1"},
                {"role": "assistant", "content": "Yes, a free tier.", "created_at": "t2"},
            ],
        }
    )
    sender = AsyncMock(return_value={"success": True})
    with patch.object(ps, "get_service_supabase", return_value=db), \
            patch.object(ps, "send_platform_email", sender):
        await ps._email_transcript_once(_SESSION)
    assert sender.call_count == 1
    att = sender.call_args.kwargs["attachments"][0]
    assert "is it free?" in base64.b64decode(att["content"]).decode("utf-8")


@pytest.mark.asyncio
async def test_email_transcript_once_idempotent_when_already_sent():
    db = _db(
        {
            "platform_support_sessions": [
                {"session_id": _SESSION, "transcript_sent_at": "2026-06-15T00:00:00Z"}
            ],
            "platform_support_messages": [
                {"role": "user", "content": "hi", "created_at": "t1"},
            ],
        }
    )
    sender = AsyncMock()
    with patch.object(ps, "get_service_supabase", return_value=db), \
            patch.object(ps, "send_platform_email", sender):
        await ps._email_transcript_once(_SESSION)
    sender.assert_not_called()


@pytest.mark.asyncio
async def test_email_transcript_once_skips_when_no_user_message():
    db = _db(
        {
            "platform_support_sessions": [
                {"session_id": _SESSION, "transcript_sent_at": None}
            ],
            "platform_support_messages": [
                {"role": "assistant", "content": "greeting", "created_at": "t1"},
            ],
        }
    )
    sender = AsyncMock()
    with patch.object(ps, "get_service_supabase", return_value=db), \
            patch.object(ps, "send_platform_email", sender):
        await ps._email_transcript_once(_SESSION)
    sender.assert_not_called()


@pytest.mark.asyncio
async def test_notify_new_chat_sends_heads_up():
    sender = AsyncMock(return_value={"success": True})
    with patch.object(ps, "send_platform_email", sender):
        await ps._notify_new_chat("s1", "first message", "/pricing")
    body = sender.call_args.kwargs["body_html"]
    assert "first message" in body and "/pricing" in body


# --- endpoint-level coverage -------------------------------------------------


def test_chat_endpoint_returns_reply(client):
    db = _db(
        {
            "platform_support_sessions": [],
            "platform_support_messages": [{"role": "user", "content": "hi"}],
        }
    )
    with patch.object(ps, "get_service_supabase", return_value=db), patch.object(
        ps, "call_claude_messages", AsyncMock(return_value=MagicMock(text="Hello!"))
    ), patch.object(ps, "send_platform_email", AsyncMock(return_value={"success": True})):
        resp = client.post(
            "/api/v1/platform-support/chat",
            json={"session_id": "s1", "message": "hi", "page_url": "/x"},
        )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Hello!"


def test_chat_endpoint_existing_session(client):
    db = _db(
        {
            "platform_support_sessions": [{"session_id": "s2"}],
            "platform_support_messages": [{"role": "user", "content": "again"}],
        }
    )
    with patch.object(ps, "get_service_supabase", return_value=db), patch.object(
        ps, "call_claude_messages", AsyncMock(return_value=MagicMock(text="Hi back"))
    ):
        resp = client.post(
            "/api/v1/platform-support/chat",
            json={"session_id": "s2", "message": "again"},
        )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Hi back"


def test_chat_endpoint_rejects_blank_message(client):
    resp = client.post(
        "/api/v1/platform-support/chat",
        json={"session_id": "s1", "message": "   "},
    )
    assert resp.status_code == 400


def test_report_endpoint_acks(client):
    db = _db({"platform_support_sessions": [], "platform_support_messages": []})
    with patch.object(ps, "get_service_supabase", return_value=db), patch.object(
        ps, "send_platform_email", AsyncMock(return_value={"success": True})
    ):
        resp = client.post(
            "/api/v1/platform-support/report",
            json={
                "session_id": "s1",
                "email": "u@x.com",
                "message": "broken",
                "page_url": "/p",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_end_endpoint_acks(client):
    resp = client.post(
        "/api/v1/platform-support/end", json={"session_id": "s1"}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_email_report_attaches_transcript_and_sets_reply_to():
    db = _db(
        {
            "platform_support_messages": [
                {"role": "user", "content": "broken button", "created_at": "t1"},
            ],
        }
    )
    sender = AsyncMock(return_value={"success": True})
    with patch.object(ps, "get_service_supabase", return_value=db), \
            patch.object(ps, "send_platform_email", sender):
        await ps._email_report(_SESSION, "user@x.com", "it is broken", "/pricing")
    kwargs = sender.call_args.kwargs
    assert kwargs["reply_to"] == "user@x.com"
    assert "it is broken" in kwargs["body_html"]
    assert kwargs["attachments"][0]["filename"].endswith(".txt")
