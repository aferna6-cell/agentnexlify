"""Tests for the tenant-silence watch (funnel-audit follow-up, GH #573 companion).

Contract: a paying, active, non-demo tenant with no conversation in
SILENCE_DAYS gets exactly one ops alert per REALERT_DAYS window; healthy,
brand-new, and demo tenants are skipped; dedup-lookup failure fails noisy
(alert still sends).

Run: pytest backend/tests/test_tenant_silence_watch.py --noconftest -v
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.automation.scheduled import tenant_silence_watch as tsw


NOW = datetime.now(timezone.utc)
OLD = (NOW - timedelta(days=30)).isoformat()
RECENT = (NOW - timedelta(days=1)).isoformat()
STALE = (NOW - timedelta(days=10)).isoformat()

TENANT = {
    "id": "t-1",
    "business_name": "Acme",
    "plan": "chatbot",
    "plan_status": "active",
    "created_at": OLD,
    "is_demo": False,
}


class _FakeQuery:
    """Minimal chainable supabase query stub keyed by table name."""

    def __init__(self, db, table):
        self.db = db
        self.table = table

    def __getattr__(self, name):
        # select/eq/in_/gte/order/limit all chain
        def _chain(*args, **kwargs):
            return self

        return _chain

    def execute(self):
        result = MagicMock()
        result.data = self.db.responses.get(self.table, [])
        return result


class _FakeDB:
    def __init__(self, responses):
        self.responses = responses

    def table(self, name):
        return _FakeQuery(self, name)


def _run(db, send_email=None):
    send = send_email or AsyncMock(return_value={"success": True})
    with patch.object(tsw, "get_service_supabase", return_value=db), patch.object(
        tsw, "send_email", send
    ), patch.object(tsw, "log_activity") as log, patch.object(
        tsw, "_alert_recipient", return_value="ops@example.com"
    ):
        sent = asyncio.run(tsw.check_tenant_silence())
    return sent, send, log


def test_silent_tenant_alerts():
    db = _FakeDB(
        {
            "tenants": [dict(TENANT)],
            "conversations": [{"created_at": STALE}],
            "activity_log": [],
        }
    )
    sent, send, log = _run(db)
    assert sent == 1
    send.assert_awaited_once()
    assert "no conversations" in send.await_args.kwargs["subject"]
    log.assert_called_once()
    assert log.call_args.kwargs["activity_type"] == tsw.ALERT_ACTIVITY_TYPE


def test_never_conversed_old_tenant_alerts():
    db = _FakeDB(
        {"tenants": [dict(TENANT)], "conversations": [], "activity_log": []}
    )
    sent, send, _ = _run(db)
    assert sent == 1
    assert "NEVER" in send.await_args.kwargs["body_html"]


def test_healthy_tenant_skipped():
    db = _FakeDB(
        {
            "tenants": [dict(TENANT)],
            "conversations": [{"created_at": RECENT}],
            "activity_log": [],
        }
    )
    sent, send, _ = _run(db)
    assert sent == 0
    send.assert_not_awaited()


def test_recent_alert_dedups():
    db = _FakeDB(
        {
            "tenants": [dict(TENANT)],
            "conversations": [{"created_at": STALE}],
            "activity_log": [{"id": "existing-alert"}],
        }
    )
    sent, send, _ = _run(db)
    assert sent == 0
    send.assert_not_awaited()


def test_brand_new_tenant_skipped():
    tenant = dict(TENANT, created_at=(NOW - timedelta(days=2)).isoformat())
    db = _FakeDB({"tenants": [tenant], "conversations": [], "activity_log": []})
    sent, send, _ = _run(db)
    assert sent == 0
    send.assert_not_awaited()


def test_demo_tenant_skipped():
    tenant = dict(TENANT, is_demo=True)
    db = _FakeDB(
        {"tenants": [tenant], "conversations": [{"created_at": STALE}], "activity_log": []}
    )
    sent, send, _ = _run(db)
    assert sent == 0
    send.assert_not_awaited()


def test_dedup_lookup_failure_fails_noisy():
    db = _FakeDB(
        {"tenants": [dict(TENANT)], "conversations": [{"created_at": STALE}]}
    )
    send = AsyncMock(return_value={"success": True})
    with patch.object(tsw, "get_service_supabase", return_value=db), patch.object(
        tsw, "send_email", send
    ), patch.object(tsw, "log_activity"), patch.object(
        tsw, "_alert_recipient", return_value="ops@example.com"
    ), patch.object(
        tsw, "_recently_alerted", return_value=False
    ):
        sent_count = asyncio.run(tsw.check_tenant_silence())
    assert sent_count == 1
    send.assert_awaited_once()


def test_tenant_query_failure_returns_zero():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    with patch.object(tsw, "get_service_supabase", return_value=db):
        sent = asyncio.run(tsw.check_tenant_silence())
    assert sent == 0
