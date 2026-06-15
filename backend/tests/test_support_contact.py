"""Tests for the dashboard support contact form (email forwarding)."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import support


def test_contact_endpoint_stores_and_acks(client):
    with patch.object(support, "send_platform_email", AsyncMock(return_value={"success": True})):
        resp = client.post(
            "/api/v1/support/contact",
            json={"name": "Pat", "email": "p@x.com", "message": "hello there"},
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_email_support_message_forwards_to_owner():
    sender = AsyncMock(return_value={"success": True})
    with patch.object(support, "send_platform_email", sender):
        await support._email_support_message("Pat", "p@x.com", "line1\nline2")
    kwargs = sender.call_args.kwargs
    assert "Pat" in kwargs["body_html"]
    assert "p@x.com" in kwargs["body_html"]
    assert "line1<br>line2" in kwargs["body_html"]
    assert kwargs["reply_to"] == "p@x.com"


@pytest.mark.asyncio
async def test_email_support_message_swallows_errors():
    with patch.object(support, "send_platform_email", AsyncMock(side_effect=RuntimeError("down"))):
        # Never raises — background task safety.
        await support._email_support_message("Pat", "p@x.com", "x")
