"""Tests for the Agent OS fail/abstain platform-owner alert."""

import base64
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import os_failure_notify

_CLIENT = "11111111-0000-0000-0000-000000000001"
_THREAD = "thread-abc"


@pytest.fixture(autouse=True)
def _reset_throttle():
    os_failure_notify._last_sent.clear()
    yield
    os_failure_notify._last_sent.clear()


def _db(messages):
    db = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        MagicMock(data=messages)
    )
    return db, table


def test_build_transcript_orders_and_labels():
    out = os_failure_notify.build_transcript(
        [
            {"role": "user", "content": "help me", "created_at": "t1"},
            {"role": "assistant", "content": "no", "created_at": "t2"},
        ]
    )
    assert "USER" in out and "ASSISTANT" in out
    assert "help me" in out and out.index("help me") < out.index("no")


@pytest.mark.asyncio
async def test_alert_emails_owner_with_transcript_attached():
    msgs = [
        {"role": "user", "content": "I need a quote", "created_at": "t1"},
        {"role": "assistant", "content": "Run failed: boom", "created_at": "t2"},
    ]
    db, table = _db(msgs)
    sender = AsyncMock(return_value={"success": True})
    with patch.object(os_failure_notify, "tenant_table", return_value=table), \
            patch.object(os_failure_notify, "send_platform_email", sender):
        sent = await os_failure_notify.notify_agent_failure(
            db, _CLIENT, _THREAD, "failed", "Acme Co"
        )
    assert sent is True
    kwargs = sender.call_args.kwargs
    assert "failed" in kwargs["subject"] and "Acme Co" in kwargs["subject"]
    att = kwargs["attachments"][0]
    transcript = base64.b64decode(att["content"]).decode("utf-8")
    assert "I need a quote" in transcript
    # Last customer message surfaced in the body.
    assert "I need a quote" in kwargs["body_html"]


@pytest.mark.asyncio
async def test_throttle_suppresses_second_alert_same_thread():
    db, table = _db([{"role": "user", "content": "x", "created_at": "t1"}])
    sender = AsyncMock(return_value={"success": True})
    with patch.object(os_failure_notify, "tenant_table", return_value=table), \
            patch.object(os_failure_notify, "send_platform_email", sender):
        first = await os_failure_notify.notify_agent_failure(
            db, _CLIENT, _THREAD, "wishlist_fallback"
        )
        second = await os_failure_notify.notify_agent_failure(
            db, _CLIENT, _THREAD, "wishlist_fallback"
        )
    assert first is True and second is False
    assert sender.call_count == 1


@pytest.mark.asyncio
async def test_db_failure_swallowed():
    db = MagicMock()
    with patch.object(
        os_failure_notify, "tenant_table", side_effect=RuntimeError("db down")
    ):
        sent = await os_failure_notify.notify_agent_failure(
            db, _CLIENT, _THREAD, "failed"
        )
    assert sent is False  # never raises — turn unaffected
