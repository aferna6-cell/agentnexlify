"""Tests for the weekly owner funnel report (Monday scoreboard email).

Run with:
    pytest backend/tests/test_weekly_funnel_report.py --noconftest -v
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

import backend.services.weekly_funnel_report as wfr


MONDAY = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)      # a Monday
TUESDAY = datetime(2026, 7, 14, 14, 0, tzinfo=timezone.utc)
NEXT_MONDAY = datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc)

FUNNEL = {
    "total_tenants": 5,
    "activated": 3,
    "with_leads": 2,
    "paid": 3,
    "new_signups_week": 1,
    "new_leads_week": 4,
    "new_appointments_week": 2,
    "errors": [],
}


def _reset():
    wfr._last_sent_date = None


class TestMondayGate:
    def test_non_monday_sends_nothing(self):
        _reset()
        send = AsyncMock()
        with patch.object(wfr, "compute_funnel", return_value=FUNNEL), patch.object(
            wfr, "send_platform_email", send
        ):
            assert asyncio.run(wfr.send_weekly_funnel_report(now=TUESDAY)) == 0
        send.assert_not_called()

    def test_monday_sends_report(self):
        _reset()
        send = AsyncMock()
        with patch.object(wfr, "compute_funnel", return_value=FUNNEL), patch.object(
            wfr, "send_platform_email", send
        ):
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 1
        send.assert_called_once()
        subject = send.call_args.kwargs["subject"]
        assert "1 signups" in subject and "4 leads" in subject and "2 bookings" in subject

    def test_second_call_same_monday_is_deduped(self):
        _reset()
        send = AsyncMock()
        with patch.object(wfr, "compute_funnel", return_value=FUNNEL), patch.object(
            wfr, "send_platform_email", send
        ):
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 1
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 0
        send.assert_called_once()

    def test_next_monday_sends_again(self):
        _reset()
        send = AsyncMock()
        with patch.object(wfr, "compute_funnel", return_value=FUNNEL), patch.object(
            wfr, "send_platform_email", send
        ):
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 1
            assert asyncio.run(wfr.send_weekly_funnel_report(now=NEXT_MONDAY)) == 1
        assert send.call_count == 2


class TestFailureContract:
    def test_compute_funnel_failure_never_raises(self):
        _reset()
        with patch.object(
            wfr, "compute_funnel", side_effect=RuntimeError("db down")
        ), patch.object(wfr, "send_platform_email", AsyncMock()) as send:
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 0
        send.assert_not_called()

    def test_send_failure_never_raises_and_allows_retry(self):
        _reset()
        send = AsyncMock(side_effect=RuntimeError("resend down"))
        with patch.object(wfr, "compute_funnel", return_value=FUNNEL), patch.object(
            wfr, "send_platform_email", send
        ):
            assert asyncio.run(wfr.send_weekly_funnel_report(now=MONDAY)) == 0
        # Send failed before the guard was set — next tick retries.
        assert wfr._last_sent_date is None


class TestReportBody:
    def test_body_contains_all_metrics_and_escapes(self):
        body = wfr._build_report_html({**FUNNEL, "errors": ["<script>leads</script>"]})
        for expected in ["5", "3", "2", "1", "4"]:
            assert expected in body
        assert "<script>" not in body
        assert "Metrics that failed" in body
