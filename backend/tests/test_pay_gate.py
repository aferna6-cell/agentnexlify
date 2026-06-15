"""Tests for pay-gate helpers - is_pay_gated and require_active_plan dependency.

Mirror mocking style from backend/tests/test_os_approval_notify.py.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.services.pay_gate import is_pay_gated, require_active_plan

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# is_pay_gated unit tests
# ---------------------------------------------------------------------------


def test_is_pay_gated_exempt_false_active():
    """Exempt tenant with active plan is not gated."""
    row = {"pay_gate_exempt": True, "plan_status": "active"}
    assert is_pay_gated(row) is False


def test_is_pay_gated_exempt_true_no_plan():
    """Exempt tenant with no plan is not gated - grandfathered."""
    row = {"pay_gate_exempt": True, "plan_status": None}
    assert is_pay_gated(row) is False


def test_is_pay_gated_active_plan():
    """Non-exempt tenant with active plan is not gated."""
    row = {"pay_gate_exempt": False, "plan_status": "active"}
    assert is_pay_gated(row) is False


def test_is_pay_gated_trialing_plan():
    """Non-exempt tenant on trial is not gated."""
    row = {"pay_gate_exempt": False, "plan_status": "trialing"}
    assert is_pay_gated(row) is False


def test_is_pay_gated_unpaid_non_exempt():
    """New tenant with no paid plan and not exempt is gated."""
    row = {"pay_gate_exempt": False, "plan_status": None}
    assert is_pay_gated(row) is True


def test_is_pay_gated_canceled_non_exempt():
    """Non-exempt tenant whose plan was canceled is gated."""
    row = {"pay_gate_exempt": False, "plan_status": "canceled"}
    assert is_pay_gated(row) is True


def test_is_pay_gated_past_due_non_exempt():
    """Non-exempt tenant past_due is gated."""
    row = {"pay_gate_exempt": False, "plan_status": "past_due"}
    assert is_pay_gated(row) is True


def test_is_pay_gated_missing_keys():
    """Missing keys default to not exempt and empty status - gated."""
    row = {}
    assert is_pay_gated(row) is True


# ---------------------------------------------------------------------------
# require_active_plan dependency tests
# ---------------------------------------------------------------------------


def _mock_db(pay_gate_exempt=False, plan_status=None, found=True):
    """Build a mock Supabase client that returns a tenant row."""
    db = MagicMock()
    tenants = MagicMock()
    if found:
        tenants.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": _TENANT, "pay_gate_exempt": pay_gate_exempt, "plan_status": plan_status}]
        )
    else:
        tenants.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
    db.table.return_value = tenants
    return db


_CLAIMS = {"tenant_id": _TENANT, "email": "owner@test.com", "plan": "free"}


@pytest.mark.asyncio
async def test_require_active_plan_passes_for_exempt():
    """Exempt tenant passes the gate without raising."""
    with patch("backend.services.pay_gate.get_service_supabase", return_value=_mock_db(pay_gate_exempt=True)):
        result = await require_active_plan(claims=_CLAIMS)
    assert result["tenant_id"] == _TENANT


@pytest.mark.asyncio
async def test_require_active_plan_passes_for_active():
    """Non-exempt active tenant passes the gate."""
    with patch("backend.services.pay_gate.get_service_supabase", return_value=_mock_db(pay_gate_exempt=False, plan_status="active")):
        result = await require_active_plan(claims=_CLAIMS)
    assert result["tenant_id"] == _TENANT


@pytest.mark.asyncio
async def test_require_active_plan_raises_402_for_unpaid_non_exempt():
    """Unpaid non-exempt tenant gets HTTP 402."""
    with patch("backend.services.pay_gate.get_service_supabase", return_value=_mock_db(pay_gate_exempt=False, plan_status=None)):
        with pytest.raises(HTTPException) as exc_info:
            await require_active_plan(claims=_CLAIMS)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "payment_required"
    assert exc_info.value.detail["upgrade_path"] == "/billing"


@pytest.mark.asyncio
async def test_require_active_plan_raises_404_when_tenant_missing():
    """Missing tenant row returns 404."""
    with patch("backend.services.pay_gate.get_service_supabase", return_value=_mock_db(found=False)):
        with pytest.raises(HTTPException) as exc_info:
            await require_active_plan(claims=_CLAIMS)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_require_active_plan_fails_open_on_db_error():
    """DB error fails open - does not block the user."""
    db = MagicMock()
    db.table.side_effect = RuntimeError("DB unavailable")
    with patch("backend.services.pay_gate.get_service_supabase", return_value=db):
        result = await require_active_plan(claims=_CLAIMS)
    # Fail open - returns claims so the user is not blocked
    assert result["tenant_id"] == _TENANT


@pytest.mark.asyncio
async def test_require_active_plan_fails_open_on_client_init_error():
    """Supabase client construction failure fails open, not 500.

    Regression: get_service_supabase() was called outside the try block, so a
    client-init failure (missing env, infra outage) propagated as a 500 and
    blocked the endpoint. The construction call must be inside the fail-open
    guard so an infra issue never gates a legitimate tenant.
    """
    with patch(
        "backend.services.pay_gate.get_service_supabase",
        side_effect=Exception("supabase_url is required"),
    ):
        result = await require_active_plan(claims=_CLAIMS)
    assert result["tenant_id"] == _TENANT
