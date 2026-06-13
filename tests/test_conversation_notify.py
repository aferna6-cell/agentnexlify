"""Tests for new-conversation email notifications
(backend/services/conversation_notify.py).

Covers:
  - build_new_conversation_html: copy, HTML escaping (XSS), first-message block
  - notify_new_conversation: opt-out skip, configured-address send, owner_email
    fallback, no-destination skip, send failure never raises
"""

import os
os.environ["TESTING"] = "1"
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# build_new_conversation_html — pure function
# ---------------------------------------------------------------------------

class TestBuildNewConversationHtml:
    def test_announces_new_conversation(self):
        from backend.services.conversation_notify import build_new_conversation_html
        html = build_new_conversation_html("Acme Plumbing", "Do you fix water heaters?")
        assert "new conversation" in html.lower()
        assert "Acme Plumbing" in html
        assert "Do you fix water heaters?" in html

    def test_escapes_first_message(self):
        from backend.services.conversation_notify import build_new_conversation_html
        html = build_new_conversation_html("Biz", "<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_escapes_business_name(self):
        from backend.services.conversation_notify import build_new_conversation_html
        html = build_new_conversation_html("<img onerror=x>", "hi")
        assert "<img onerror=x>" not in html
        assert "&lt;img" in html

    def test_no_message_block_when_blank(self):
        from backend.services.conversation_notify import build_new_conversation_html
        html = build_new_conversation_html("Biz", "   ")
        assert "First message" not in html

    def test_has_inbox_link(self):
        from backend.services.conversation_notify import build_new_conversation_html
        html = build_new_conversation_html("Biz", "hi")
        assert "/dashboard/conversations" in html


# ---------------------------------------------------------------------------
# notify_new_conversation — mocked send_email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skips_when_not_enabled():
    from backend.services import conversation_notify as cn
    tenant = {"id": "t1", "business_name": "Acme", "owner_email": "o@acme.com",
              "conversation_email_notify_enabled": False, "conversation_notify_email": "a@x.com"}
    with patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_new_conversation(tenant, "hello")
    assert sent is False
    send.assert_not_called()


@pytest.mark.asyncio
async def test_sends_to_configured_address():
    from backend.services import conversation_notify as cn
    tenant = {"id": "t1", "business_name": "Acme", "owner_email": "o@acme.com",
              "conversation_email_notify_enabled": True, "conversation_notify_email": "alerts@acme.com"}
    with patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_new_conversation(tenant, "hello")
    assert sent is True
    assert send.call_count == 1
    assert send.call_args.kwargs["to"] == "alerts@acme.com"
    assert send.call_args.kwargs["tenant_id"] == "t1"


@pytest.mark.asyncio
async def test_falls_back_to_owner_email():
    from backend.services import conversation_notify as cn
    tenant = {"id": "t1", "business_name": "Acme", "owner_email": "owner@acme.com",
              "conversation_email_notify_enabled": True, "conversation_notify_email": None}
    with patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_new_conversation(tenant, "hello")
    assert sent is True
    assert send.call_args.kwargs["to"] == "owner@acme.com"


@pytest.mark.asyncio
async def test_skips_when_no_destination():
    from backend.services import conversation_notify as cn
    tenant = {"id": "t1", "business_name": "Acme", "owner_email": None,
              "conversation_email_notify_enabled": True, "conversation_notify_email": None}
    with patch.object(cn, "send_email", new_callable=AsyncMock) as send:
        sent = await cn.notify_new_conversation(tenant, "hello")
    assert sent is False
    send.assert_not_called()


@pytest.mark.asyncio
async def test_send_failure_never_raises():
    from backend.services import conversation_notify as cn
    tenant = {"id": "t1", "business_name": "Acme", "owner_email": None,
              "conversation_email_notify_enabled": True, "conversation_notify_email": "a@x.com"}
    with patch.object(cn, "send_email", new_callable=AsyncMock, side_effect=RuntimeError("smtp down")) as send:
        sent = await cn.notify_new_conversation(tenant, "hello")
    assert sent is False
    send.assert_called_once()
