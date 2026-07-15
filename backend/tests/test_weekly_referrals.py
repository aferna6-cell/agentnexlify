"""Tests for backend/services/weekly_referrals.py (referral stats in weekly digest).

Coverage:
- Resolves ref_code from widget_configs.api_key for the tenant.
- Counts referral_clicks (ref_tenant_id == ref_code) in the window.
- Counts referred signups (tenants.referred_by_widget_key == ref_code) in window.
- No widget config → ref_code "" → all zeros, no further queries.
- Partial failure resilience: one table error yields zero for that field, not a crash.
- Tenant isolation: widget_configs uses tenant_id; clicks/signups use the embed key.
- Digest integration: a referral row renders in the value table when signups > 0.

No live DB calls — all Supabase access is mocked via unittest.mock.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure repo root is importable without an installed package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.weekly_referrals import compute_weekly_referrals

SINCE = "2026-06-16T00:00:00+00:00"


def _mock_result(data=None, count=None):
    r = MagicMock()
    r.data = data if data is not None else []
    r.count = count
    return r


def _build_db(widget_configs=None, clicks_count=None, signups_count=None):
    """Mock Supabase client with per-table responses for the referral reads.

    One mock is cached per table name so ``.eq``/``.gte`` call args persist for
    isolation assertions (a fresh mock per call would lose the recorded calls).
    """
    db = MagicMock()
    cache: dict[str, MagicMock] = {}

    results = {
        "widget_configs": _mock_result(data=widget_configs if widget_configs is not None else []),
        "referral_clicks": _mock_result(count=clicks_count),
        "tenants": _mock_result(count=signups_count),
    }

    def table_side_effect(name):
        if name not in cache:
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            m.execute.return_value = results.get(name, _mock_result())
            cache[name] = m
        return cache[name]

    db.table.side_effect = table_side_effect
    return db


class TestHappyPath:

    def test_counts_clicks_and_signups(self):
        db = _build_db(
            widget_configs=[{"api_key": "wk_abc"}],
            clicks_count=9,
            signups_count=2,
        )
        out = compute_weekly_referrals(db, "tenant-1", SINCE)
        assert out["ref_code"] == "wk_abc"
        assert out["referral_clicks"] == 9
        assert out["referred_signups"] == 2

    def test_result_has_all_expected_keys(self):
        db = _build_db(widget_configs=[{"api_key": "wk_abc"}], clicks_count=0, signups_count=0)
        out = compute_weekly_referrals(db, "tenant-1", SINCE)
        assert set(out.keys()) == {"ref_code", "referral_clicks", "referred_signups"}

    def test_null_counts_coerce_to_zero(self):
        # Supabase count= can come back None — must not propagate.
        db = _build_db(widget_configs=[{"api_key": "wk_abc"}], clicks_count=None, signups_count=None)
        out = compute_weekly_referrals(db, "tenant-1", SINCE)
        assert out["referral_clicks"] == 0
        assert out["referred_signups"] == 0


class TestNoReferralIdentity:

    def test_no_widget_config_returns_zeros(self):
        db = _build_db(widget_configs=[], clicks_count=5, signups_count=5)
        out = compute_weekly_referrals(db, "tenant-1", SINCE)
        assert out["ref_code"] == ""
        assert out["referral_clicks"] == 0
        assert out["referred_signups"] == 0

    def test_empty_api_key_returns_zeros(self):
        db = _build_db(widget_configs=[{"api_key": ""}], clicks_count=5, signups_count=5)
        out = compute_weekly_referrals(db, "tenant-1", SINCE)
        assert out["ref_code"] == ""
        assert out["referral_clicks"] == 0
        assert out["referred_signups"] == 0

    def test_no_identity_skips_count_queries(self):
        """With no embed key, neither referral_clicks nor tenants is queried."""
        db = _build_db(widget_configs=[])
        compute_weekly_referrals(db, "tenant-1", SINCE)
        queried = [c.args[0] for c in db.table.call_args_list]
        assert "referral_clicks" not in queried
        assert "tenants" not in queried


class TestPartialFailureResilience:

    def _db_with_failing(self, failing_table):
        db = MagicMock()

        def _table(name):
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.gte.return_value = m
            m.limit.return_value = m
            if name == failing_table:
                m.execute.side_effect = RuntimeError("DB error")
            elif name == "widget_configs":
                m.execute.return_value = _mock_result(data=[{"api_key": "wk_abc"}])
            elif name == "referral_clicks":
                m.execute.return_value = _mock_result(count=4)
            elif name == "tenants":
                m.execute.return_value = _mock_result(count=1)
            else:
                m.execute.return_value = _mock_result()
            return m

        db.table.side_effect = _table
        return db

    def test_widget_configs_failure_returns_zeros(self):
        out = compute_weekly_referrals(self._db_with_failing("widget_configs"), "t", SINCE)
        assert out == {"ref_code": "", "referral_clicks": 0, "referred_signups": 0}

    def test_clicks_failure_yields_zero_clicks_keeps_signups(self):
        out = compute_weekly_referrals(self._db_with_failing("referral_clicks"), "t", SINCE)
        assert out["ref_code"] == "wk_abc"
        assert out["referral_clicks"] == 0
        assert out["referred_signups"] == 1

    def test_signups_failure_yields_zero_signups_keeps_clicks(self):
        out = compute_weekly_referrals(self._db_with_failing("tenants"), "t", SINCE)
        assert out["ref_code"] == "wk_abc"
        assert out["referral_clicks"] == 4
        assert out["referred_signups"] == 0


class TestTenantIsolation:

    def test_widget_configs_resolved_by_tenant_id(self):
        db = _build_db(widget_configs=[{"api_key": "wk_abc"}], clicks_count=0, signups_count=0)
        compute_weekly_referrals(db, "tenant-99", SINCE)
        wc_eq_calls = db.table("widget_configs").eq.call_args_list
        assert any("tenant_id" in str(c) for c in wc_eq_calls)

    def test_clicks_and_signups_scoped_by_ref_code(self):
        db = _build_db(widget_configs=[{"api_key": "wk_xyz"}], clicks_count=1, signups_count=1)
        compute_weekly_referrals(db, "tenant-1", SINCE)
        clicks_eq = db.table("referral_clicks").eq.call_args_list
        signups_eq = db.table("tenants").eq.call_args_list
        assert any("ref_tenant_id" in str(c) and "wk_xyz" in str(c) for c in clicks_eq)
        assert any("referred_by_widget_key" in str(c) and "wk_xyz" in str(c) for c in signups_eq)


# ---------------------------------------------------------------------------
# Digest integration — referral row renders in the value table
# ---------------------------------------------------------------------------

def _run_async(coro):
    return asyncio.run(coro)


def _make_digest_db_with_referrals(api_key, clicks_count, signups_count):
    """Digest-level mock that also answers widget_configs + referral reads.

    leads/appointments/etc. return one lead so the week is non-empty (the
    referral row only renders in the stats-table branch, not empty-state).
    """
    db = MagicMock()

    def table_side_effect(name):
        m = MagicMock()
        for meth in ("select", "eq", "neq", "in_", "gte", "limit", "or_", "filter"):
            getattr(m, meth).return_value = m
        if name == "tenants":
            # tenants is used both for the digest roster (data) and the referred
            # signups count (count=). _build_and_send_digest only triggers the
            # count path here, so return both.
            m.execute.return_value = _mock_result(data=[], count=signups_count)
        elif name == "widget_configs":
            m.execute.return_value = _mock_result(data=[{"api_key": api_key}])
        elif name == "referral_clicks":
            m.execute.return_value = _mock_result(count=clicks_count)
        elif name == "leads":
            m.execute.return_value = _mock_result(data=[{"id": "l1", "deal_value": "100"}])
        elif name == "appointments":
            m.execute.return_value = _mock_result(count=0)
        elif name == "chat_messages":
            m.execute.return_value = _mock_result(data=[])
        elif name == "invoices":
            m.execute.return_value = _mock_result(data=[])
        elif name == "os_agent_runs":
            m.execute.return_value = _mock_result(count=0)
        else:
            m.execute.return_value = _mock_result()
        return m

    db.table.side_effect = table_side_effect
    return db


_TENANT = {
    "id": "t1",
    "owner_email": "x@x.com",
    "owner_name": "X",
    "business_name": "X Biz",
    "avg_lead_value": None,
    "plan_status": "active",
}


def _send_digest_capture(db):
    from backend.services.automation.scheduled_jobs_ext import _build_and_send_digest

    bodies = []

    async def mock_send_email(to, subject, body_html, tenant_id):
        bodies.append(body_html)
        return {"success": True}

    with patch("backend.services.automation.scheduled_jobs_ext.send_email", side_effect=mock_send_email):
        with patch("backend.services.activity.log_activity"):
            _run_async(
                _build_and_send_digest(
                    db=db,
                    tenant=_TENANT,
                    tid="t1",
                    email="x@x.com",
                    week_start="2026-06-12T00:00:00+00:00",
                    week_tag="weekly_digest_2026-06-19",
                )
            )
    assert len(bodies) == 1
    return bodies[0]


class TestDigestReferralRow:

    def test_signups_render_people_you_referred_row(self):
        db = _make_digest_db_with_referrals("wk_abc", clicks_count=12, signups_count=3)
        body = _send_digest_capture(db)
        assert "People you referred" in body
        assert ">3<" in body
        # Signups present → clicks row is NOT shown (signups is the money line)
        assert "Referral link clicks" not in body

    def test_clicks_only_render_link_clicks_row(self):
        db = _make_digest_db_with_referrals("wk_abc", clicks_count=7, signups_count=0)
        body = _send_digest_capture(db)
        assert "Referral link clicks" in body
        assert "People you referred" not in body

    def test_no_referral_activity_renders_no_referral_row(self):
        db = _make_digest_db_with_referrals("wk_abc", clicks_count=0, signups_count=0)
        body = _send_digest_capture(db)
        assert "People you referred" not in body
        assert "Referral link clicks" not in body
        # Core stats table still renders
        assert "Leads captured" in body
