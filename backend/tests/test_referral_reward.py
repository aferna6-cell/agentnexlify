"""Tests for the referral reward service (backend/services/referral_reward.py).

Covers: promo-code channel, widget-watermark channel, idempotency (the UNIQUE
referred_tenant_id contract), self-referral guard, no-referrer no-op, and the
missing-email failure path. Uses an in-memory fake Supabase that enforces the
unique constraint so idempotency is exercised for real, not mocked away.
"""

import asyncio
from unittest.mock import patch

import pytest

from backend.services import referral_reward
from backend.services.referral_reward import (
    REFERRAL_REWARD_CENTS,
    _grant_sync,
    grant_referral_reward_for_signup,
)

REFERRED = "00000000-0000-0000-0000-0000000000aa"
REFERRER = "00000000-0000-0000-0000-0000000000bb"
WIDGET_KEY = "anx_widget_key_referrer"


class _Result:
    def __init__(self, data):
        self.data = data
        self.count = None


class _Query:
    def __init__(self, db, table):
        self.db = db
        self.table_name = table
        self._filters = []
        self._op = None
        self._payload = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self._payload = row
        return self

    def update(self, vals):
        self._op = "update"
        self._payload = vals
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def limit(self, _n):
        return self

    def _match(self, rows):
        return [r for r in rows if all(r.get(c) == v for c, v in self._filters)]

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])
        if self._op == "select":
            return _Result([dict(r) for r in self._match(rows)])
        if self._op == "insert":
            row = dict(self._payload)
            if self.table_name == "referral_rewards":
                rt = row.get("referred_tenant_id")
                if any(r.get("referred_tenant_id") == rt for r in rows):
                    raise Exception("duplicate key value violates unique constraint")
                row.setdefault("id", f"reward-{len(rows) + 1}")
            rows.append(row)
            return _Result([dict(row)])
        if self._op == "update":
            matched = self._match(rows)
            for r in matched:
                r.update(self._payload)
            return _Result([dict(r) for r in matched])
        return _Result([])


class _FakeDB:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return _Query(self, name)


class _StripeCustomer:
    id = "cus_test_referrer"


def _seed_promo(db):
    db.tables["tenants"] = [
        {"id": REFERRED, "referred_by": REFERRER, "referred_by_widget_key": None},
        {"id": REFERRER, "owner_email": "ref@biz.com", "business_name": "Ref Biz"},
    ]


def _seed_widget(db):
    db.tables["tenants"] = [
        {"id": REFERRED, "referred_by": None, "referred_by_widget_key": WIDGET_KEY},
        {"id": REFERRER, "owner_email": "ref@biz.com", "business_name": "Ref Biz"},
    ]
    db.tables["widget_configs"] = [{"api_key": WIDGET_KEY, "tenant_id": REFERRER}]


@pytest.fixture()
def fake_db():
    db = _FakeDB()
    with patch(
        "backend.models.database.get_service_supabase", return_value=db
    ), patch(
        "backend.services.stripe_service.get_or_create_customer",
        return_value=_StripeCustomer(),
    ) as cust, patch(
        "stripe.Customer.create_balance_transaction"
    ) as bal:
        bal.return_value = type("Txn", (), {"id": "cbtxn_test"})()
        db._cust_mock = cust
        db._bal_mock = bal
        yield db


def _rewards(db):
    return db.tables.get("referral_rewards", [])


def test_grant_promo_channel(fake_db):
    _seed_promo(fake_db)
    _grant_sync(REFERRED)

    rows = _rewards(fake_db)
    assert len(rows) == 1
    assert rows[0]["status"] == "granted"
    assert rows[0]["attribution_channel"] == "promo_code"
    assert rows[0]["amount_cents"] == REFERRAL_REWARD_CENTS
    assert rows[0]["referrer_tenant_id"] == REFERRER

    fake_db._bal_mock.assert_called_once()
    _args, kwargs = fake_db._bal_mock.call_args
    assert kwargs["amount"] == -REFERRAL_REWARD_CENTS  # negative = credit
    assert kwargs["currency"] == "usd"


def test_grant_widget_channel(fake_db):
    _seed_widget(fake_db)
    _grant_sync(REFERRED)

    rows = _rewards(fake_db)
    assert len(rows) == 1
    assert rows[0]["status"] == "granted"
    assert rows[0]["attribution_channel"] == "widget_watermark"
    fake_db._bal_mock.assert_called_once()


def test_idempotent_double_fire(fake_db):
    _seed_promo(fake_db)
    _grant_sync(REFERRED)
    _grant_sync(REFERRED)  # webhook redelivery / second endpoint

    assert len(_rewards(fake_db)) == 1
    fake_db._bal_mock.assert_called_once()  # credit applied exactly once


def test_self_referral_promo_skips(fake_db):
    fake_db.tables["tenants"] = [
        {"id": REFERRED, "referred_by": REFERRED, "referred_by_widget_key": None},
    ]
    _grant_sync(REFERRED)

    assert _rewards(fake_db) == []
    fake_db._bal_mock.assert_not_called()


def test_no_referrer_noop(fake_db):
    fake_db.tables["tenants"] = [
        {"id": REFERRED, "referred_by": None, "referred_by_widget_key": None},
    ]
    _grant_sync(REFERRED)

    assert _rewards(fake_db) == []
    fake_db._bal_mock.assert_not_called()


