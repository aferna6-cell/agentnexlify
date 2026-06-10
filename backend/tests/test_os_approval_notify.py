"""Tests for owner notification on pending Agent OS approvals."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.services import os_approval_notify

_TENANT = "11111111-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _reset_throttle():
    os_approval_notify._last_sent.clear()
    yield
    os_approval_notify._last_sent.clear()


def _db(owner_email="owner@biz.com", pending_count=2):
    db = MagicMock()
    tenants = MagicMock()
    tenants.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"owner_email": owner_email, "owner_name": "Pat", "business_name": "Biz"}]
    )
    db.table.return_value = tenants
    return db


def _patch_runs(pending_count):
    runs = MagicMock()
    runs.select.return_value.eq.return_value.execute.return_value = MagicMock(
        count=pending_count
    )
    return patch.object(os_approval_notify, "tenant_table", return_value=runs)


@pytest.mark.asyncio
async def test_sends_email_with_pending_count():
    db = _db()
    with _patch_runs(3), patch.object(
        os_approval_notify, "send_email", new=AsyncMock()
    ) as mock_send:
        sent = await os_approval_notify.notify_pending_approval(
            db, _TENANT, agent_name="marketing", channel="email", title="Spring promo"
        )
    assert sent is True
    kwargs = mock_send.call_args.kwargs
    assert kwargs["to"] == "owner@biz.com"
    assert "3 waiting" in kwargs["subject"]
    assert "Spring promo" in kwargs["body_html"]
    assert kwargs["tenant_id"] == _TENANT


@pytest.mark.asyncio
async def test_throttle_suppresses_second_send():
    db = _db()
    with _patch_runs(1), patch.object(
        os_approval_notify, "send_email", new=AsyncMock()
    ) as mock_send:
        first = await os_approval_notify.notify_pending_approval(
            db, _TENANT, agent_name="sales", channel="sms", title=None
        )
        second = await os_approval_notify.notify_pending_approval(
            db, _TENANT, agent_name="sales", channel="sms", title=None
        )
    assert first is True and second is False
    assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_missing_owner_email_no_send():
    db = _db(owner_email=None)
    with _patch_runs(1), patch.object(
        os_approval_notify, "send_email", new=AsyncMock()
    ) as mock_send:
        sent = await os_approval_notify.notify_pending_approval(
            db, _TENANT, agent_name="sales", channel="sms", title=None
        )
    assert sent is False
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_db_failure_swallowed():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    sent = await os_approval_notify.notify_pending_approval(
        db, _TENANT, agent_name="sales", channel="sms", title=None
    )
    assert sent is False  # never raises — turn unaffected
