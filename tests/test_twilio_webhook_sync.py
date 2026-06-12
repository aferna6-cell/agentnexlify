"""Tests for the Twilio phone-number webhook auto-sync job.

Contract: every number on the account ends up pointing at this backend's
voice/incoming, voice/call-status, and os/inbound/sms webhooks; numbers
already correct are not touched; missing creds or non-HTTPS api_url skip
the sync entirely.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.twilio_webhook_sync import (
    desired_webhooks,
    sync_twilio_number_webhooks,
)

_BASE = "https://agentnexlify-production.up.railway.app"


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeAsyncClient:
    """Records GET/POST calls; serves queued list pages on GET."""

    def __init__(self, pages):
        self._pages = list(pages)
        self.get_calls = []
        self.post_calls = []

    def __call__(self, *a, **kw):  # so patch(..., new=instance) constructor works
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kw):
        self.get_calls.append(url)
        return _FakeResponse(self._pages.pop(0))

    async def post(self, url, data=None, **kw):
        self.post_calls.append((url, data))
        return _FakeResponse({})


def _number(sid, phone, *, correct=False):
    desired = desired_webhooks()
    if correct:
        return {
            "sid": sid,
            "phone_number": phone,
            "voice_url": desired["VoiceUrl"],
            "voice_method": "POST",
            "status_callback": desired["StatusCallback"],
            "status_callback_method": "POST",
            "sms_url": desired["SmsUrl"],
            "sms_method": "POST",
        }
    return {
        "sid": sid,
        "phone_number": phone,
        "voice_url": "",
        "voice_method": "POST",
        "status_callback": "",
        "status_callback_method": "POST",
        "sms_url": "",
        "sms_method": "POST",
    }


def _settings_patches(**overrides):
    values = {
        "twilio_account_sid": "AC123",
        "twilio_auth_token": "tok",
        "twilio_webhook_sync_enabled": True,
        "api_url": _BASE,
    }
    values.update(overrides)
    return [
        patch(f"backend.services.twilio_webhook_sync.settings.{name}", value)
        for name, value in values.items()
    ]


def test_desired_webhooks_shape():
    desired = desired_webhooks_with_base()
    assert desired["VoiceUrl"].endswith("/api/v1/calls/voice/incoming")
    assert desired["StatusCallback"].endswith("/api/v1/calls/voice/call-status")
    assert desired["SmsUrl"].endswith("/api/v1/os/inbound/sms")
    assert desired["VoiceMethod"] == desired["SmsMethod"] == "POST"


def desired_webhooks_with_base():
    patches = _settings_patches()
    for p in patches:
        p.start()
    try:
        return desired_webhooks()
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_updates_only_drifted_numbers():
    fake = _FakeAsyncClient(
        pages=[{
            "incoming_phone_numbers": [
                _number("PN_ok", "+15550001", correct=True),
                _number("PN_drift", "+15550002"),
            ],
            "next_page_uri": None,
        }]
    )
    patches = _settings_patches()
    for p in patches:
        p.start()
    try:
        with patch("backend.services.twilio_webhook_sync.httpx.AsyncClient", new=fake):
            result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()

    assert result == {"checked": 2, "updated": 1, "failed": 0}
    assert len(fake.post_calls) == 1
    url, data = fake.post_calls[0]
    assert "PN_drift" in url
    assert data["VoiceUrl"] == f"{_BASE}/api/v1/calls/voice/incoming"
    assert data["StatusCallback"] == f"{_BASE}/api/v1/calls/voice/call-status"
    assert data["SmsUrl"] == f"{_BASE}/api/v1/os/inbound/sms"


@pytest.mark.asyncio
async def test_paginates_account_numbers():
    fake = _FakeAsyncClient(
        pages=[
            {
                "incoming_phone_numbers": [_number("PN_a", "+15550001", correct=True)],
                "next_page_uri": "/2010-04-01/Accounts/AC123/IncomingPhoneNumbers.json?Page=1",
            },
            {
                "incoming_phone_numbers": [_number("PN_b", "+15550002", correct=True)],
                "next_page_uri": None,
            },
        ]
    )
    patches = _settings_patches()
    for p in patches:
        p.start()
    try:
        with patch("backend.services.twilio_webhook_sync.httpx.AsyncClient", new=fake):
            result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()

    assert result == {"checked": 2, "updated": 0, "failed": 0}
    assert len(fake.get_calls) == 2


@pytest.mark.asyncio
async def test_skips_without_credentials():
    patches = _settings_patches(twilio_account_sid="")
    for p in patches:
        p.start()
    try:
        result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()
    assert result == {"skipped": "twilio_unconfigured"}


@pytest.mark.asyncio
async def test_skips_when_disabled():
    patches = _settings_patches(twilio_webhook_sync_enabled=False)
    for p in patches:
        p.start()
    try:
        result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()
    assert result == {"skipped": "disabled"}


@pytest.mark.asyncio
async def test_skips_non_https_base_url():
    patches = _settings_patches(api_url="http://localhost:8000")
    for p in patches:
        p.start()
    try:
        result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()
    assert result == {"skipped": "api_url_not_https"}


@pytest.mark.asyncio
async def test_listing_failure_never_raises():
    class _Boom:
        def __call__(self, *a, **kw):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, *a, **kw):
            raise RuntimeError("twilio down")

    patches = _settings_patches()
    for p in patches:
        p.start()
    try:
        with patch("backend.services.twilio_webhook_sync.httpx.AsyncClient", new=_Boom()):
            result = await sync_twilio_number_webhooks()
    finally:
        for p in patches:
            p.stop()
    assert result["error"] == "list_failed"
