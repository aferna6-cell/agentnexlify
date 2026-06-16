"""Trial-expiry + dunning access contract (locked-immediately policy).

Pins the access policy chosen 2026-06-16:
- trialing / active  -> NOT pay-gated (dashboard unlocked)
- past_due / paused  -> pay-gated (locked the instant a charge fails)
- recovery (a later successful payment) restores access from EITHER locked
  status, deterministically, regardless of which webhook wrote the lock.

Why this file exists: the 7-day trial (PR #299) makes trial-end the first real
charge for every new paid tenant. These tests lock the behavior so a future
edit can't silently flip the policy or reintroduce the order-dependent recovery
bug where invoice.payment_failed wrote "paused" but customer.subscription.updated
overwrote it with "past_due", stranding a recovered tenant in past_due.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import billing
from backend.services.pay_gate import is_pay_gated

_CUSTOMER = "cus_trialtest"
_TENANT = "cccccccc-0000-0000-0000-000000000007"


# ---------------------------------------------------------------------------
# Pay-gate status contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "plan_status,expected_gated",
    [
        ("trialing", False),   # inside the 7-day trial -> unlocked
        ("active", False),     # paying -> unlocked
        ("past_due", True),    # first charge failed (subscription event) -> locked
        ("paused", True),      # first charge failed (invoice event) -> locked
        ("canceled", True),    # ended -> locked
        ("", True),            # never subscribed -> locked
    ],
)
def test_pay_gate_status_contract(plan_status, expected_gated):
    row = {"pay_gate_exempt": False, "plan_status": plan_status}
    assert is_pay_gated(row) is expected_gated


def test_exempt_tenant_never_gated_even_when_past_due():
    """Grandfathered tenants stay unlocked regardless of billing status."""
    assert is_pay_gated({"pay_gate_exempt": True, "plan_status": "past_due"}) is False


# ---------------------------------------------------------------------------
# Deterministic recovery: a successful payment restores access from EITHER
# locked status when the tenant was locked BY dunning (attempt_count > 0).
# ---------------------------------------------------------------------------

def _recovery_db(plan_status, dunning_count):
    """Mock supabase for _handle_payment_succeeded; captures the update payload."""
    captured = {}

    select_chain = MagicMock()
    select_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(
            data=[{
                "id": _TENANT,
                "plan_status": plan_status,
                "billing_dunning_attempt_count": dunning_count,
            }]
        )
    )

    def _update(payload):
        captured.update(payload)
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": _TENANT}])
        return chain

    select_chain.update.side_effect = _update
    db = MagicMock()
    db.table.return_value = select_chain
    return db, captured


@pytest.mark.asyncio
@pytest.mark.parametrize("locked_status", ["paused", "past_due"])
async def test_payment_recovery_restores_from_either_locked_status(locked_status):
    """A recovered card un-gates the tenant whether it was paused OR past_due."""
    db, captured = _recovery_db(locked_status, dunning_count=2)

    await billing._handle_payment_succeeded(db, {"customer": _CUSTOMER})

    assert captured.get("plan_status") == "active", (
        f"{locked_status}: recovery must restore active, got {captured.get('plan_status')!r}"
    )
    assert captured.get("billing_dunning_attempt_count") == 0


@pytest.mark.asyncio
async def test_fraud_pause_survives_payment_success():
    """A fraud pause (paused with zero dunning count) is NOT cleared by payment."""
    db, captured = _recovery_db("paused", dunning_count=0)

    await billing._handle_payment_succeeded(db, {"customer": _CUSTOMER})

    # dunning_count <= 0 short-circuits before any update
    assert "plan_status" not in captured, "fraud pause must survive payment events"
