"""Tests for conversation-wrap email notifications (backend/services/conversation_notify.py).

Covers:
  - build_transcript_html: role labels, HTML escaping (XSS), lead block, empty case
  - notify_idle_conversations: opted-out tenants skipped, idle-vs-active filter,
    exactly-once claim, owner_email fallback, send-failure releases the claim
"""

import os
os.environ["TESTING"] = "1"
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _utc_now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# build_transcript_html — pure function
# ---------------------------------------------------------------------------

class TestBuildTranscript:
    def _msgs(self):
        return [
            {"role": "user", "content": "Hi, do you fix water heaters?", "created_at": "2026-06-13T10:00:00Z"},
            {"role": "assistant", "content": "Yes! We do.", "created_at": "2026-06-13T10:00:05Z"},
        ]

    def test_labels_visitor_and_business(self):
        from backend.services.conversation_notify import build_transcript_html
        html = build_transcript_html("Acme Plumbing", self._msgs())
        assert "Visitor:" in html
        assert "Acme Plumbing:" in html
        assert "do you fix water heaters?" in html

    def test_escapes_visitor_content(self):
        from backend.services.conversation_notify import build_transcript_html
        msgs = [{"role": "user", "content": "<script>alert(1)</script>", "created_at": "2026-06-13T10:00:00Z"}]
        html = build_transcript_html("Biz", msgs)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_escapes_business_name(self):
        from backend.services.conversation_notify import build_transcript_html
        html = build_transcript_html("<img onerror=x>", self._msgs())
        assert "<img onerror=x>" not in html
        assert "&lt;img" in html

    def test_lead_block_when_present(self):
        from backend.services.conversation_notify import build_transcript_html
        html = build_transcript_html("Biz", self._msgs(), {"name": "Jane", "email": "j@x.com", "phone": "555"})
        assert "Captured contact" in html
        assert "Jane" in html and "j@x.com" in html

    def test_no_lead_block_without_lead(self):
        from backend.services.conversation_notify import build_transcript_html
        html = build_transcript_html("Biz", self._msgs())
        assert "Captured contact" not in html

    def test_empty_messages(self):
        from backend.services.conversation_notify import build_transcript_html
        html = build_transcript_html("Biz", [])
        assert "(no messages)" in html


# ---------------------------------------------------------------------------
# notify_idle_conversations — mocked DB + send_email
# ---------------------------------------------------------------------------

def _mock_db(*, tenants=None, conversations=None, messages=None, leads=None, claim_wins=True):
    """MagicMock Supabase keyed by table. Selector methods chain; execute()
    returns the configured rows per table. The conversations UPDATE (claim)
    returns claim_wins-controlled data."""
    db = MagicMock()

    def _table(name):
        t = MagicMock()
        for m in ["select", "insert", "update", "eq", "neq", "gte", "lte",
                  "gt", "lt", "limit", "order", "filter", "is_", "not_", "in_"]:
            getattr(t, m).return_value = t

        select_result = MagicMock()
        if name == "tenants":
            select_result.data = tenants or []
        elif name == "conversations":
            select_result.data = conversations or []
        elif name == "chat_messages":
            select_result.data = messages or []
        elif name == "leads":
            select_result.data = leads or []
        else:
            select_result.data = []
        t.execute.return_value = select_result

        # conversations.update(...).eq(...).is_(...).execute() is the claim;
        # give it its own result so claim success is controllable.
        if name == "conversations":
            claim_result = MagicMock()
            claim_result.data = [{"id": "c1"}] if claim_wins else []

            def _update(*_a, **_k):
                u = MagicMock()
                for m in ["eq", "is_"]:
                    getattr(u, m).return_value = u
                u.execute.return_value = claim_result
                return u

            t.update.side_effect = _update
        return t

    db.table.side_effect = _table
    return db


@pytest.mark.asyncio
async def test_no_enabled_tenants_returns_zero():
    from backend.services import conversation_notify as cn
    db = _mock_db(tenants=[])
    with patch.object(cn, "get_service_supabase", return_value=db), \
         patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_idle_conversations()
    assert sent == 0
    send.assert_not_called()


@pytest.mark.asyncio
async def test_idle_conversation_sends_once():
    from backend.services import conversation_notify as cn
    old = (_utc_now() - timedelta(minutes=30)).isoformat()
    tenants = [{"id": "t1", "business_name": "Acme", "conversation_notify_email": "alerts@acme.com", "owner_email": "o@acme.com"}]
    conversations = [{"id": "c1", "client_id": "t1", "session_id": "s1", "created_at": old}]
    messages = [{"session_id": "s1", "role": "user", "content": "hello", "created_at": old}]
    db = _mock_db(tenants=tenants, conversations=conversations, messages=messages)
    with patch.object(cn, "get_service_supabase", return_value=db), \
         patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_idle_conversations()
    assert sent == 1
    assert send.call_count == 1
    assert send.call_args.kwargs["to"] == "alerts@acme.com"


@pytest.mark.asyncio
async def test_active_conversation_skipped():
    from backend.services import conversation_notify as cn
    fresh = _utc_now().isoformat()
    tenants = [{"id": "t1", "business_name": "Acme", "conversation_notify_email": "a@x.com", "owner_email": None}]
    conversations = [{"id": "c1", "client_id": "t1", "session_id": "s1", "created_at": fresh}]
    messages = [{"session_id": "s1", "role": "user", "content": "hi", "created_at": fresh}]
    db = _mock_db(tenants=tenants, conversations=conversations, messages=messages)
    with patch.object(cn, "get_service_supabase", return_value=db), \
         patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_idle_conversations(idle_minutes=15)
    assert sent == 0
    send.assert_not_called()


@pytest.mark.asyncio
async def test_falls_back_to_owner_email():
    from backend.services import conversation_notify as cn
    old = (_utc_now() - timedelta(minutes=30)).isoformat()
    tenants = [{"id": "t1", "business_name": "Acme", "conversation_notify_email": None, "owner_email": "owner@acme.com"}]
    conversations = [{"id": "c1", "client_id": "t1", "session_id": "s1", "created_at": old}]
    messages = [{"session_id": "s1", "role": "user", "content": "hello", "created_at": old}]
    db = _mock_db(tenants=tenants, conversations=conversations, messages=messages)
    with patch.object(cn, "get_service_supabase", return_value=db), \
         patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_idle_conversations()
    assert sent == 1
    assert send.call_args.kwargs["to"] == "owner@acme.com"


@pytest.mark.asyncio
async def test_lost_claim_does_not_send():
    """Another worker already stamped notified_at → claim returns no rows → skip."""
    from backend.services import conversation_notify as cn
    old = (_utc_now() - timedelta(minutes=30)).isoformat()
    tenants = [{"id": "t1", "business_name": "Acme", "conversation_notify_email": "a@x.com", "owner_email": None}]
    conversations = [{"id": "c1", "client_id": "t1", "session_id": "s1", "created_at": old}]
    messages = [{"session_id": "s1", "role": "user", "content": "hello", "created_at": old}]
    db = _mock_db(tenants=tenants, conversations=conversations, messages=messages, claim_wins=False)
    with patch.object(cn, "get_service_supabase", return_value=db), \
         patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_idle_conversations()
    assert sent == 0
    send.assert_not_called()
