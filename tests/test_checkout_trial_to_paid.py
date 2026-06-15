"""Tests for rubric criterion 3.7 — trial → paid transition.

Contract under test (two-plan model, 2026-06-15 repricing):
- checkout.session.completed webhook with metadata.plan set to each canonical
  plan name (chatbot, agent_os) flips the tenant's plan and plan_status to
  'active' immediately.
- _resolve_plan prefers metadata.plan over amount-based resolution when present.
- Both plan names resolve without ambiguity.
- A tenant that was on 'free' or trial is written to the new plan with plan_status='active'.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _no_fraud():
    """Happy-path checkouts: the fraud guard finds nothing.

    Without this, the MagicMock session data reads as suspicious and every
    test exercises the fraud-pause branch instead of activation. The fraud
    branch has its own coverage in backend/tests/test_fraud_guard.py.
    """
    with patch("backend.routers.billing.guard_checkout_for_fraud", return_value=None):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class Chain:
    """Minimal Supabase chain mock."""

    def __init__(self, data=None):
        self.data = data or []
        self.updated = None

    def select(self, *a, **kw):
        return self

    def update(self, data):
        self.updated = data
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        return MagicMock(data=self.data)


def _make_checkout_session(plan: str, tenant_id: str = "tenant-1") -> dict:
    """Build a minimal checkout.session.completed data dict."""
    return {
        "id": "cs_test_123",
        "object": "checkout.session",
        "mode": "subscription",
        "status": "complete",
        "customer": "cus_test",
        "subscription": "sub_test",
        "customer_email": "owner@example.com",
        "amount_total": 9900,  # won't be used — metadata.plan takes priority
        "metadata": {
            "tenant_id": tenant_id,
            "plan": plan,
        },
    }


# ---------------------------------------------------------------------------
# 3.7 — each plan flips tenant to plan_status='active'
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("plan_name", ["chatbot", "agent_os"])
def test_checkout_completed_sets_active_plan_status(plan_name):
    """checkout.session.completed for each canonical plan sets plan_status='active'."""
    from backend.routers.billing import _handle_checkout_completed

    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    db.table.return_value = tenant_update_chain

    session = _make_checkout_session(plan=plan_name, tenant_id="tenant-1")

    _handle_checkout_completed(db, session)

    assert tenant_update_chain.updated is not None, "tenants.update() was not called"
    assert tenant_update_chain.updated.get("plan_status") == "active", (
        f"Expected plan_status='active' for plan={plan_name!r}, "
        f"got {tenant_update_chain.updated.get('plan_status')!r}"
    )
    assert tenant_update_chain.updated.get("plan") == plan_name, (
        f"Expected plan={plan_name!r}, got {tenant_update_chain.updated.get('plan')!r}"
    )


@pytest.mark.parametrize("plan_name", ["chatbot", "agent_os"])
def test_checkout_completed_writes_stripe_ids(plan_name):
    """checkout.session.completed should also persist stripe_customer_id and stripe_subscription_id."""
    from backend.routers.billing import _handle_checkout_completed

    tenant_update_chain = Chain(data=[{"id": "tenant-1"}])
    db = MagicMock()
    db.table.return_value = tenant_update_chain

    session = _make_checkout_session(plan=plan_name, tenant_id="tenant-1")
    session["customer"] = "cus_xyz"
    session["subscription"] = "sub_xyz"

    _handle_checkout_completed(db, session)

    assert tenant_update_chain.updated.get("stripe_customer_id") == "cus_xyz"
    assert tenant_update_chain.updated.get("stripe_subscription_id") == "sub_xyz"


# ---------------------------------------------------------------------------
# 3.7 — _resolve_plan uses metadata.plan first
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("plan_name", ["chatbot", "agent_os"])
def test_resolve_plan_from_metadata(plan_name):
    """_resolve_plan returns metadata.plan directly for all four canonical plan names."""
    from backend.routers.billing import _resolve_plan

    session = {
        "metadata": {"plan": plan_name},
        "amount_total": 9900,  # would resolve to 'growth' if metadata not used
    }
    result = _resolve_plan(session)
    assert result == plan_name, f"Expected {plan_name!r}, got {result!r}"


def test_resolve_plan_rejects_retired_plan_names():
    """_resolve_plan must reject retired plan names like 'foundation' and 'operations'."""
    from backend.routers.billing import _resolve_plan

    # 'foundation' is a retired plan name — must not resolve
    session = {"metadata": {"plan": "foundation"}, "amount_total": 0}
    result = _resolve_plan(session)
    assert result is None, f"Expected None for retired plan 'foundation', got {result!r}"

    session = {"metadata": {"plan": "operations"}, "amount_total": 0}
    result = _resolve_plan(session)
    assert result is None, f"Expected None for retired plan 'operations', got {result!r}"


# ---------------------------------------------------------------------------
# 3.7 — checkout with no matching tenant is silently skipped (no crash)
# ---------------------------------------------------------------------------


def test_checkout_completed_missing_tenant_skips_gracefully():
    """If tenant_id is missing and email lookup returns nothing, function returns without crashing."""
    from backend.routers.billing import _handle_checkout_completed

    db = MagicMock()
    empty_chain = Chain(data=[])
    db.table.return_value = empty_chain

    session = {
        "metadata": {"plan": "growth"},
        "customer": "cus_test",
        "customer_email": "unknown@example.com",
        # No tenant_id in metadata — forces email lookup
    }

    # Should not raise
    _handle_checkout_completed(db, session)

    # No update should have been called because tenant was not found
    assert empty_chain.updated is None, "Update was called despite no tenant being found"


# ---------------------------------------------------------------------------
# 3.7 — tenant with plan='free' or plan='trial' transitions to paid
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("initial_plan", ["free", "chatbot"])
@pytest.mark.parametrize("new_plan", ["agent_os"])
def test_checkout_completed_upgrades_tenant_from_any_plan(initial_plan, new_plan):
    """_handle_checkout_completed writes new plan regardless of what tenant's old plan was.

    This proves trial/free tenants transition to paid correctly.
    """
    from backend.routers.billing import _handle_checkout_completed

    tenant_update_chain = Chain(data=[{"id": "tenant-1", "plan": initial_plan}])
    db = MagicMock()
    db.table.return_value = tenant_update_chain

    session = _make_checkout_session(plan=new_plan, tenant_id="tenant-1")
    _handle_checkout_completed(db, session)

    assert tenant_update_chain.updated.get("plan") == new_plan
    assert tenant_update_chain.updated.get("plan_status") == "active"
