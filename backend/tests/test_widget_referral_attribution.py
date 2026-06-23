"""Tests for widget-watermark referral attribution (apply_widget_referral_attribution).

Covers:
  (a) signup with a valid ref (api_key) stores referred_by_widget_key
  (b) signup without ref makes no DB write (signup works unchanged)
  (c) unknown api_key is silently ignored
  (d) self-referral is blocked
  (e) DB exception never raises (signup never blocked)
  (f) empty/None ref makes no DB calls
"""

import os
import sys
from unittest.mock import MagicMock, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.services.referral import apply_widget_referral_attribution

_NEW_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"
_REFERRER_TENANT = "bbbbbbbb-0000-0000-0000-000000000002"
_API_KEY = "anx_test_widget_api_key_xyz"


def _make_db(wc_rows):
    """Fake Supabase client returning wc_rows for widget_configs lookup."""
    db = MagicMock()

    wc_chain = MagicMock()
    wc_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=wc_rows
    )
    wc_chain.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )

    def table(name):
        return {"widget_configs": wc_chain, "tenants": wc_chain}[name]

    db.table.side_effect = table
    return db, wc_chain


def test_valid_ref_writes_referred_by_widget_key():
    """(a) Valid api_key → referred_by_widget_key stored on tenant."""
    db, chain = _make_db([{"tenant_id": _REFERRER_TENANT}])
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref=_API_KEY)
    # tenants.update should be called with the api_key
    chain.update.assert_called_once_with({"referred_by_widget_key": _API_KEY})
    chain.update.return_value.eq.assert_called_once_with("id", _NEW_TENANT)


def test_no_ref_makes_no_db_calls():
    """(b) None ref → zero DB calls (signup unaffected)."""
    db = MagicMock()
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref=None)
    db.table.assert_not_called()


def test_blank_ref_makes_no_db_calls():
    """(b) Whitespace-only ref → zero DB calls."""
    db = MagicMock()
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref="   ")
    db.table.assert_not_called()


def test_unknown_api_key_is_ignored():
    """(c) api_key not in widget_configs → no write, no exception."""
    db, chain = _make_db([])
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref="anx_bad_key")
    chain.update.assert_not_called()


def test_self_referral_blocked():
    """(d) Referrer tenant == new tenant → no write."""
    db, chain = _make_db([{"tenant_id": _NEW_TENANT}])
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref=_API_KEY)
    chain.update.assert_not_called()


def test_db_exception_never_raises():
    """(e) DB failure during lookup → swallowed, signup not blocked."""
    db = MagicMock()
    db.table.side_effect = RuntimeError("db is down")
    # Must not raise
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref=_API_KEY)


def test_db_exception_on_update_never_raises():
    """(e) DB failure during update → swallowed, signup not blocked."""
    db, chain = _make_db([{"tenant_id": _REFERRER_TENANT}])
    chain.update.return_value.eq.return_value.execute.side_effect = RuntimeError(
        "write failed"
    )
    # Must not raise
    apply_widget_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref=_API_KEY)
