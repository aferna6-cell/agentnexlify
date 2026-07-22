"""Tests for voice minutes metering (G3 Phase 3) — backend/services/voice_usage.py.

Contracts:
  - monthly aggregation sums this month's duration_seconds, 0 on error
  - allowance <= 0 means unmetered (never exhausted)
  - exhaustion trips at allowance*60 seconds and FAILS OPEN on errors
  - /voice/incoming degrades an over-cap AI-mode tenant to voicemail
    (<Record>), never a dropped call
"""

import os
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.main import app
from backend.routers.automations import verify_twilio_request
from backend.services import voice_usage as vu
from backend.tests.conftest import SyncASGITestClient


def _db_with_calls(rows):
    result = MagicMock()
    result.data = rows
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.execute.return_value = result
    db = MagicMock()
    db.table.return_value = chain
    return db


class TestMonthlyAggregation:
    def test_sums_duration_seconds(self):
        rows = [{"duration_seconds": 120}, {"duration_seconds": 45}, {"duration_seconds": None}]
        with patch.object(vu, "get_service_supabase", return_value=_db_with_calls(rows)):
            assert vu.monthly_voice_seconds("t1") == 165

    def test_zero_on_error(self):
        with patch.object(vu, "get_service_supabase", side_effect=RuntimeError("db down")):
            assert vu.monthly_voice_seconds("t1") == 0

    def test_month_start_is_first_of_month(self):
        from datetime import datetime, timezone

        now = datetime(2026, 7, 13, 15, 30, tzinfo=timezone.utc)
        assert vu.month_start_iso(now).startswith("2026-07-01T00:00:00")


class TestExhaustion:
    def test_under_allowance_not_exhausted(self):
        with patch.object(vu, "included_voice_minutes", return_value=300), patch.object(
            vu, "monthly_voice_seconds", return_value=299 * 60
        ):
            assert vu.voice_minutes_exhausted("t1") is False

    def test_at_allowance_exhausted(self):
        with patch.object(vu, "included_voice_minutes", return_value=300), patch.object(
            vu, "monthly_voice_seconds", return_value=300 * 60
        ):
            assert vu.voice_minutes_exhausted("t1") is True

    def test_non_positive_allowance_means_unmetered(self):
        with patch.object(vu, "included_voice_minutes", return_value=0), patch.object(
            vu, "monthly_voice_seconds", return_value=10_000_000
        ) as agg:
            assert vu.voice_minutes_exhausted("t1") is False
        agg.assert_not_called()

    def test_fails_open_on_error(self):
        with patch.object(vu, "included_voice_minutes", side_effect=RuntimeError("boom")):
            assert vu.voice_minutes_exhausted("t1") is False


class TestIncomingCallGuard:
    """Over-cap AI-mode tenant gets voicemail TwiML, not a dropped call."""

    _TENANT = {
        "id": "00000000-0000-0000-0000-000000000042",
        "business_name": "Metered Co",
        "business_type": "general",
        "owner_email": "o@metered.co",
        "notification_phone": "+15555550200",
        "plan": "agent_os",
        "voice_ai_enabled": True,
    }

    @pytest.fixture(autouse=True)
    def _bypass_signature(self):
        app.dependency_overrides[verify_twilio_request] = lambda: None
        try:
            yield
        finally:
            app.dependency_overrides.pop(verify_twilio_request, None)

    def _post_incoming(self):
        client = SyncASGITestClient(app)
        try:
            body = urllib.parse.urlencode(
                {
                    "CallSid": "CAmetered001",
                    "From": "+15555550100",
                    "To": "+15555550200",
                }
            )
            return client.post(
                "/api/v1/calls/voice/incoming",
                content=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        finally:
            client.close()

    def test_over_cap_degrades_to_voicemail(self, mock_supabase):
        with patch(
            "backend.routers.calls_webhooks._find_tenant_by_phone", return_value=self._TENANT
        ), patch(
            "backend.services.voice_usage.voice_minutes_exhausted", return_value=True
        ):
            resp = self._post_incoming()
        assert resp.status_code == 200
        assert "<Record" in resp.text  # voicemail mode
        assert "<Gather" not in resp.text

    def test_under_cap_stays_in_ai_mode(self, mock_supabase):
        with patch(
            "backend.routers.calls_webhooks._find_tenant_by_phone", return_value=self._TENANT
        ), patch(
            "backend.services.voice_usage.voice_minutes_exhausted", return_value=False
        ):
            resp = self._post_incoming()
        assert resp.status_code == 200
        assert "<Gather" in resp.text

    def test_metering_error_fails_open_to_ai_mode(self, mock_supabase):
        with patch(
            "backend.routers.calls_webhooks._find_tenant_by_phone", return_value=self._TENANT
        ), patch(
            "backend.services.voice_usage.voice_minutes_exhausted",
            side_effect=RuntimeError("metering down"),
        ):
            resp = self._post_incoming()
        assert resp.status_code == 200
        assert "<Gather" in resp.text
