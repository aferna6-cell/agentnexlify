"""Tests for the gmail.reply Agent OS action handler.

Covers the approve-a-draft send path that inbox_triage's drafts-only mode
depends on: a structured deliverable (written by inbox_triage) is sent via
gmail_connector.send_reply on approval, with clean failures when the draft
is malformed, Gmail is disconnected, or the send fails.
"""

import asyncio
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")

from backend.services.os_actions import gmail_reply
from backend.services.os_actions.base import ActionContext

_CLIENT = "11111111-1111-1111-1111-111111111111"


def _ctx(deliverable):
    return ActionContext(
        db=MagicMock(),
        client_id=_CLIENT,
        deliverable_id="deliv-1",
        action_run_id="run-1",
        action_type="gmail.reply",
        deliverable=deliverable,
        agent_run={},
    )


def _draft(**overrides):
    deliverable = {
        "body": "Thanks for reaching out!\n\nWe open at 9am.",
        "metadata": {
            "gmail_thread_id": "thread-123",
            "to": "customer@example.com",
            "subject": "Re: Opening hours",
            "in_reply_to": "<msg-1@mail.example.com>",
            "references": "<msg-1@mail.example.com>",
        },
    }
    deliverable.update(overrides)
    return deliverable


def test_registered_in_action_registry():
    from backend.services.os_actions import get_action

    spec = get_action("gmail.reply")
    assert spec is not None
    assert spec.name == "gmail.reply"


def test_success_sends_threaded_reply():
    send = MagicMock(return_value={"success": True, "message_id": "m-9", "detail": "sent"})
    with patch.object(gmail_reply.gmail_connector, "is_connected", return_value=True), \
         patch.object(gmail_reply.gmail_connector, "send_reply", send):
        result = asyncio.run(gmail_reply._run(_ctx(_draft())))

    assert result.status == "succeeded"
    assert result.response_payload["provider"] == "gmail"
    assert result.response_payload["message_id"] == "m-9"
    kwargs = send.call_args.kwargs
    assert kwargs["thread_id"] == "thread-123"
    assert kwargs["to"] == "customer@example.com"
    assert kwargs["in_reply_to"] == "<msg-1@mail.example.com>"
    assert "<p>" in kwargs["body_html"]


def test_missing_fields_fails_without_send():
    send = MagicMock()
    with patch.object(gmail_reply.gmail_connector, "is_connected", return_value=True), \
         patch.object(gmail_reply.gmail_connector, "send_reply", send):
        result = asyncio.run(
            gmail_reply._run(_ctx(_draft(metadata={"to": "", "gmail_thread_id": ""})))
        )

    assert result.status == "failed"
    assert result.error_detail["stage"] == "validate"
    send.assert_not_called()


def test_not_connected_fails_without_send():
    send = MagicMock()
    with patch.object(gmail_reply.gmail_connector, "is_connected", return_value=False), \
         patch.object(gmail_reply.gmail_connector, "send_reply", send):
        result = asyncio.run(gmail_reply._run(_ctx(_draft())))

    assert result.status == "failed"
    assert result.error_detail["stage"] == "gmail"
    send.assert_not_called()


def test_send_failure_reported():
    send = MagicMock(return_value={"success": False, "detail": "gmail api error 403"})
    with patch.object(gmail_reply.gmail_connector, "is_connected", return_value=True), \
         patch.object(gmail_reply.gmail_connector, "send_reply", send):
        result = asyncio.run(gmail_reply._run(_ctx(_draft())))

    assert result.status == "failed"
    assert result.error_detail["message"] == "gmail api error 403"


def test_send_exception_reported():
    with patch.object(gmail_reply.gmail_connector, "is_connected", return_value=True), \
         patch.object(gmail_reply.gmail_connector, "send_reply", side_effect=RuntimeError("boom")):
        result = asyncio.run(gmail_reply._run(_ctx(_draft())))

    assert result.status == "failed"
    assert result.error_detail["stage"] == "gmail"
