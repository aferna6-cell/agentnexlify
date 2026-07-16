"""Shared notification plumbing (notify_common).

Contract:
  1. IdempotencyGuard is at-most-once per key, treats empty key parts as
     never-deduped, bounds its memory, and resets cleanly.
  2. fetch_owner_alert_config returns the tenants row and degrades to {}
     on DB failure or missing row - never raises.
  3. safe_send_email / safe_send_sms swallow every provider failure.
  4. dispatch_owner_alert fires the email branch only with an owner_email
     and the SMS branch only when enabled AND a phone is set.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.notify_common import (
    IdempotencyGuard,
    dispatch_owner_alert,
    fetch_owner_alert_config,
    safe_send_email,
    safe_send_sms,
)

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


# --- IdempotencyGuard ---------------------------------------------------------
def test_guard_dedupes_second_call():
    g = IdempotencyGuard()
    assert g.seen(_TENANT, "lead-1") is False
    assert g.seen(_TENANT, "lead-1") is True


def test_guard_empty_key_part_never_dedupes():
    g = IdempotencyGuard()
    assert g.seen(_TENANT, "") is False
    assert g.seen(_TENANT, "") is False
    assert g.seen("", "lead-1") is False


def test_guard_reset_clears_tracking():
    g = IdempotencyGuard()
    g.seen(_TENANT, "lead-1")
    g.reset()
    assert g.seen(_TENANT, "lead-1") is False


def test_guard_bounds_memory():
    g = IdempotencyGuard(max_tracked=3)
    for i in range(3):
        g.seen(_TENANT, f"lead-{i}")
    # Cap reached: the set clears, so an old key reads as fresh again.
    assert g.seen(_TENANT, "lead-99") is False
    assert g.seen(_TENANT, "lead-0") is False


# --- fetch_owner_alert_config ---------------------------------------------------
def _db(rows):
    db = MagicMock()
    chain = MagicMock()
    for attr in ("select", "eq", "limit"):
        getattr(chain, attr).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    return db


def test_fetch_config_returns_row():
    cfg = {"business_name": "Acme", "owner_email": "o@acme.com"}
    got = fetch_owner_alert_config(lambda: _db([cfg]), _TENANT, "test_alert")
    assert got == cfg


def test_fetch_config_empty_on_no_rows_or_failure():
    assert fetch_owner_alert_config(lambda: _db([]), _TENANT, "test_alert") == {}

    def boom():
        raise RuntimeError("db down")

    assert fetch_owner_alert_config(boom, _TENANT, "test_alert") == {}


# --- safe senders ---------------------------------------------------------------
def test_safe_send_email_swallows_failure():
    failing = AsyncMock(side_effect=RuntimeError("resend down"))
    with patch("backend.services.email_sender.send_email", failing):
        asyncio.run(
            safe_send_email(
                tenant_id=_TENANT, to="o@a.com", subject="s",
                body_html="<p>b</p>", log_prefix="test_alert",
            )
        )
    failing.assert_awaited_once()


def test_safe_send_sms_swallows_failure():
    failing = AsyncMock(side_effect=RuntimeError("twilio down"))
    with patch("backend.services.twilio_service.send_sms", failing):
        asyncio.run(
            safe_send_sms(
                tenant_id=_TENANT, to="+15555550123", body="b", log_prefix="test_alert",
            )
        )
    failing.assert_awaited_once()


# --- dispatch branch logic --------------------------------------------------------
def _dispatch(config):
    email_fn = AsyncMock()
    sms_fn = AsyncMock()
    asyncio.run(
        dispatch_owner_alert(
            tenant_id=_TENANT, config=config,
            email_fn=email_fn, sms_fn=sms_fn, log_prefix="test_alert",
        )
    )
    return email_fn, sms_fn


def test_dispatch_fires_both_channels_when_configured():
    email_fn, sms_fn = _dispatch(
        {
            "business_name": "Acme",
            "owner_email": "o@acme.com",
            "notification_phone": "+15555550123",
            "sms_notifications_enabled": True,
        }
    )
    email_fn.assert_awaited_once_with("Acme", "o@acme.com")
    sms_fn.assert_awaited_once_with("Acme", "+15555550123")


def test_dispatch_skips_email_without_owner_email():
    email_fn, sms_fn = _dispatch(
        {
            "business_name": "Acme",
            "notification_phone": "+15555550123",
            "sms_notifications_enabled": True,
        }
    )
    email_fn.assert_not_awaited()
    sms_fn.assert_awaited_once()


def test_dispatch_skips_sms_when_disabled_or_phoneless():
    email_fn, sms_fn = _dispatch(
        {
            "business_name": "Acme",
            "owner_email": "o@acme.com",
            "notification_phone": "+15555550123",
            "sms_notifications_enabled": False,
        }
    )
    email_fn.assert_awaited_once()
    sms_fn.assert_not_awaited()

    email_fn, sms_fn = _dispatch(
        {"business_name": "Acme", "owner_email": "o@acme.com",
         "sms_notifications_enabled": True}
    )
    sms_fn.assert_not_awaited()


def test_dispatch_defaults_business_name():
    email_fn, _ = _dispatch({"owner_email": "o@acme.com"})
    email_fn.assert_awaited_once_with("your business", "o@acme.com")
