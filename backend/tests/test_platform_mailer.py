"""Tests for the platform-owner transactional mailer."""

import base64
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import platform_mailer


def test_text_attachment_is_base64():
    att = platform_mailer.text_attachment("conv.txt", "hello world")
    assert att["filename"] == "conv.txt"
    assert base64.b64decode(att["content"]).decode("utf-8") == "hello world"


@pytest.mark.asyncio
async def test_skips_when_recipient_unset():
    with patch.object(platform_mailer.settings, "platform_support_email", ""):
        result = await platform_mailer.send_platform_email("s", "<p>b</p>")
    assert result["success"] is False
    assert "platform_support_email" in result["detail"]


@pytest.mark.asyncio
async def test_skips_when_resend_key_unset():
    with patch.object(platform_mailer.settings, "platform_support_email", "me@x.com"), \
            patch.object(platform_mailer.settings, "resend_api_key", ""):
        result = await platform_mailer.send_platform_email("s", "<p>b</p>")
    assert result["success"] is False
    assert "resend_api_key" in result["detail"]


@pytest.mark.asyncio
async def test_success_path_sends_to_owner_with_attachment():
    fake = MagicMock(return_value={"id": "re_123"})
    with patch.object(platform_mailer.settings, "platform_support_email", "owner@x.com"), \
            patch.object(platform_mailer.settings, "resend_api_key", "re_key"), \
            patch.object(platform_mailer.resend.Emails, "send", fake):
        att = platform_mailer.text_attachment("c.txt", "transcript")
        result = await platform_mailer.send_platform_email(
            "Subject", "<p>body</p>", attachments=[att], reply_to="reply@x.com"
        )
    assert result["success"] is True
    assert result["resend_id"] == "re_123"
    params = fake.call_args.args[0]
    assert params["to"] == ["owner@x.com"]
    assert params["subject"] == "Subject"
    assert params["reply_to"] == "reply@x.com"
    assert params["attachments"][0]["filename"] == "c.txt"


@pytest.mark.asyncio
async def test_send_failure_swallowed():
    def boom(_):
        raise RuntimeError("resend down")

    with patch.object(platform_mailer.settings, "platform_support_email", "owner@x.com"), \
            patch.object(platform_mailer.settings, "resend_api_key", "re_key"), \
            patch.object(platform_mailer.resend.Emails, "send", boom):
        result = await platform_mailer.send_platform_email("s", "<p>b</p>")
    assert result["success"] is False
