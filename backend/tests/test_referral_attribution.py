"""Tests for referral attribution at signup (rubric 9.4).

Service-level coverage of backend/services/referral.py:
  - valid code → tenants.referred_by written
  - active promo with discount → referral_discount_pct written
  - unknown code → no write, no exception
  - self-referral → blocked, no write
  - DB exception → swallowed (signup never blocked)
  - empty/None code → no DB calls at all
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.services.referral import apply_referral_attribution

_NEW_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"
_REFERRER = "bbbbbbbb-0000-0000-0000-000000000002"


def _make_db(referrer_rows, promo_rows):
    """Fake supabase client routing by table name."""
    db = MagicMock()

    tenants_select = MagicMock()
    tenants_select.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=referrer_rows
    )
    tenants_update = MagicMock()
    tenants_select.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )
    tenants_select.update_mock = tenants_update

    promos = MagicMock()
    promos.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=promo_rows
    )

    def table(name):
        return {"tenants": tenants_select, "admin_promotions": promos}[name]

    db.table.side_effect = table
    return db, tenants_select


def test_valid_code_writes_referred_by():
    db, tenants = _make_db([{"id": _REFERRER}], [])
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="abc12345")
    updates = tenants.update.call_args[0][0]
    assert updates == {"referred_by": _REFERRER}
    tenants.update.return_value.eq.assert_called_once_with("id", _NEW_TENANT)


def test_active_promo_applies_discount():
    db, tenants = _make_db(
        [{"id": _REFERRER}],
        [{"id": "promo-1", "discount_pct": 20, "expires_at": None}],
    )
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="abc12345")
    updates = tenants.update.call_args[0][0]
    assert updates == {"referred_by": _REFERRER, "referral_discount_pct": 20}


def test_unknown_code_is_ignored():
    db, tenants = _make_db([], [])
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="nope1234")
    tenants.update.assert_not_called()


def test_self_referral_blocked():
    db, tenants = _make_db([{"id": _NEW_TENANT}], [])
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="abc12345")
    tenants.update.assert_not_called()


def test_db_exception_never_raises():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    # Must not raise — signup is never blocked by referral lookup
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="abc12345")


def test_none_or_blank_code_makes_no_db_calls():
    db = MagicMock()
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code=None)
    apply_referral_attribution(db, new_tenant_id=_NEW_TENANT, ref_code="   ")
    db.table.assert_not_called()
