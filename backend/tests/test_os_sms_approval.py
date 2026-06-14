"""Tests for approve-by-text (os_sms_approval).

Contract: an exact keyword SMS from the tenant's own notification_phone
acts on the newest pending draft; everything else returns None so the
normal inbound bridge handles it.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.services import os_sms_approval

_TENANT = "11111111-0000-0000-0000-000000000001"
_OWNER_PHONE = "+15551230000"


def _db(
    *,
    notification_phone=_OWNER_PHONE,
    sms_enabled=True,
    pending_runs=None,
):
    db = MagicMock()
    tenants = MagicMock()
    tenants.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{
            "notification_phone": notification_phone,
            "sms_notifications_enabled": sms_enabled,
            "business_name": "Biz",
        }]
    )
    db.table.return_value = tenants
    return db


def _patch_runs(pending_runs):
    runs = MagicMock()
    runs.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=pending_runs
    )
    runs.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
    return runs


_PENDING_RUN = {
    "id": "run-1",
    "deliverable_status": "pending_approval",
    "action_type": "sms.send",
    "deliverable": {"title": "Callback text for Jamie"},
}


@pytest.mark.asyncio
async def test_yes_from_owner_approves_and_dispatches():
    db = _db()
    runs = _patch_runs([_PENDING_RUN])
    with patch.object(os_sms_approval, "tenant_table", return_value=runs), patch.object(
        os_sms_approval, "queue_action_for_run", new=AsyncMock(return_value="ar-1")
    ) as mock_queue:
        reply = await os_sms_approval.handle_owner_sms(db, _TENANT, _OWNER_PHONE, "YES")
    assert reply is not None
    assert "Callback text for Jamie" in reply
    mock_queue.assert_awaited_once()
    update_payload = runs.update.call_args.args[0]
    assert update_payload["deliverable_status"] == "approved"
    assert update_payload["action_run_id"] == "ar-1"


@pytest.mark.asyncio
async def test_no_from_owner_rejects_without_dispatch():
    db = _db()
    runs = _patch_runs([_PENDING_RUN])
    with patch.object(os_sms_approval, "tenant_table", return_value=runs), patch.object(
        os_sms_approval, "queue_action_for_run", new=AsyncMock()
    ) as mock_queue:
        reply = await os_sms_approval.handle_owner_sms(db, _TENANT, _OWNER_PHONE, "no")
    assert reply is not None
    assert "Dismissed" in reply
    mock_queue.assert_not_awaited()
    assert runs.update.call_args.args[0]["deliverable_status"] == "rejected"


@pytest.mark.asyncio
async def test_non_command_falls_through():
    db = _db()
    reply = await os_sms_approval.handle_owner_sms(
        db, _TENANT, _OWNER_PHONE, "Can you book me for Tuesday?"
    )
    assert reply is None


@pytest.mark.asyncio
async def test_command_from_customer_phone_falls_through():
    db = _db()
    runs = _patch_runs([_PENDING_RUN])
    with patch.object(os_sms_approval, "tenant_table", return_value=runs):
        reply = await os_sms_approval.handle_owner_sms(
            db, _TENANT, "+15559998888", "YES"
        )
    assert reply is None


@pytest.mark.asyncio
async def test_sms_disabled_falls_through():
    db = _db(sms_enabled=False)
    reply = await os_sms_approval.handle_owner_sms(db, _TENANT, _OWNER_PHONE, "YES")
    assert reply is None


@pytest.mark.asyncio
async def test_no_pending_drafts_gets_friendly_reply():
    db = _db()
    runs = _patch_runs([])
    with patch.object(os_sms_approval, "tenant_table", return_value=runs):
        reply = await os_sms_approval.handle_owner_sms(db, _TENANT, _OWNER_PHONE, "YES")
    assert reply is not None
    assert "Nothing" in reply


@pytest.mark.asyncio
async def test_db_failure_falls_through():
    db = MagicMock()
    db.table.side_effect = RuntimeError("supabase down")
    reply = await os_sms_approval.handle_owner_sms(db, _TENANT, _OWNER_PHONE, "YES")
    assert reply is None
