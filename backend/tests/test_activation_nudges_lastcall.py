"""Tests for the day-14+ last-call stage of activation nudges.

Added 2026-07-09: the d1/d3/d7 stages use exact-day windows, so tenants who
signed up before the nudge system shipped (or who slip past day 7) were never
contacted again. The last-call stage has an OPEN-ENDED window (created_at
older than 14 days, no lower bound) and relies on activity_log dedup to stay
one-shot per tenant.

Run with:
    pytest backend/tests/test_activation_nudges_lastcall.py --noconftest -v
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.activation_nudges import (
    _STAGES,
    _build_email,
    send_activation_nudges,
)


class _FakeQuery:
    """Chainable stub for the supabase query builder."""

    def __init__(self, rows=None, count=None):
        self._rows = rows or []
        self._count = count
        self.calls = []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self.calls.append((name, args))
            return self

        return _method

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        result.count = self._count
        return result


def _tenant_row(business_name, age_days, plan="free", email="owner@example.com"):
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    return {
        "id": f"tenant-{business_name.lower().replace(' ', '-')}",
        "business_name": business_name,
        "owner_email": email,
        "owner_name": "Owner",
        "plan": plan,
        "is_demo": False,
        "created_at": created,
    }


class TestStageDefinition:
    def test_lastcall_stage_present_and_open_ended(self):
        lastcall = [s for s in _STAGES if s[0] == "activation_nudge_d14_lastcall"]
        assert len(lastcall) == 1
        _, min_day, max_day = lastcall[0]
        assert min_day == 14
        assert max_day is None  # open-ended — catches pre-existing drop-offs

    def test_exact_day_stages_unchanged(self):
        exact = {(s[0], s[1], s[2]) for s in _STAGES if s[2] is not None}
        assert ("activation_nudge_d1", 1, 1) in exact
        assert ("activation_nudge_d3", 3, 3) in exact
        assert ("activation_nudge_d7", 7, 7) in exact


class TestLastcallEmail:
    def test_build_email_lastcall_subject_and_body(self):
        subject, body = _build_email(
            "activation_nudge_d14_lastcall",
            "Nikola",
            "Niko's Consulting",
            "https://app.agentnexlify.com/dashboard/settings",
        )
        assert "still waiting" in subject
        assert "Niko&#x27;s Consulting" in subject or "Niko's Consulting" in subject
        assert "last automated email" in body
        assert "app.agentnexlify.com" in body

    def test_lastcall_body_escapes_html(self):
        _, body = _build_email(
            "activation_nudge_d14_lastcall",
            "<script>alert(1)</script>",
            "<b>Biz</b>",
            "https://app.agentnexlify.com/x",
        )
        assert "<script>" not in body
        assert "<b>Biz</b>" not in body


class TestSendLoop:
    def _run(self, tenant_rows):
        """Run send_activation_nudges with a fake db. Returns (sent, send_email mock)."""
        fake_db = MagicMock()

        def _table(name):
            if name == "tenants":
                return _FakeQuery(rows=tenant_rows)
            if name == "activity_log":
                return _FakeQuery(rows=[], count=0)  # no prior nudges
            if name == "leads":
                return _FakeQuery(rows=[], count=0)  # zero leads → stuck
            return _FakeQuery()

        fake_db.table.side_effect = _table

        send_mock = AsyncMock(return_value={"success": True})
        with patch(
            "backend.services.activation_nudges.get_service_supabase",
            return_value=fake_db,
        ), patch(
            "backend.services.activation_nudges.send_email", send_mock
        ), patch(
            "backend.services.activation_nudges.log_activity", MagicMock()
        ):
            sent = asyncio.run(send_activation_nudges())
        return sent, send_mock

    def test_old_abandoned_signup_gets_lastcall(self):
        # 20-day-old free tenant — outside every exact-day window, inside last-call.
        sent, send_mock = self._run([_tenant_row("Sunset Mobile Detailing", 20)])
        assert sent >= 1
        subjects = [c.kwargs.get("subject", "") for c in send_mock.call_args_list]
        assert any("still waiting" in s for s in subjects)

    def test_internal_tenant_never_nudged(self):
        sent, send_mock = self._run(
            [
                _tenant_row("AgentNexLiFy Smoke Test", 20),
                _tenant_row("Agent Nexlify", 30),
                _tenant_row("Luxe & Co. Salon (DEMO)", 25),
            ]
        )
        assert sent == 0
        send_mock.assert_not_called()

    def test_paid_tenant_never_nudged(self):
        sent, send_mock = self._run([_tenant_row("Real Biz", 20, plan="agent_os")])
        assert sent == 0
        send_mock.assert_not_called()

    def test_tenant_without_email_skipped(self):
        sent, send_mock = self._run([_tenant_row("No Email Biz", 20, email=None)])
        assert sent == 0
        send_mock.assert_not_called()
