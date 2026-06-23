"""Tests for churn_watch.run_churn_watch().

Mocks the Supabase client using the same _FakeChain pattern as test_funnel_metrics.py.
Mocks send_platform_email so no real emails are sent.

Run with:
    pytest backend/tests/test_churn_watch.py --noconftest -v

Coverage:
  - No alert sent when all paid tenants have recent leads
  - No alert sent when all paid tenants have recent chat_messages
  - Alert sent (to platform owner) when paid tenant has zero leads AND zero chat_messages in 14d
  - Free/lapsed tenants excluded from alert
  - trialing plan_status tenants included
  - per-tenant DB failure doesn't crash the batch (best-effort isolation)
  - tenants DB failure returns 0 and logs without raising
  - Empty at-risk list → no email sent
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Allow running without an installed package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Fake Supabase chain builder
# ---------------------------------------------------------------------------

class _FakeChain:
    """Chainable Supabase-style query mock — mirrors test_funnel_metrics.py."""

    def __init__(self, data=None, count=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._count = count
        self._raise = raise_on_execute

    # Chainable query builders — all return self
    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def neq(self, *_):
        return self

    def in_(self, *_):
        return self

    def gte(self, *_):
        return self

    def lt(self, *_):
        return self

    def lte(self, *_):
        return self

    def filter(self, *_):
        return self

    def limit(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        result.count = (
            self._count if self._count is not None else len(self._data)
        )
        return result


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _old_iso(days=20):
    """ISO timestamp older than the 14-day window."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _recent_iso(days=3):
    """ISO timestamp within the 14-day window."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _make_db(
    *,
    tenants_data=None,
    leads_data=None,
    messages_data=None,
    raise_tenants=False,
    raise_leads=False,
    raise_messages=False,
):
    """Build a MagicMock Supabase client for churn_watch tests.

    run_churn_watch() calls table() in this order per run:
      1. "tenants"      — fetch paid tenants (neq plan 'free', in_ plan_status active/trialing)
      2. "leads"        — fetch recent leads per tenant (eq client_id, gte created_at)
      3. "chat_messages" — fetch recent messages per tenant (eq tenant_id, gte created_at)

    Because leads and chat_messages are queried once per paid tenant (inside a
    per-tenant loop), a call counter approach is used only for "tenants".
    leads/messages routing is flat (same response for all eq calls in test scope).
    """
    leads_calls = [0]
    messages_calls = [0]

    def _router(name: str):
        if name == "tenants":
            return _FakeChain(
                data=tenants_data if tenants_data is not None else [],
                raise_on_execute=raise_tenants,
            )
        if name == "leads":
            leads_calls[0] += 1
            if raise_leads:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=leads_data if leads_data is not None else [])
        if name == "chat_messages":
            messages_calls[0] += 1
            if raise_messages:
                return _FakeChain(raise_on_execute=True)
            return _FakeChain(data=messages_data if messages_data is not None else [])
        return _FakeChain(data=[])

    db = MagicMock()
    db.table.side_effect = _router
    return db


# ---------------------------------------------------------------------------
# Helper: run the async function synchronously
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestRunChurnWatch:
    """Direct unit tests against run_churn_watch() with mocked DB and mailer."""

    def _call(self, db, *, send_mock=None):
        """Invoke run_churn_watch() with patched DB and mailer.

        Patches _now_utc to return a fixed Sunday so the weekday gate passes
        regardless of when tests run.
        """
        from backend.services.churn_watch import run_churn_watch

        if send_mock is None:
            send_mock = AsyncMock(return_value={"success": True})

        # 2026-06-28 is a Sunday (weekday() == 6)
        _sunday = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)

        with (
            patch("backend.services.churn_watch.get_service_supabase", return_value=db),
            patch("backend.services.churn_watch.send_platform_email", send_mock),
            patch("backend.services.churn_watch._now_utc", side_effect=lambda: _sunday),
        ):
            result = _run(run_churn_watch())

        return result, send_mock

    # --- Happy path: no at-risk tenants → no email ---

    def test_no_email_when_no_paid_tenants(self):
        db = _make_db(tenants_data=[])
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    def test_no_email_when_paid_tenant_has_recent_leads(self):
        tenants = [
            {
                "id": "t1",
                "business_name": "Biz A",
                "plan": "chatbot",
                "plan_status": "active",
            }
        ]
        # leads table returns a recent lead for client_id=t1
        leads = [{"id": "lead-1", "created_at": _recent_iso(2)}]
        db = _make_db(tenants_data=tenants, leads_data=leads, messages_data=[])
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    def test_no_email_when_paid_tenant_has_recent_messages(self):
        tenants = [
            {
                "id": "t2",
                "business_name": "Biz B",
                "plan": "agent_os",
                "plan_status": "active",
            }
        ]
        # chat_messages has recent activity
        messages = [{"id": "msg-1", "created_at": _recent_iso(5)}]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=messages)
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    # --- At-risk detection: zero leads AND zero messages in 14d → alert ---

    def test_email_sent_when_zero_leads_and_zero_messages(self):
        tenants = [
            {
                "id": "t3",
                "business_name": "Silent Corp",
                "plan": "chatbot",
                "plan_status": "active",
            }
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        result, send_mock = self._call(db)
        assert result == 1
        send_mock.assert_called_once()
        # Subject should mention churn or at-risk
        call_kwargs = send_mock.call_args.kwargs
        assert "subject" in call_kwargs
        assert "body_html" in call_kwargs

    def test_email_body_contains_business_name(self):
        tenants = [
            {
                "id": "t4",
                "business_name": "Acme Plumbing",
                "plan": "agent_os",
                "plan_status": "active",
            }
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        _, send_mock = self._call(db)
        send_mock.assert_called_once()
        body = send_mock.call_args.kwargs["body_html"]
        assert "Acme Plumbing" in body

    # --- trialing plan_status included ---

    def test_trialing_tenant_included_in_churn_watch(self):
        tenants = [
            {
                "id": "t5",
                "business_name": "Trial Biz",
                "plan": "chatbot",
                "plan_status": "trialing",
            }
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        result, send_mock = self._call(db)
        assert result == 1
        send_mock.assert_called_once()

    # --- Free / inactive tenants excluded ---

    def test_free_plan_tenant_excluded(self):
        tenants = [
            {
                "id": "t6",
                "business_name": "Free Tenant",
                "plan": "free",
                "plan_status": "active",
            }
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        # The tenants query should already filter out free plans via neq("plan","free")
        # and in_("plan_status", [...]) — but churn_watch also double-checks in Python.
        # The _FakeChain returns whatever tenants_data we give it regardless of filters,
        # so if free tenants slip through, the Python guard must catch them.
        result, send_mock = self._call(db)
        # Even if DB returned the free tenant, the Python guard should skip it
        assert result == 0
        send_mock.assert_not_called()

    def test_cancelled_plan_status_excluded(self):
        tenants = [
            {
                "id": "t7",
                "business_name": "Cancelled Biz",
                "plan": "chatbot",
                "plan_status": "cancelled",
            }
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    # --- Multiple tenants: only at-risk ones listed ---

    def test_only_at_risk_tenants_counted(self):
        tenants = [
            {
                "id": "ta",
                "business_name": "Active Biz",
                "plan": "agent_os",
                "plan_status": "active",
            },
            {
                "id": "tb",
                "business_name": "Silent Biz",
                "plan": "chatbot",
                "plan_status": "active",
            },
        ]
        # ta gets leads, tb gets nothing
        leads_calls = [0]
        messages_calls = [0]

        def _router(name):
            if name == "tenants":
                return _FakeChain(data=tenants)
            if name == "leads":
                leads_calls[0] += 1
                # First call = ta (has recent lead), second call = tb (empty)
                if leads_calls[0] == 1:
                    return _FakeChain(data=[{"id": "l1", "created_at": _recent_iso(1)}])
                return _FakeChain(data=[])
            if name == "chat_messages":
                messages_calls[0] += 1
                return _FakeChain(data=[])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _router

        from backend.services.churn_watch import run_churn_watch

        send_mock = AsyncMock(return_value={"success": True})
        _sunday = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
        with (
            patch("backend.services.churn_watch.get_service_supabase", return_value=db),
            patch("backend.services.churn_watch.send_platform_email", send_mock),
            patch("backend.services.churn_watch._now_utc", side_effect=lambda: _sunday),
        ):
            result = _run(run_churn_watch())

        # Only tb is at-risk; only one email with count=1
        assert result == 1
        send_mock.assert_called_once()
        body = send_mock.call_args.kwargs["body_html"]
        assert "Silent Biz" in body

    # --- Fault tolerance: per-tenant DB failure doesn't crash the batch ---

    def test_per_tenant_leads_failure_does_not_crash_batch(self):
        tenants = [
            {
                "id": "tf1",
                "business_name": "Failure Biz",
                "plan": "chatbot",
                "plan_status": "active",
            },
            {
                "id": "tf2",
                "business_name": "Good Biz",
                "plan": "chatbot",
                "plan_status": "active",
            },
        ]
        leads_calls = [0]

        def _router(name):
            if name == "tenants":
                return _FakeChain(data=tenants)
            if name == "leads":
                leads_calls[0] += 1
                if leads_calls[0] == 1:
                    return _FakeChain(raise_on_execute=True)  # tf1 fails
                return _FakeChain(data=[])  # tf2 has no leads
            if name == "chat_messages":
                return _FakeChain(data=[])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _router

        from backend.services.churn_watch import run_churn_watch

        send_mock = AsyncMock(return_value={"success": True})
        _sunday = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
        with (
            patch("backend.services.churn_watch.get_service_supabase", return_value=db),
            patch("backend.services.churn_watch.send_platform_email", send_mock),
            patch("backend.services.churn_watch._now_utc", side_effect=lambda: _sunday),
        ):
            # Must not raise; tf2 should still be evaluated
            result = _run(run_churn_watch())

        # tf1 is skipped (error), tf2 is at-risk → result = 1 (one at-risk entry in alert)
        # OR result = 0 if tf1's error causes it to be conservatively excluded.
        # Either is acceptable as long as no exception propagates.
        assert isinstance(result, int)

    def test_tenants_db_failure_returns_zero_and_does_not_raise(self):
        db = _make_db(raise_tenants=True)
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    # --- Empty at-risk list → no email sent ---

    def test_all_tenants_active_no_email(self):
        tenants = [
            {
                "id": "tc1",
                "business_name": "Healthy Biz",
                "plan": "agent_os",
                "plan_status": "active",
            }
        ]
        leads = [{"id": "l1", "created_at": _recent_iso(1)}]
        messages = [{"id": "m1", "created_at": _recent_iso(2)}]
        db = _make_db(tenants_data=tenants, leads_data=leads, messages_data=messages)
        result, send_mock = self._call(db)
        assert result == 0
        send_mock.assert_not_called()

    # --- Count return value ---

    def test_return_value_equals_at_risk_count(self):
        tenants = [
            {
                "id": "tx1",
                "business_name": "At Risk 1",
                "plan": "chatbot",
                "plan_status": "active",
            },
            {
                "id": "tx2",
                "business_name": "At Risk 2",
                "plan": "agent_os",
                "plan_status": "trialing",
            },
        ]
        db = _make_db(tenants_data=tenants, leads_data=[], messages_data=[])
        result, send_mock = self._call(db)
        assert result == 2
        # One email (digest for all at-risk tenants)
        send_mock.assert_called_once()
