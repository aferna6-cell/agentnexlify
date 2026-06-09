"""Tests for tenant_payments — Item 5 Stripe Connect resolver (launch-safe).

Locks the inert-by-default contract: with the feature flag OFF (prod default),
invoice payments ALWAYS route to the platform account, regardless of what is
stored on the tenant. Only when the flag is ON, status is active, and an account
id exists does it return the connected account.
"""

from unittest.mock import MagicMock, patch

from backend.services import tenant_payments
from backend.services.tenant_payments import resolve_invoice_stripe_account


def _db_returning(row):
    """Build a Supabase-style mock whose query chain returns ``[row]``."""
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=[row] if row is not None else [])
    return db


class TestFlagOff:
    def test_off_by_default_returns_none(self):
        # Default settings: flag is False -> platform account, no DB read.
        db = MagicMock()
        assert resolve_invoice_stripe_account(db, "tenant-1") is None
        db.table.assert_not_called()

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=False)
    def test_off_ignores_active_connection(self, _flag):
        db = _db_returning(
            {
                "stripe_connect_account_id": "acct_live",
                "stripe_connect_status": "active",
            }
        )
        assert resolve_invoice_stripe_account(db, "tenant-1") is None


class TestFlagOn:
    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_active_account_returns_id(self, _flag):
        db = _db_returning(
            {"stripe_connect_account_id": "acct_123", "stripe_connect_status": "active"}
        )
        assert resolve_invoice_stripe_account(db, "tenant-1") == "acct_123"

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_pending_status_returns_none(self, _flag):
        db = _db_returning(
            {
                "stripe_connect_account_id": "acct_123",
                "stripe_connect_status": "pending",
            }
        )
        assert resolve_invoice_stripe_account(db, "tenant-1") is None

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_missing_account_id_returns_none(self, _flag):
        db = _db_returning(
            {"stripe_connect_account_id": "", "stripe_connect_status": "active"}
        )
        assert resolve_invoice_stripe_account(db, "tenant-1") is None

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_no_row_returns_none(self, _flag):
        db = _db_returning(None)
        assert resolve_invoice_stripe_account(db, "tenant-1") is None

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_missing_columns_resilient(self, _flag):
        # Migration 135 not applied -> the select raises -> fall back to platform.
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
            'column "stripe_connect_account_id" does not exist'
        )
        assert resolve_invoice_stripe_account(db, "tenant-1") is None

    @patch.object(tenant_payments, "tenant_payments_enabled", return_value=True)
    def test_empty_tenant_id_returns_none(self, _flag):
        assert resolve_invoice_stripe_account(MagicMock(), "") is None
