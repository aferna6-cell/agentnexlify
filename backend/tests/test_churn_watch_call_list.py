"""Churn-watch call list (2026-08-25).

The Sunday alert is now an actionable call list: each at-risk tenant row
carries plan price framing, last recorded activity, and the owner's contact
email, plus a ready-to-send re-engagement draft. Drafts are copy-paste only —
the job must never email the tenant directly (drafts-only trust boundary).

Run with:
    pytest backend/tests/test_churn_watch_call_list.py --noconftest -v
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


class _FakeChain:
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

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

    def limit(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated DB failure")
        result = MagicMock()
        result.data = self._data
        return result


def _run(coro):
    return asyncio.run(coro)


_SUNDAY = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)


def _call_with_router(router):
    from backend.services.churn_watch import run_churn_watch

    db = MagicMock()
    db.table.side_effect = router
    send_mock = AsyncMock(return_value={"success": True})
    with (
        patch("backend.services.churn_watch.get_service_supabase", return_value=db),
        patch("backend.services.churn_watch.send_platform_email", send_mock),
        patch("backend.services.churn_watch._now_utc", side_effect=lambda: _SUNDAY),
    ):
        result = _run(run_churn_watch())
    return result, send_mock


def _silent_tenant_router(
    *, owner_email="owner@silent.biz", last_lead_iso=None, last_msg_iso=None
):
    """One at-risk tenant. First leads/messages calls are the 14d-window checks
    (empty), later calls are the last-activity lookups."""
    tenants = [
        {
            "id": "t1",
            "business_name": "Silent Corp",
            "plan": "agent_os",
            "plan_status": "active",
            "owner_email": owner_email,
        }
    ]
    leads_calls = [0]
    msgs_calls = [0]

    def _router(name):
        if name == "tenants":
            return _FakeChain(data=tenants)
        if name == "leads":
            leads_calls[0] += 1
            if leads_calls[0] == 1:  # in-window check → at risk
                return _FakeChain(data=[])
            return _FakeChain(
                data=[{"created_at": last_lead_iso}] if last_lead_iso else []
            )
        if name == "chat_messages":
            msgs_calls[0] += 1
            if msgs_calls[0] == 1:
                return _FakeChain(data=[])
            return _FakeChain(
                data=[{"created_at": last_msg_iso}] if last_msg_iso else []
            )
        return _FakeChain(data=[])

    return _router


class TestCallListEmail:
    def test_body_contains_reengagement_draft(self):
        result, send_mock = _call_with_router(_silent_tenant_router())
        assert result == 1
        body = send_mock.call_args.kwargs["body_html"]
        assert "Ready-to-send drafts" in body
        assert "Draft for Silent Corp" in body
        assert "Subject: Getting more out of your AI assistant" in body
        # drafts-only boundary is stated
        assert "Nothing is sent automatically" in body

    def test_body_contains_owner_email_and_mailto(self):
        _, send_mock = _call_with_router(
            _silent_tenant_router(owner_email="owner@silent.biz")
        )
        body = send_mock.call_args.kwargs["body_html"]
        assert "owner@silent.biz" in body
        assert "mailto:owner@silent.biz" in body

    def test_body_contains_plan_price_framing(self):
        _, send_mock = _call_with_router(_silent_tenant_router())
        body = send_mock.call_args.kwargs["body_html"]
        assert "$99.99/mo" in body  # agent_os MRR at stake

    def test_body_contains_last_activity_date(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        _, send_mock = _call_with_router(
            _silent_tenant_router(last_msg_iso=old)
        )
        body = send_mock.call_args.kwargs["body_html"]
        assert old[:10] in body

    def test_no_activity_recorded_when_tenant_never_active(self):
        _, send_mock = _call_with_router(_silent_tenant_router())
        body = send_mock.call_args.kwargs["body_html"]
        assert "No activity recorded" in body

    def test_only_platform_email_is_sent(self):
        """The job emails the OWNER once; it never emails the tenant."""
        result, send_mock = _call_with_router(_silent_tenant_router())
        assert result == 1
        send_mock.assert_called_once()  # single platform (owner) email

    def test_last_activity_lookup_failure_does_not_crash(self):
        tenants = [
            {
                "id": "t1",
                "business_name": "Silent Corp",
                "plan": "chatbot",
                "plan_status": "active",
                "owner_email": "o@x.com",
            }
        ]
        leads_calls = [0]

        def _router(name):
            if name == "tenants":
                return _FakeChain(data=tenants)
            if name == "leads":
                leads_calls[0] += 1
                if leads_calls[0] == 1:
                    return _FakeChain(data=[])
                return _FakeChain(raise_on_execute=True)  # lookup fails
            if name == "chat_messages":
                return _FakeChain(data=[])
            return _FakeChain(data=[])

        result, send_mock = _call_with_router(_router)
        assert result == 1
        send_mock.assert_called_once()


class TestDraftContent:
    def test_draft_is_personalized_and_signed_as_placeholder(self):
        from backend.services.churn_watch import _reengagement_draft

        draft = _reengagement_draft({"business_name": "Acme Plumbing"}, 14)
        assert "Acme Plumbing" in draft
        assert "14 days" in draft
        assert "[Your name]" in draft  # owner personalizes before sending

    def test_draft_handles_missing_name(self):
        from backend.services.churn_watch import _reengagement_draft

        draft = _reengagement_draft({}, 14)
        assert "Hi there team" in draft


class TestLastActivityHelper:
    def test_picks_latest_of_lead_and_message(self):
        from backend.services.churn_watch import _last_activity

        lead_iso = "2026-07-01T00:00:00+00:00"
        msg_iso = "2026-08-01T00:00:00+00:00"

        def _router(name):
            if name == "leads":
                return _FakeChain(data=[{"created_at": lead_iso}])
            if name == "chat_messages":
                return _FakeChain(data=[{"created_at": msg_iso}])
            return _FakeChain(data=[])

        db = MagicMock()
        db.table.side_effect = _router
        assert _last_activity(db, "t1") == msg_iso

    def test_empty_when_no_rows(self):
        from backend.services.churn_watch import _last_activity

        db = MagicMock()
        db.table.side_effect = lambda name: _FakeChain(data=[])
        assert _last_activity(db, "t1") == ""
