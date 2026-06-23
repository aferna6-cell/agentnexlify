"""Tests for the comp/100%-off checkout activation safety net in billing.py.

Covers the gap identified in GH #93 follow-up: when _handle_checkout_completed
is called for a session where _resolve_plan returns None (e.g. a no_payment_required
/ $0-coupon comped checkout with missing plan metadata), the handler must:
  1. Log a logger.error with session_id, customer, payment_status, and tenant_id.
  2. NOT activate the tenant (DB update must NOT be called with plan_status=active).
  3. Return None (same as the pre-existing no-plan path).

Also verifies the SUCCESS case: a no_payment_required session WITH a valid 'plan'
in metadata still activates normally (plan_status=active, returns activation dict).

All Stripe and DB calls are mocked — no live network calls.
Run with:
    .venv/bin/python -m pytest backend/tests/test_billing_comp_activation.py -v --noconftest
"""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing

_TENANT = "cccccccc-0000-0000-0000-000000000099"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capturing_db():
    """Mock Supabase client that records tenant update payloads."""
    db = MagicMock()
    captured = []

    def _update(payload):
        captured.append(payload)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": _TENANT}])
        return chain

    db.table.return_value.update.side_effect = _update
    return db, captured


def _make_comp_session(**overrides):
    """Stripe checkout session dict for a $0 / comped / 100%-off checkout."""
    base = {
        "id": "cs_test_comp_001",
        "customer": "cus_comp_test",
        "customer_email": "beta@example.com",
        "payment_status": "no_payment_required",
        "amount_total": 0,
        "metadata": {"tenant_id": _TENANT},  # plan key intentionally absent
        "subscription": None,
        "mode": "subscription",
        "status": "complete",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1: no_payment_required + no resolvable plan → logger.error + no activation
# ---------------------------------------------------------------------------

class TestCompNoResolvablePlan:
    """When payment_status=no_payment_required and plan is unresolvable, must log
    a logger.error and NOT activate the tenant."""

    def test_logs_error_with_session_id(self, caplog):
        """logger.error must include the session_id so it's greppable."""
        db, updates = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is None, "Must return None when plan is unresolvable"
        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert error_msgs, "Expected at least one ERROR log entry"
        combined = " ".join(error_msgs)
        assert "cs_test_comp_001" in combined, (
            f"session_id must appear in error log; got: {combined}"
        )

    def test_logs_error_with_customer(self, caplog):
        """logger.error must include the customer id."""
        db, _ = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            billing._handle_checkout_completed(db, session)

        combined = " ".join(r.message for r in caplog.records if r.levelno == logging.ERROR)
        assert "cus_comp_test" in combined, (
            f"customer must appear in error log; got: {combined}"
        )

    def test_logs_error_with_payment_status(self, caplog):
        """logger.error must include payment_status so no_payment_required sessions
        are identifiable in log searches."""
        db, _ = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            billing._handle_checkout_completed(db, session)

        combined = " ".join(r.message for r in caplog.records if r.levelno == logging.ERROR)
        assert "no_payment_required" in combined, (
            f"payment_status must appear in error log; got: {combined}"
        )

    def test_logs_error_with_tenant_id(self, caplog):
        """logger.error must include tenant_id so the affected tenant is identifiable."""
        db, _ = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            billing._handle_checkout_completed(db, session)

        combined = " ".join(r.message for r in caplog.records if r.levelno == logging.ERROR)
        assert _TENANT in combined, (
            f"tenant_id must appear in error log; got: {combined}"
        )

    def test_tenant_not_activated_on_no_plan(self):
        """DB update must NOT set plan_status=active when plan is unresolvable."""
        db, updates = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is None
        # Either no update was called, or no update with plan_status=active
        active_updates = [u for u in updates if u.get("plan_status") == "active"]
        assert not active_updates, (
            f"Must NOT update tenant with plan_status=active when plan is unresolvable. "
            f"Got: {updates}"
        )

    def test_returns_none_not_dict(self):
        """Return value must be None, not an activation dict."""
        db, _ = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is None

    def test_error_logged_even_when_tenant_id_is_none(self, caplog):
        """When both tenant and plan are None, the no-tenant branch fires first (not
        the no-plan branch).  No spurious activation in that case either."""
        db, updates = _capturing_db()
        session = _make_comp_session()

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=None),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.WARNING, logger="backend.routers.billing"),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is None
        active_updates = [u for u in updates if u.get("plan_status") == "active"]
        assert not active_updates


# ---------------------------------------------------------------------------
# Test 2: no_payment_required WITH valid plan → activates normally
# ---------------------------------------------------------------------------

class TestCompWithResolvablePlan:
    """A comped session that DOES have a valid 'plan' in metadata must activate
    normally — plan_status=active, returns activation dict, no spurious error log."""

    def test_activates_tenant_when_plan_present(self):
        """plan in metadata → tenant upgraded, activation dict returned."""
        db, updates = _capturing_db()
        session = _make_comp_session(
            metadata={"tenant_id": _TENANT, "plan": "agent_os"}
        )

        with (
            patch.object(billing, "guard_checkout_for_fraud", return_value=None),
            patch.object(billing, "log_activity"),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is not None, "Expected activation dict, got None"
        assert result["event"] == "activated"
        assert result["plan"] == "agent_os"
        assert result["tenant_id"] == _TENANT
        # amount_total is 0 for a comped session — that is correct
        assert result["amount_total"] == 0

    def test_no_error_log_when_plan_present(self, caplog):
        """No ERROR-level log when the comp session has a resolvable plan."""
        db, _ = _capturing_db()
        session = _make_comp_session(
            metadata={"tenant_id": _TENANT, "plan": "chatbot"}
        )

        with (
            patch.object(billing, "guard_checkout_for_fraud", return_value=None),
            patch.object(billing, "log_activity"),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is not None
        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert not error_msgs, (
            f"Unexpected ERROR logs on successful comp activation: {error_msgs}"
        )

    def test_plan_status_set_to_active(self):
        """DB update must set plan_status=active on successful comp activation."""
        db, updates = _capturing_db()
        session = _make_comp_session(
            metadata={"tenant_id": _TENANT, "plan": "agent_os"}
        )

        with (
            patch.object(billing, "guard_checkout_for_fraud", return_value=None),
            patch.object(billing, "log_activity"),
        ):
            billing._handle_checkout_completed(db, session)

        active_updates = [u for u in updates if u.get("plan_status") == "active"]
        assert active_updates, (
            f"Expected at least one update with plan_status=active; got: {updates}"
        )
        assert active_updates[-1]["plan"] == "agent_os"


# ---------------------------------------------------------------------------
# Test 3: Non-comp session (paid) with no resolvable plan — same error path
# ---------------------------------------------------------------------------

class TestPaidSessionNoResolvablePlan:
    """Paid sessions (payment_status=paid) with an unresolvable plan also log
    the error.  payment_status=no_payment_required is not special-cased — the
    logger.error fires for any unresolvable-plan checkout regardless of amount."""

    def test_paid_session_no_plan_logs_error(self, caplog):
        db, _ = _capturing_db()
        session = _make_comp_session(
            payment_status="paid",
            amount_total=9999,
            metadata={"tenant_id": _TENANT},  # no plan key
        )

        with (
            patch.object(billing, "_resolve_tenant_id", return_value=_TENANT),
            patch.object(billing, "_resolve_plan", return_value=None),
            caplog.at_level(logging.ERROR, logger="backend.routers.billing"),
        ):
            result = billing._handle_checkout_completed(db, session)

        assert result is None
        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert error_msgs, "logger.error must fire for any unresolvable-plan session"
