"""Tests for owner alert on new paid signup (Feature 5) and
subscription_activated activity log (Feature 3).

Covers:
- Clean activation returns activation dict, triggers owner notify, logs activity.
- Fraud-paused path returns None, does NOT notify owner, does NOT log subscription_activated.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing

_TENANT = "bbbbbbbb-0000-0000-0000-000000000042"


def _capturing_db(updates=None):
    """Mock Supabase client that records tenant update payloads."""
    db = MagicMock()
    captured = updates if updates is not None else []

    def _update(payload):
        captured.append(payload)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": _TENANT}])
        return chain

    db.table.return_value.update.side_effect = _update
    return db, captured


def _make_session(**overrides):
    base = {
        "id": "cs_test_alert",
        "metadata": {"tenant_id": _TENANT, "plan": "growth"},
        "customer": "cus_test",
        "customer_email": "owner@example.com",
        "subscription": "sub_test",
        "amount_total": 9900,
        "mode": "subscription",
        "status": "complete",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Feature 5 + Feature 3: clean activation path
# ---------------------------------------------------------------------------

def test_clean_activation_returns_dict_and_triggers_notify_and_logs():
    """Clean checkout returns activation dict, owner notify is awaited, activity logged."""
    db, updates = _capturing_db()
    session = _make_session()

    with (
        patch.object(billing, "guard_checkout_for_fraud", return_value=None),
        patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
        patch.object(billing, "_resolve_plan", return_value="growth"),
        patch.object(billing, "log_activity") as mock_log,
    ):
        result = billing._handle_checkout_completed(db, session)

    # Must return activation dict (not None)
    assert result is not None, "Expected activation dict, got None"
    assert result["event"] == "activated"
    assert result["plan"] == "growth"
    assert result["tenant_id"] == _TENANT
    assert result["amount_total"] == 9900
    assert result["customer_email"] == "owner@example.com"

    # Must log subscription_activated activity
    calls = [call.kwargs if call.kwargs else dict(zip(
        ["tenant_id", "activity_type", "description", "lead_id", "metadata"],
        call.args,
    )) for call in mock_log.call_args_list]
    activity_types = [c.get("activity_type") for c in calls]
    assert "subscription_activated" in activity_types, (
        f"Expected subscription_activated in log calls, got: {activity_types}"
    )


def test_owner_notify_is_awaited_on_clean_activation():
    """notify_new_paid_signup coroutine calls send_platform_email with correct args."""
    from backend.services import owner_alerts

    mock_send = AsyncMock(return_value={"success": True})
    with patch.object(owner_alerts, "send_platform_email", mock_send):
        asyncio.run(
            owner_alerts.notify_new_paid_signup(
                plan="growth",
                amount_total=9900,
                tenant_id=_TENANT,
                customer_email="owner@example.com",
            )
        )

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert "New paid signup" in call_kwargs["subject"]
    assert "growth" in call_kwargs["subject"]


# ---------------------------------------------------------------------------
# Fraud path: must NOT notify owner, must NOT log subscription_activated
# ---------------------------------------------------------------------------

def test_fraud_path_returns_none_no_notify_no_subscription_log():
    """Fraud-paused checkout returns None; owner NOT notified; subscription_activated NOT logged."""
    db, updates = _capturing_db()
    session = _make_session()

    with (
        patch.object(billing, "guard_checkout_for_fraud", return_value="velocity_exceeded"),
        patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
        patch.object(billing, "_resolve_plan", return_value="growth"),
        patch.object(billing, "log_activity") as mock_log,
    ):
        result = billing._handle_checkout_completed(db, session)

    # Must return None on fraud path
    assert result is None, f"Expected None on fraud path, got: {result}"

    # Must NOT have logged subscription_activated
    calls = [call.kwargs if call.kwargs else dict(zip(
        ["tenant_id", "activity_type", "description", "lead_id", "metadata"],
        call.args,
    )) for call in mock_log.call_args_list]
    activity_types = [c.get("activity_type") for c in calls]
    assert "subscription_activated" not in activity_types, (
        f"subscription_activated must not be logged on fraud path; got: {activity_types}"
    )

    # fraud_alert must still be logged
    assert "fraud_alert" in activity_types, (
        f"Expected fraud_alert to be logged; got: {activity_types}"
    )

    # DB update must set plan_status=paused (not active)
    assert updates, "DB should have been updated on fraud path"
    assert updates[-1]["plan_status"] == "paused"


def test_no_tenant_returns_none():
    """Missing tenant_id short-circuits with None."""
    db, _ = _capturing_db()
    session = _make_session()

    with (
        patch.object(billing, "_resolve_tenant_id", return_value=None),
        patch.object(billing, "_resolve_plan", return_value="growth"),
    ):
        result = billing._handle_checkout_completed(db, session)

    assert result is None


def test_no_plan_returns_none():
    """Missing plan short-circuits with None."""
    db, _ = _capturing_db()
    session = _make_session()

    with (
        patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
        patch.object(billing, "_resolve_plan", return_value=None),
    ):
        result = billing._handle_checkout_completed(db, session)

    assert result is None
