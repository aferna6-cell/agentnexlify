"""Agency/reseller partner inquiry endpoint (2026-08-25).

Contract:
  - Valid inquiry emails the owner (platform mailer) and returns 200.
  - Honeypot field filled -> silently accepted, NO email (bot learns nothing).
  - Mailer failure never surfaces to the prospect (still 200).
  - User-supplied fields are HTML-escaped in the owner email.

Run: pytest backend/tests/test_partners_inquiry.py --noconftest
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("TESTING", "1")

from backend.routers.partners import PartnerInquiryRequest, partner_inquiry


def _run(coro):
    return asyncio.run(coro)


def _body(**overrides):
    data = {
        "agency_name": "Shoreline Digital",
        "contact_name": "Sam Rivera",
        "email": "sam@shorelinedigital.com",
        "client_count": "12",
        "message": "We manage salons and HVAC companies in CT.",
        "website": "",
    }
    data.update(overrides)
    return PartnerInquiryRequest(**data)


def _request():
    req = MagicMock()
    req.client.host = "203.0.113.9"
    return req


class TestPartnerInquiry:
    def test_valid_inquiry_emails_owner(self):
        send_mock = AsyncMock(return_value={"success": True})
        with patch("backend.routers.partners.send_platform_email", send_mock):
            out = _run(partner_inquiry.__wrapped__(_request(), _body()))
        assert out == {"status": "received"}
        send_mock.assert_called_once()
        kwargs = send_mock.call_args.kwargs
        assert "Shoreline Digital" in kwargs["subject"]
        assert "sam@shorelinedigital.com" in kwargs["body_html"]
        assert "12" in kwargs["body_html"]

    def test_honeypot_drops_silently(self):
        send_mock = AsyncMock()
        with patch("backend.routers.partners.send_platform_email", send_mock):
            out = _run(
                partner_inquiry.__wrapped__(
                    _request(), _body(website="https://spam.example")
                )
            )
        assert out == {"status": "received"}  # bot sees success
        send_mock.assert_not_called()  # owner sees nothing

    def test_mailer_failure_still_returns_received(self):
        send_mock = AsyncMock(side_effect=RuntimeError("resend down"))
        with patch("backend.routers.partners.send_platform_email", send_mock):
            out = _run(partner_inquiry.__wrapped__(_request(), _body()))
        assert out == {"status": "received"}

    def test_html_is_escaped(self):
        send_mock = AsyncMock(return_value={"success": True})
        with patch("backend.routers.partners.send_platform_email", send_mock):
            _run(
                partner_inquiry.__wrapped__(
                    _request(),
                    _body(
                        agency_name="Bad<script>alert(1)</script>Co",
                        message="<img src=x onerror=alert(1)>",
                    ),
                )
            )
        body_html = send_mock.call_args.kwargs["body_html"]
        assert "<script>" not in body_html
        assert "&lt;script&gt;" in body_html
        assert "<img" not in body_html

    def test_email_validation_rejects_garbage(self):
        import pytest

        with pytest.raises(Exception):
            _body(email="not-an-email")
