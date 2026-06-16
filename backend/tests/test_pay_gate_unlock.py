"""Money-path unlock test: a completed Stripe checkout opens the pay-gate.

Proves the loop the pay-gate depends on: checkout.session.completed ->
tenant row flips to plan_status="active" -> is_pay_gated() returns False.
This is the backend half of launch smoke #1 (the card-entry half is manual,
see docs/ops/paid-signup-smoke.md - Stripe Checkout is a third-party redirect
that can't be driven hermetically).
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing
from backend.services.pay_gate import is_pay_gated

_TENANT = "aaaaaaaa-0000-0000-0000-000000000099"


def _capturing_db(updates):
    """Mock Supabase client that records every tenants.update() payload."""
    db = MagicMock()

    def _update(payload):
        updates.append(payload)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": _TENANT}])
        return chain

    db.table.return_value.update.side_effect = _update
    return db


def test_completed_checkout_activates_plan_and_opens_gate():
    """A clean (non-fraud) checkout writes plan_status='active' and the gate opens."""
    updates = []
    db = _capturing_db(updates)
    session = {
        "id": "cs_test_unlock",
        "metadata": {"tenant_id": _TENANT, "plan": "chatbot"},
        "customer": "cus_test",
        "subscription": "sub_test",
        "amount_total": 1999,
        "mode": "subscription",
        "status": "complete",
    }

    # guard_checkout_for_fraud has its own coverage; here we assert the clean path.
    with patch.object(billing, "guard_checkout_for_fraud", return_value=None), \
         patch.object(billing, "_resolve_tenant_id", return_value=_TENANT), \
         patch.object(billing, "_resolve_plan", return_value="chatbot"):
        billing._handle_checkout_completed(db, session)

    assert updates, "checkout handler did not write any tenant update"
    activation = updates[-1]
    assert activation["plan"] == "chatbot"
    assert activation["plan_status"] == "active"

    # The row the webhook just wrote must clear the gate for a non-exempt tenant.
    row = {"pay_gate_exempt": False, "plan_status": activation["plan_status"]}
    assert is_pay_gated(row) is False


def test_unpaid_tenant_is_gated_before_checkout():
    """Sanity bookend: the same tenant is gated until the webhook lands."""
    row = {"pay_gate_exempt": False, "plan_status": None}
    assert is_pay_gated(row) is True
