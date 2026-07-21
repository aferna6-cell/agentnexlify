"""Tests for photo-quote metered billing (#39).

Faked db + injected stripe_reporter — standalone:
    python3 -m pytest backend/tests/test_photo_quote_usage.py -v --noconftest
"""

from datetime import datetime, timezone

from backend.services import photo_quote_usage as usage
from backend.services.plan_catalog import PREMIUM_PLANS


# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #
class FakeChain:
    def __init__(self, store, key, upserts):
        self._store = store
        self._key = key
        self._upserts = upserts
        self._sel = False
        self._eqs = {}

    def select(self, *a, **k):
        self._sel = True
        return self

    def eq(self, col, val):
        self._eqs[col] = val
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, row, on_conflict=None):
        self._upserts.append({"row": row, "on_conflict": on_conflict})
        self._store[(row["client_id"], row["period_start"])] = row
        return self

    def execute(self):
        if self._sel:
            k = (self._eqs.get("client_id"), self._eqs.get("period_start"))
            row = self._store.get(k)
            return type("R", (), {"data": [row] if row else []})()
        return type("R", (), {"data": []})()


class FakeDB:
    def __init__(self):
        self.store = {}
        self.upserts = []

    def table(self, name):
        return FakeChain(self.store, name, self.upserts)


NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# eligibility                                                                  #
# --------------------------------------------------------------------------- #
def test_premium_plans_billing_eligible():
    for plan in PREMIUM_PLANS:
        assert usage.is_billing_eligible(plan)


def test_free_and_chatbot_not_eligible():
    assert not usage.is_billing_eligible("free")
    assert not usage.is_billing_eligible("chatbot")
    assert not usage.is_billing_eligible(None)


# --------------------------------------------------------------------------- #
# counting + rollover                                                          #
# --------------------------------------------------------------------------- #
def test_first_of_month_creates_new_period_row():
    db = FakeDB()
    count, overage = usage.increment_usage("t1", db=db, now=NOW)
    assert count == 1 and overage == 0
    # a row for this month's period_start exists
    assert ("t1", "2026-07-01") in db.store
    assert db.upserts[0]["on_conflict"] == "client_id,period_start"


def test_mid_month_increments_existing():
    db = FakeDB()
    db.store[("t1", "2026-07-01")] = {
        "client_id": "t1", "period_start": "2026-07-01",
        "quote_count": 12, "overage_count": 0,
    }
    count, overage = usage.increment_usage("t1", db=db, now=NOW)
    assert count == 13 and overage == 0


def test_new_month_starts_fresh_count():
    db = FakeDB()
    db.store[("t1", "2026-06-01")] = {
        "client_id": "t1", "period_start": "2026-06-01",
        "quote_count": 400, "overage_count": 0,
    }
    # July request — new period, count resets to 1
    count, _ = usage.increment_usage("t1", db=db, now=NOW)
    assert count == 1


# --------------------------------------------------------------------------- #
# overage trip + Stripe report                                                 #
# --------------------------------------------------------------------------- #
def test_overage_trips_past_500_and_reports(monkeypatch):
    # configure a metered price so the report path fires
    from backend import config as cfg
    monkeypatch.setattr(cfg.settings, "stripe_photo_quote_metered_price_id", "price_meter_123")

    reports = []

    def reporter(*, client_id, price_id, idempotency_key):
        reports.append({"client_id": client_id, "price_id": price_id, "idem": idempotency_key})

    db = FakeDB()
    db.store[("t1", "2026-07-01")] = {
        "client_id": "t1", "period_start": "2026-07-01",
        "quote_count": 500, "overage_count": 0,
    }
    count, overage = usage.increment_usage(
        "t1", quote_request_id="q-42", db=db, now=NOW, stripe_reporter=reporter
    )
    assert count == 501 and overage == 1
    assert len(reports) == 1
    assert reports[0]["idem"] == "t1:q-42"  # {client_id}:{quote_request_id}
    assert reports[0]["price_id"] == "price_meter_123"


def test_under_cap_does_not_report(monkeypatch):
    from backend import config as cfg
    monkeypatch.setattr(cfg.settings, "stripe_photo_quote_metered_price_id", "price_meter_123")
    reports = []
    db = FakeDB()
    usage.increment_usage(
        "t1", db=db, now=NOW,
        stripe_reporter=lambda **k: reports.append(k),
    )
    assert reports == []  # 1st quote of the month, well under 500


def test_overage_without_configured_price_counts_but_skips_report(monkeypatch):
    from backend import config as cfg
    monkeypatch.setattr(cfg.settings, "stripe_photo_quote_metered_price_id", "")
    reports = []
    db = FakeDB()
    db.store[("t1", "2026-07-01")] = {
        "client_id": "t1", "period_start": "2026-07-01",
        "quote_count": 500, "overage_count": 3,
    }
    count, overage = usage.increment_usage(
        "t1", db=db, now=NOW, stripe_reporter=lambda **k: reports.append(k)
    )
    assert count == 501 and overage == 4  # counted locally
    assert reports == []  # no price configured -> report skipped, never raised