def test_referrer_missing_email_marks_failed(fake_db):
    fake_db.tables["tenants"] = [
        {"id": REFERRED, "referred_by": REFERRER, "referred_by_widget_key": None},
        {"id": REFERRER, "owner_email": "", "business_name": "Ref Biz"},
    ]
    _grant_sync(REFERRED)

    rows = _rewards(fake_db)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "owner_email" in rows[0]["error"]
    fake_db._bal_mock.assert_not_called()


def test_async_wrapper_runs(fake_db, monkeypatch):
    # Flag added 2026-07-09: the grant is opt-in (REFERRAL_REWARD_ENABLED,
    # default off) so merging the feature commits no money until the owner
    # flips the env var. This test exercises the enabled path.
    monkeypatch.setenv("REFERRAL_REWARD_ENABLED", "1")
    _seed_promo(fake_db)
    asyncio.run(grant_referral_reward_for_signup(referred_tenant_id=REFERRED))

    assert len(_rewards(fake_db)) == 1
    fake_db._bal_mock.assert_called_once()


def test_async_wrapper_disabled_by_default_is_noop(fake_db, monkeypatch):
    monkeypatch.delenv("REFERRAL_REWARD_ENABLED", raising=False)
    _seed_promo(fake_db)
    asyncio.run(grant_referral_reward_for_signup(referred_tenant_id=REFERRED))

    assert _rewards(fake_db) == []
    fake_db._bal_mock.assert_not_called()


def test_async_wrapper_explicit_zero_is_noop(fake_db, monkeypatch):
    monkeypatch.setenv("REFERRAL_REWARD_ENABLED", "0")
    _seed_promo(fake_db)
    asyncio.run(grant_referral_reward_for_signup(referred_tenant_id=REFERRED))

    assert _rewards(fake_db) == []
    fake_db._bal_mock.assert_not_called()


def test_async_wrapper_empty_id_noop(fake_db):
    asyncio.run(grant_referral_reward_for_signup(referred_tenant_id=None))
    assert _rewards(fake_db) == []


# ---------------------------------------------------------------------------
# Reward-granted email (GH #413 item 10)
# ---------------------------------------------------------------------------


def test_grant_sends_referrer_email(fake_db):
    _seed_promo(fake_db)
    with patch(
        "backend.services.referral_reward_email.notify_reward_granted_sync"
    ) as notify:
        _grant_sync(REFERRED)

    assert _rewards(fake_db)[0]["status"] == "granted"
    notify.assert_called_once()
    kwargs = notify.call_args.kwargs
    assert kwargs["amount_cents"] == REFERRAL_REWARD_CENTS
    assert kwargs["recipient"]  # referrer owner_email from the seed


def test_email_failure_never_fails_the_grant(fake_db):
    _seed_promo(fake_db)
    with patch(
        "backend.services.referral_reward_email.notify_reward_granted_sync",
        side_effect=RuntimeError("resend down"),
    ):
        _grant_sync(REFERRED)  # must not raise

    # The grant row stays granted even though the email exploded — the email
    # path has its own try/except so it can never flip the row to failed.
    rows = _rewards(fake_db)
    assert rows and rows[0]["status"] == "granted"


def test_no_email_when_grant_skipped(fake_db):
    # No referrer seeded -> no grant -> no email
    with patch(
        "backend.services.referral_reward_email.notify_reward_granted_sync"
    ) as notify:
        _grant_sync(REFERRED)
    notify.assert_not_called()


class TestNotifyRewardGrantedSync:
    def test_skips_without_api_key(self):
        from backend.services import referral_reward_email as rre

        with patch.object(rre, "logger"), patch(
            "backend.config.settings.resend_api_key", ""
        ):
            ok = rre.notify_reward_granted_sync(
                recipient="o@t.co", referrer_name="A", referred_name="B",
                amount_cents=2000,
            )
        assert ok is False

    def test_sends_via_resend_when_configured(self):
        import resend

        from backend.services import referral_reward_email as rre

        with patch.object(resend.Emails, "send") as send, patch(
            "backend.config.settings.resend_api_key", "re_test_key"
        ):
            ok = rre.notify_reward_granted_sync(
                recipient="owner@biz.co", referrer_name="Biz A",
                referred_name="Biz B", amount_cents=2000,
            )
        assert ok is True
        params = send.call_args.args[0]
        assert params["to"] == ["owner@biz.co"]
        assert "$20" in params["subject"]
        assert "Biz B" in params["html"]
        assert "applied automatically" in params["html"]

    def test_send_failure_returns_false_never_raises(self):
        import resend

        from backend.services import referral_reward_email as rre

        with patch.object(
            resend.Emails, "send", side_effect=RuntimeError("api down")
        ), patch("backend.config.settings.resend_api_key", "re_test_key"):
            ok = rre.notify_reward_granted_sync(
                recipient="owner@biz.co", referrer_name="A",
                referred_name="B", amount_cents=2000,
            )
        assert ok is False

    def test_no_recipient_skips(self):
        from backend.services import referral_reward_email as rre

        assert (
            rre.notify_reward_granted_sync(
                recipient="", referrer_name="A", referred_name="B",
                amount_cents=2000,
            )
            is False
        )
