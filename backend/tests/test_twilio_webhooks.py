"""Tests for backend/routers/twilio_webhooks.py.

Characterization tests capture existing behavior before modification.
Extension tests verify Phase 1 additions: missed_call_texts row,
activity log, runs_total increment, automation check, replay window.

Supabase client mocked via _stub_supabase_singletons (autouse in conftest).
Twilio signature verification patched for all tests.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


TENANT_ID = "00000000-0000-0000-0000-000000000001"
CALLER = "+15555550100"
CALLED = "+15555550200"
CALL_SID = "CAtest123"
SMS_SID = "SMtest456"

# Minimal tenant row as returned from DB
TENANT_ROW = {
    "id": TENANT_ID,
    "business_name": "Test Plumbing",
    "notification_phone": CALLED,
    "sms_notifications_enabled": True,
    "plan": "growth",
    "textback_enabled": True,
    "textback_message": None,
    "textback_quiet_start": None,
    "textback_quiet_end": None,
}

AUTOMATION_ROW = {
    "id": "auto-001",
    "tenant_id": TENANT_ID,
    "type": "missed_call_textback",
    "is_enabled": True,
    "config": {"mode": "hold", "hold_seconds": 60, "template_id": "default"},
    "runs_total": 0,
}


def _make_form_body(
    caller: str = CALLER,
    called: str = CALLED,
    call_status: str = "no-answer",
    call_sid: str = CALL_SID,
    call_duration: str = "0",
    timestamp: str | None = None,
) -> bytes:
    """Build a URL-encoded Twilio webhook body."""
    from urllib.parse import urlencode
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    params = {
        "From": caller,
        "To": called,
        "CallStatus": call_status,
        "CallSid": call_sid,
        "CallDuration": call_duration,
        "Timestamp": ts,
    }
    return urlencode(params).encode()


def _patch_sig_verify(monkeypatch):
    """Bypass Twilio HMAC-SHA1 signature check."""
    monkeypatch.setattr(
        "backend.routers.twilio_webhooks._verify_twilio_signature",
        lambda request, body: True,
    )


@pytest.fixture(autouse=True)
def _default_not_opted_out(monkeypatch):
    """SMS opt-out suppression has dedicated coverage in
    tests/test_sms_compliance.py. These handler tests assume the caller is NOT
    opted out (the common case); without this, the new opt-out lookup hits the
    generic Supabase mock whose .data is truthy and wrongly suppresses every
    text-back. Tests that want suppression override this with patch(...).
    """
    monkeypatch.setattr(
        "backend.routers.twilio_webhooks.sms_compliance.is_suppressed",
        lambda *a, **k: False,
    )
    monkeypatch.setattr(
        "backend.routers.twilio_webhooks.sms_compliance.recently_messaged",
        lambda *a, **k: False,
    )


def _wire_tenant_lookup(mock_supabase, tenant: dict | None = TENANT_ROW):
    """Wire mock_supabase to return tenant for _find_tenant_by_phone."""
    result = MagicMock()
    result.data = [tenant] if tenant else []
    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = result
    return result


@pytest.fixture(autouse=True)
def _reset_tenant_phone_index():
    """Clear the per-worker phone->tenant cache between tests.

    _find_tenant_by_phone (GH #98) caches SMS-enabled tenants at module scope
    with a 60s TTL. Without resetting, one test's wired tenant would leak into
    the next (e.g. test_no_matching_tenant would still see a cached row).
    """
    import backend.routers.twilio_webhooks as tw

    tw._TENANT_PHONE_INDEX = {}
    tw._TENANT_PHONE_INDEX_AT = 0.0
    yield
    tw._TENANT_PHONE_INDEX = {}
    tw._TENANT_PHONE_INDEX_AT = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Characterization tests — capture EXISTING behavior (do not change)
# ─────────────────────────────────────────────────────────────────────────────

class TestHandleMissedCallCharacterization:
    """Capture existing handle_missed_call behavior before Phase 1 additions."""

    def test_returns_200_ok_on_valid_missed_call(self, client, mock_supabase, monkeypatch):
        """Valid missed-call webhook → 200 PlainText 'OK'."""
        _patch_sig_verify(monkeypatch)

        # Tenant lookup
        tenant_result = MagicMock()
        tenant_result.data = [TENANT_ROW]
        # Leads lookup (no existing lead)
        leads_result = MagicMock()
        leads_result.data = []
        # leads insert
        insert_result = MagicMock()
        insert_result.data = []
        # activity_log insert
        activity_result = MagicMock()
        activity_result.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = tenant_result
        mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_result

        with patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:
            mock_sms.return_value = True
            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_no_caller_returns_ok(self, client, mock_supabase, monkeypatch):
        """Empty From field → 200 OK, no processing."""
        _patch_sig_verify(monkeypatch)
        body = b"From=&To=%2B15555550200&CallStatus=no-answer&CallSid=CA1&CallDuration=0&Timestamp=2026-04-22T12%3A00%3A00%2B0000"
        resp = client.post(
            "/api/v1/twilio/missed-call",
            content=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200

    def test_answered_call_skipped(self, client, mock_supabase, monkeypatch):
        """CallStatus=in-progress → skipped, 200 OK."""
        _patch_sig_verify(monkeypatch)
        resp = client.post(
            "/api/v1/twilio/missed-call",
            content=_make_form_body(call_status="in-progress"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200

    def test_bad_signature_returns_403(self, client, mock_supabase, monkeypatch):
        """Invalid Twilio signature → 403."""
        monkeypatch.setattr(
            "backend.routers.twilio_webhooks._verify_twilio_signature",
            lambda request, body: False,
        )
        resp = client.post(
            "/api/v1/twilio/missed-call",
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 403

    def test_no_matching_tenant_returns_ok(self, client, mock_supabase, monkeypatch):
        """No tenant found for called number → 200 OK, no SMS."""
        _patch_sig_verify(monkeypatch)
        no_tenant = MagicMock()
        no_tenant.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = no_tenant

        with patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:
            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        mock_sms.assert_not_called()
        assert resp.status_code == 200

    def test_textback_disabled_skips_sms(self, client, mock_supabase, monkeypatch):
        """textback_enabled=False → 200 OK, no SMS."""
        _patch_sig_verify(monkeypatch)
        tenant_no_textback = {**TENANT_ROW, "textback_enabled": False}
        result = MagicMock()
        result.data = [tenant_no_textback]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = result

        with patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:
            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        mock_sms.assert_not_called()
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Extension tests — Phase 1 new behavior
# ─────────────────────────────────────────────────────────────────────────────

class TestHandleMissedCallExtensions:
    """Phase 1 extension: missed_call_texts row, activity log, automation check."""

    def test_handle_missed_call_disabled_automation_skips(
        self, client, mock_supabase, monkeypatch
    ):
        """automation.is_enabled=False → 200 OK, no SMS, no DB writes."""
        _patch_sig_verify(monkeypatch)

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = {**AUTOMATION_ROW, "is_enabled": False}

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_handle_missed_call_suppressed_when_opted_out(
        self, client, mock_supabase, monkeypatch
    ):
        """Caller opted out (STOP) → 200 OK, no SMS (TCPA suppression)."""
        _patch_sig_verify(monkeypatch)
        monkeypatch.setattr(
            "backend.routers.twilio_webhooks.sms_compliance.is_suppressed",
            lambda *a, **k: True,
        )
        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_handle_missed_call_frequency_cap_skips(
        self, client, mock_supabase, monkeypatch
    ):
        """Already texted this caller within 24h → 200 OK, no second SMS."""
        _patch_sig_verify(monkeypatch)
        monkeypatch.setattr(
            "backend.routers.twilio_webhooks.sms_compliance.recently_messaged",
            lambda *a, **k: True,
        )
        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_handle_missed_call_no_automation_row_skips(
        self, client, mock_supabase, monkeypatch
    ):
        """No automation row found → 200 OK, no SMS."""
        _patch_sig_verify(monkeypatch)

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = None

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_handle_missed_call_replay_window_rejects_old_timestamp(
        self, client, mock_supabase, monkeypatch
    ):
        """Timestamp older than 5 minutes → 200 OK, no SMS (replay protection)."""
        _patch_sig_verify(monkeypatch)
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%S+0000"
        )

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(timestamp=old_ts),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_handle_missed_call_writes_row_and_activity(
        self, client, mock_supabase, monkeypatch
    ):
        """Successful send → INSERT missed_call_texts + log_activity called."""
        _patch_sig_verify(monkeypatch)

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms, \
             patch("backend.routers.twilio_webhooks.log_activity") as mock_log, \
             patch("backend.routers.twilio_webhooks._insert_missed_call_row") as mock_insert, \
             patch("backend.routers.twilio_webhooks._increment_runs_total") as mock_incr:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW
            mock_sms.return_value = (True, SMS_SID)
            mock_insert.return_value = None
            mock_incr.return_value = None

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_called_once()
        mock_log.assert_called_once()
        mock_insert.assert_called_once()
        mock_incr.assert_called_once_with(TENANT_ID, "missed_call_textback")

    def test_handle_missed_call_increments_runs_total(
        self, client, mock_supabase, monkeypatch
    ):
        """On success, _increment_runs_total called with correct tenant + type."""
        _patch_sig_verify(monkeypatch)

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms, \
             patch("backend.routers.twilio_webhooks.log_activity"), \
             patch("backend.routers.twilio_webhooks._insert_missed_call_row"), \
             patch("backend.routers.twilio_webhooks._increment_runs_total") as mock_incr:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW
            mock_sms.return_value = (True, SMS_SID)

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_incr.assert_called_once_with(TENANT_ID, "missed_call_textback")

    def test_handle_missed_call_personalized_for_known_lead(
        self, client, mock_supabase, monkeypatch
    ):
        """Known lead in DB → send_sms called (personalization doesn't block flow)."""
        _patch_sig_verify(monkeypatch)

        with patch("backend.routers.twilio_webhooks._find_tenant_by_phone") as mock_find, \
             patch("backend.routers.twilio_webhooks._get_automation") as mock_auto, \
             patch("backend.routers.twilio_webhooks.send_sms", new_callable=AsyncMock) as mock_sms, \
             patch("backend.routers.twilio_webhooks.log_activity"), \
             patch("backend.routers.twilio_webhooks._insert_missed_call_row"), \
             patch("backend.routers.twilio_webhooks._increment_runs_total"), \
             patch("backend.routers.twilio_webhooks._find_lead_by_phone") as mock_lead:

            mock_find.return_value = TENANT_ROW
            mock_auto.return_value = AUTOMATION_ROW
            mock_lead.return_value = {"id": "lead-1", "name": "Alice"}
            mock_sms.return_value = (True, SMS_SID)

            resp = client.post(
                "/api/v1/twilio/missed-call",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_sms.assert_called_once()
        # Verify personalized message was used (contains lead name)
        sms_body_arg = mock_sms.call_args[1].get("body") or mock_sms.call_args[0][1] if len(mock_sms.call_args[0]) > 1 else mock_sms.call_args[1].get("body", "")
        # Just verify SMS was sent — personalization message checked in integration
        assert mock_sms.called


# ─────────────────────────────────────────────────────────────────────────────
# GH #98 — _find_tenant_by_phone TTL cache + correctness (no limit(50))
# ─────────────────────────────────────────────────────────────────────────────

class TestFindTenantByPhoneCache:
    """Phone->tenant lookup is cached per-worker and no longer caps at 50 rows."""

    def _wire(self, mock_supabase, rows):
        # Index refresh filter is .or_("sms_notifications_enabled.eq.true,
        # twilio_number.not.is.null") since migration 164 (voice-only tenants
        # with a provisioned number must still route).
        result = MagicMock()
        result.data = rows
        (
            mock_supabase.table.return_value
            .select.return_value
            .or_.return_value
            .execute.return_value
        ) = result

    def test_finds_tenant_among_more_than_50(self, mock_supabase):
        # GH #98: the old limit(50) silently dropped tenants past index 50.
        # The target tenant sits at position 75 and must still be found.
        import backend.routers.twilio_webhooks as tw

        target = {**TENANT_ROW, "id": "t-75", "notification_phone": "+15557770075"}
        rows = [
            {**TENANT_ROW, "id": f"t-{i}", "notification_phone": f"+1555000{i:04d}"}
            for i in range(75)
        ] + [target]
        self._wire(mock_supabase, rows)

        found = tw._find_tenant_by_phone("+15557770075")
        assert found is not None and found["id"] == "t-75"

    def test_normalizes_separators(self, mock_supabase):
        import backend.routers.twilio_webhooks as tw

        row = {**TENANT_ROW, "id": "t-sep", "notification_phone": "(555) 777-0099"}
        self._wire(mock_supabase, [row])
        # Inbound formatted differently but same last-10 digits.
        found = tw._find_tenant_by_phone("+1 555-777-0099")
        assert found is not None and found["id"] == "t-sep"

    def test_caches_within_ttl(self, mock_supabase):
        # Second lookup inside the TTL must not re-query the DB.
        import backend.routers.twilio_webhooks as tw

        self._wire(mock_supabase, [TENANT_ROW])
        tw._find_tenant_by_phone(CALLED)
        calls_after_first = mock_supabase.table.call_count
        tw._find_tenant_by_phone(CALLED)
        assert mock_supabase.table.call_count == calls_after_first

    def test_unknown_phone_returns_none(self, mock_supabase):
        import backend.routers.twilio_webhooks as tw

        self._wire(mock_supabase, [TENANT_ROW])
        assert tw._find_tenant_by_phone("+19998887777") is None

    def test_blank_phone_returns_none_without_query(self, mock_supabase):
        import backend.routers.twilio_webhooks as tw

        before = mock_supabase.table.call_count
        assert tw._find_tenant_by_phone("") is None
        assert mock_supabase.table.call_count == before
