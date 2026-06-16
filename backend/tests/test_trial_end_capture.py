"""Tests for stripe_trial_end capture in _handle_subscription_updated.

Covers:
- trial_end present: writes stripe_trial_end as ISO 8601 string.
- trial_end null/absent: writes stripe_trial_end as None (clears on conversion).
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing

_TENANT = "cccccccc-0000-0000-0000-000000000099"


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
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": _TENANT}]
    )
    return db, captured


def _make_subscription(**overrides):
    base = {
        "id": "sub_test_trial",
        "customer": "cus_test",
        "status": "trialing",
        "metadata": {"plan": "growth"},
        "trial_end": None,
    }
    base.update(overrides)
    return base


def test_trial_end_present_writes_iso_string():
    """When trial_end is a unix timestamp, stripe_trial_end is stored as ISO 8601."""
    db, updates = _capturing_db()
    # 2026-07-01 00:00:00 UTC
    trial_end_unix = 1751328000
    subscription = _make_subscription(trial_end=trial_end_unix)

    billing._handle_subscription_updated(db, subscription)

    assert updates, "Expected at least one DB update"
    payload = updates[-1]
    assert "stripe_trial_end" in payload, "stripe_trial_end must be in update payload"
    iso_val = payload["stripe_trial_end"]
    assert iso_val is not None, "stripe_trial_end must not be None when trial_end present"
    assert isinstance(iso_val, str), "stripe_trial_end must be a string (ISO 8601)"
    # Must be parseable as ISO and round-trip to the same unix second
    from datetime import datetime, timezone
    parsed = datetime.fromisoformat(iso_val)
    assert int(parsed.timestamp()) == trial_end_unix, (
        f"ISO string {iso_val!r} does not round-trip to {trial_end_unix}"
    )


def test_trial_end_null_writes_none():
    """When trial_end is null (trial converted), stripe_trial_end is set to None."""
    db, updates = _capturing_db()
    subscription = _make_subscription(trial_end=None)

    billing._handle_subscription_updated(db, subscription)

    assert updates, "Expected at least one DB update"
    payload = updates[-1]
    assert "stripe_trial_end" in payload, "stripe_trial_end must be in update payload"
    assert payload["stripe_trial_end"] is None, (
        "stripe_trial_end must be None when trial_end is null (clears after conversion)"
    )


def test_trial_end_absent_writes_none():
    """When trial_end key is absent from subscription, stripe_trial_end is set to None."""
    db, updates = _capturing_db()
    subscription = {
        "id": "sub_test_no_trial",
        "customer": "cus_test",
        "status": "active",
        "metadata": {"plan": "growth"},
        # trial_end key not present at all
    }

    billing._handle_subscription_updated(db, subscription)

    assert updates, "Expected at least one DB update"
    payload = updates[-1]
    assert "stripe_trial_end" in payload, "stripe_trial_end must be in update payload even when key absent"
    assert payload["stripe_trial_end"] is None, (
        "stripe_trial_end must be None when trial_end key is absent"
    )
