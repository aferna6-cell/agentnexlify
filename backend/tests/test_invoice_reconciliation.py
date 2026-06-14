"""Tests for backend/services/invoice_reconciliation.py.

All tests use a fake in-memory DB — no Supabase network calls.
Covers:
  - clean tenant: no invoices → passes
  - paid invoice with paid_at → passes
  - paid invoice without paid_at → flagged
  - overdue invoice with past due_date → passes
  - overdue invoice with future due_date → flagged
  - invoice with negative total → flagged
  - invoice with orphaned tenant_id → flagged
  - multiple flags in one pass
  - DB error on invoices load → error row, no raise
  - one tenant's error does not kill reconcile_all_invoices
  - Stripe check skipped when no key in env
  - Stripe check skipped marker present in result
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ── fake DB builder ──────────────────────────────────────────────────────────


class _FakeChain:
    """Chainable query mock that returns configurable data on execute()."""

    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        return MagicMock(data=self._data)


def _make_db(
    *,
    invoices: list | None = None,
    invoices_raise: bool = False,
    all_tenants: list | None = None,
    per_tenant_invoices: dict | None = None,
):
    """Build a MagicMock DB with table() routing.

    Call order for reconcile_invoices_for_tenant:
        1. invoices (select, filtered by tenant_id)

    Call order for reconcile_all_invoices:
        1. tenants (list all tenant ids)
        then per-tenant invoice queries.

    per_tenant_invoices: dict mapping tenant_id -> list of invoice rows.
    """
    invoice_rows = invoices if invoices is not None else []
    call_count = [0]

    def _table_router(name: str):
        call_count[0] += 1

        if name == "tenants" and all_tenants is not None:
            return _FakeChain(data=all_tenants)

        if name == "invoices":
            if invoices_raise:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=invoice_rows)

        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _table_router
    return db


def _invoice(
    inv_id="inv-1",
    tenant_id="t-1",
    status="sent",
    due_date="2099-12-31",
    total=100.0,
    paid_at=None,
    stripe_payment_link=None,
    invoice_number="INV-001",
):
    return {
        "id": inv_id,
        "tenant_id": tenant_id,
        "invoice_number": invoice_number,
        "total": total,
        "due_date": due_date,
        "status": status,
        "paid_at": paid_at,
        "stripe_payment_link": stripe_payment_link,
    }


# ── clean cases ───────────────────────────────────────────────────────────────


class TestCleanCases:
    def test_no_invoices_passes(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert result["error"] is None
        assert result["any_mismatch"] is False
        assert result["total_invoices"] == 0

    def test_paid_with_evidence_passes(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice(status="paid", paid_at="2026-01-01T10:00:00Z"),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert result["error"] is None
        assert result["internal"]["paid_missing_evidence"] == []
        assert result["any_mismatch"] is False

    def test_overdue_with_past_due_date_passes(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice(status="overdue", due_date="2020-01-01"),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert result["internal"]["overdue_not_past_due"] == []
        assert result["any_mismatch"] is False

    def test_counts_by_status(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("i1", status="paid", paid_at="2026-01-01T00:00:00Z"),
            _invoice("i2", status="overdue", due_date="2020-01-01"),
            _invoice("i3", status="sent"),
            _invoice("i4", status="draft"),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert result["counts"]["paid"] == 1
        assert result["counts"]["overdue"] == 1
        assert result["counts"]["sent"] == 1
        assert result["counts"]["draft"] == 1
        assert result["total_invoices"] == 4


# ── internal consistency flags ────────────────────────────────────────────────


class TestInternalFlags:
    def test_paid_without_paid_at_flagged(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("inv-bad", status="paid", paid_at=None),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-bad" in result["internal"]["paid_missing_evidence"]
        assert result["any_mismatch"] is True

    def test_overdue_with_future_due_date_flagged(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("inv-fut", status="overdue", due_date="2099-12-31"),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-fut" in result["internal"]["overdue_not_past_due"]
        assert result["any_mismatch"] is True

    def test_negative_total_flagged(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("inv-neg", status="sent", total=-50.0),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-neg" in result["internal"]["negative_total"]
        assert result["any_mismatch"] is True

    def test_zero_total_passes(self):
        """Zero total is valid (e.g. fully discounted invoice)."""
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("inv-zero", status="sent", total=0.0),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-zero" not in result["internal"]["negative_total"]

    def test_orphaned_tenant_flagged(self):
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        inv = _invoice("inv-orp", tenant_id="t-other", status="sent")
        db = _make_db(invoices=[inv])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-orp" in result["internal"]["orphaned_tenant"]
        assert result["any_mismatch"] is True

    def test_multiple_flags_accumulated(self):
        """Multiple bad invoices accumulate into separate lists."""
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice("inv-a", status="paid", paid_at=None),
            _invoice("inv-b", status="overdue", due_date="2099-01-01"),
            _invoice("inv-c", status="sent", total=-10.0),
        ])
        result = reconcile_invoices_for_tenant(db, "t-1")

        assert "inv-a" in result["internal"]["paid_missing_evidence"]
        assert "inv-b" in result["internal"]["overdue_not_past_due"]
        assert "inv-c" in result["internal"]["negative_total"]
        assert result["any_mismatch"] is True


# ── DB error handling ─────────────────────────────────────────────────────────


class TestDbErrors:
    def test_db_error_on_invoices_returns_error_row(self):
        """DB failure loading invoices → error field set, no exception raised."""
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices_raise=True)
        result = reconcile_invoices_for_tenant(db, "t-err")

        assert result["error"] == "db_error_invoices"
        assert result["any_mismatch"] is False  # conservative: don't flag on read failure

    def test_one_tenant_error_does_not_kill_reconcile_all(self):
        """reconcile_all_invoices continues past per-tenant errors."""
        from backend.services.invoice_reconciliation import reconcile_all_invoices

        # Two tenants; second will error on invoices load.
        call_count = [0]

        def _table(name):
            call_count[0] += 1
            if name == "tenants":
                return _FakeChain(data=[{"id": "t-ok"}, {"id": "t-fail"}])
            if name == "invoices":
                if call_count[0] > 2:  # second tenant's invoice fetch
                    return _FakeChain(raise_on_execute=True)
                return _FakeChain(data=[])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _table

        results = reconcile_all_invoices(db)

        assert len(results) == 2
        # At least one result should be clean
        errors = [r for r in results if r.get("error")]
        non_errors = [r for r in results if not r.get("error")]
        assert len(non_errors) >= 1

    def test_db_failure_on_tenant_list_returns_error(self):
        """DB failure listing tenants → error result, no raise."""
        from backend.services.invoice_reconciliation import reconcile_all_invoices

        db = MagicMock()
        db.table.return_value = _FakeChain(raise_on_execute=True)

        results = reconcile_all_invoices(db)

        assert len(results) == 1
        assert results[0].get("error") == "db_error_list_tenants"


# ── Stripe skipped when no key ────────────────────────────────────────────────


class TestStripeSkipped:
    def test_stripe_check_skipped_when_no_key(self):
        """When STRIPE_SECRET_KEY is absent, stripe_check must be 'skipped'."""
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[
            _invoice(
                "inv-link",
                status="sent",
                stripe_payment_link="https://buy.stripe.com/test_abc123def456",
            ),
        ])

        with patch.dict("os.environ", {}, clear=True):
            # Remove both key variants
            import os
            os.environ.pop("STRIPE_SECRET_KEY", None)
            os.environ.pop("STRIPE_API_KEY", None)
            result = reconcile_invoices_for_tenant(db, "t-1")

        assert result["stripe_check"] == "skipped"
        assert result["error"] is None

    def test_stripe_skipped_marker_in_result_shape(self):
        """Result always has stripe_check key regardless of skip."""
        from backend.services.invoice_reconciliation import reconcile_invoices_for_tenant

        db = _make_db(invoices=[])
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("STRIPE_SECRET_KEY", None)
            os.environ.pop("STRIPE_API_KEY", None)
            result = reconcile_invoices_for_tenant(db, "t-1")

        assert "stripe_check" in result
        assert result["stripe_check"] in ("skipped", "ok", "mismatch", "error")

    def test_reconcile_all_collects_all_tenants(self):
        """reconcile_all_invoices returns one result per tenant."""
        from backend.services.invoice_reconciliation import reconcile_all_invoices

        call_seq = [0]

        def _table(name):
            call_seq[0] += 1
            if name == "tenants":
                return _FakeChain(data=[{"id": "ta-1"}, {"id": "ta-2"}, {"id": "ta-3"}])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _table

        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("STRIPE_SECRET_KEY", None)
            os.environ.pop("STRIPE_API_KEY", None)
            results = reconcile_all_invoices(db)

        assert len(results) == 3
        for r in results:
            assert r.get("error") is None
