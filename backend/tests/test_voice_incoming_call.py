"""Integration tests for handle_incoming_call (POST /api/v1/calls/voice/incoming).

Strategy
--------
- Route is wrapped by ``@limiter.limit("30/minute")`` (slowapi), which requires
  a real Starlette Request.  We use ``SyncASGITestClient`` (from conftest) that
  drives the ASGI app through ``httpx.ASGITransport`` — the same approach used
  by every other webhook test in this suite.
- Twilio signature dependency (``verify_twilio_request``) is bypassed via
  ``app.dependency_overrides`` so no live Twilio credentials are needed.
- DB calls are intercepted by the autouse ``_stub_supabase_singletons`` fixture
  (from conftest) which seeds ``backend.models.database._service_client`` with a
  MagicMock before any test runs.
- ``_find_tenant_by_phone`` calls ``get_service_supabase()`` at runtime and
  chains: ``.table().select().limit().execute()``.  Each test wires this chain
  individually to control which tenant row (or empty list) is returned.
- No LLM calls, no live Twilio, no live DB.

Scenarios covered
-----------------
1. Unknown caller (no matching tenant) → safe ``<Say>`` TwiML, HTTP 200.
2. Known tenant, voicemail mode (chatbot plan, voice_ai_enabled False) → ``<Record>`` TwiML.
3. Known tenant, AI mode (agent_os, voice_ai_enabled True) → ``<Gather input="speech">`` TwiML.
4. AI mode + DB failure during call-open → still returns valid ``<Gather>`` TwiML (graceful).

NOT covered here (already in test_voice_plan_gate.py)
------------------------------------------------------
- _ai_voice_mode() logic / _AI_VOICE_PLANS membership.
"""

import os
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# TESTING must be set before any backend import (conftest already sets it, but
# belt-and-braces for standalone execution).
os.environ.setdefault("TESTING", "1")

from backend.main import app
from backend.routers.automations import verify_twilio_request
from backend.tests.conftest import SyncASGITestClient


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENDPOINT = "/api/v1/calls/voice/incoming"
_CALLER = "+15555550100"
_CALLED = "+15555550200"
_CALL_SID = "CAtest_incoming_001"
_TENANT_ID = "00000000-0000-0000-0000-000000000099"

_TENANT_VOICEMAIL = {
    "id": _TENANT_ID,
    "business_name": "Test Plumbing",
    "business_type": "plumber",
    "owner_email": "owner@testplumbing.com",
    "notification_phone": _CALLED,
    "sms_notifications_enabled": True,
    "plan": "chatbot",
    "voice_ai_enabled": False,
}

_TENANT_AI_MODE = {
    **_TENANT_VOICEMAIL,
    "plan": "agent_os",
    "voice_ai_enabled": True,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_form_body(
    caller: str = _CALLER,
    called: str = _CALLED,
    call_sid: str = _CALL_SID,
) -> bytes:
    """Build a URL-encoded Twilio voice webhook body."""
    return urllib.parse.urlencode(
        {"From": caller, "To": called, "CallSid": call_sid}
    ).encode()


def _make_client() -> SyncASGITestClient:
    return SyncASGITestClient(app)


def _wire_tenant_lookup(mock_supabase, tenant_row: dict | None) -> None:
    """Wire mock_supabase so _find_tenant_by_phone returns the given row (or nothing).

    _find_tenant_by_phone (G3 Phase 2) runs two queries:
        exact:    db.table("tenants").select(...).eq("twilio_number", ...).limit(1).execute()
        fallback: db.table("tenants").select(...).range(a, b).execute()  (paginated scan)
    These tenants have no twilio_number, so the exact path returns empty and
    the suffix scan matches on notification_phone - same contract as before.
    (Fallback wiring switched from .limit(200) to .range() when the silent
    200-row cap was removed - audit 2026-07-14 L4. The contracts asserted by
    these tests - greeting/TwiML/matching - are unchanged.)
    """
    exact_result = MagicMock()
    exact_result.data = []
    scan_result = MagicMock()
    scan_result.data = [tenant_row] if tenant_row else []
    select_chain = mock_supabase.table.return_value.select.return_value
    (
        select_chain
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = exact_result
    (
        select_chain
        .range.return_value
        .execute.return_value
    ) = scan_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bypass_twilio_sig():
    """Override the verify_twilio_request dependency for all tests in this module.

    verify_twilio_request is imported into backend.routers.calls_webhooks and used as a
    FastAPI Depends().  app.dependency_overrides replaces the resolved value
    so the HMAC-SHA1 check is skipped.
    """
    app.dependency_overrides[verify_twilio_request] = lambda: None
    yield
    app.dependency_overrides.pop(verify_twilio_request, None)


# ---------------------------------------------------------------------------
# Test 1: Unknown caller — no matching tenant
# ---------------------------------------------------------------------------


class TestUnknownCaller:
    def test_returns_200_with_twiml_say(self, mock_supabase):
        """No matching tenant → safe <Say> error TwiML, never a 500."""
        _wire_tenant_lookup(mock_supabase, None)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        body = resp.text
        assert "<Response>" in body
        assert "<Say" in body
        # Must NOT be a JSON error payload or HTML traceback
        assert "traceback" not in body.lower()
        assert "500" not in body
        assert resp.headers["content-type"].startswith("application/xml")

    def test_response_is_valid_twiml_xml(self, mock_supabase):
        """Response must be parseable XML (Twilio rejects malformed TwiML)."""
        import xml.etree.ElementTree as ET

        _wire_tenant_lookup(mock_supabase, None)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        # Will raise if the XML is malformed
        ET.fromstring(resp.text)


# ---------------------------------------------------------------------------
# Test 2: Voicemail mode — chatbot plan / voice_ai_enabled False
# ---------------------------------------------------------------------------


class TestVoicemailMode:
    def test_returns_record_verb(self, mock_supabase):
        """voicemail-mode tenant → TwiML with <Record>."""
        _wire_tenant_lookup(mock_supabase, _TENANT_VOICEMAIL)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        body = resp.text
        assert "<Record" in body
        # Must not be AI mode (no <Gather> for speech)
        assert 'input="speech"' not in body
        assert resp.headers["content-type"].startswith("application/xml")

    def test_response_is_valid_xml(self, mock_supabase):
        import xml.etree.ElementTree as ET

        _wire_tenant_lookup(mock_supabase, _TENANT_VOICEMAIL)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        ET.fromstring(resp.text)

    def test_includes_business_name_in_greeting(self, mock_supabase):
        """Voicemail greeting references the tenant's business name."""
        _wire_tenant_lookup(mock_supabase, _TENANT_VOICEMAIL)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert "Test Plumbing" in resp.text


# ---------------------------------------------------------------------------
# Test 3: AI mode — agent_os + voice_ai_enabled True
# ---------------------------------------------------------------------------


class TestAIMode:
    def _wire_ai_mode(self, mock_supabase):
        """Wire tenant lookup for AI-mode tenant.

        In AI mode handle_incoming_call also calls:
          db.table("leads").select(...).eq(...).eq(...).limit(1).execute()  — find lead
          db.table("leads").insert(...).execute()                           — create lead
          db.table("calls").insert(...).execute()                           — open call record
          db.table("chat_messages").insert(...).execute()                   — save greeting

        We use a side_effect chain so the tenant lookup (table="tenants") returns
        the tenant row, and all other table calls return empty-but-safe results.
        """
        tenant_result = MagicMock()
        tenant_result.data = [_TENANT_AI_MODE]

        lead_select_result = MagicMock()
        lead_select_result.data = []  # no existing lead

        lead_insert_result = MagicMock()
        lead_insert_result.data = [{"id": "lead-001"}]

        call_insert_result = MagicMock()
        call_insert_result.data = [{"id": "call-001"}]

        chat_insert_result = MagicMock()
        chat_insert_result.data = []

        # All table() calls return the same mock chain; we differentiate via
        # a side_effect on table() itself — simpler than trying to chain per-table.
        # The _find_tenant_by_phone chain is:
        #   .table("tenants").select(...).limit(50).execute()
        # _find_or_create_lead chain is (select path):
        #   .table("leads").select(...).eq(...).eq(...).limit(1).execute()
        # _find_or_create_lead chain is (insert path):
        #   .table("leads").insert(...).execute()
        # calls insert:
        #   .table("calls").insert(...).execute()
        # chat_messages insert:
        #   .table("chat_messages").insert(...).execute()
        #
        # We use a counter-based side_effect so calls arrive in the order
        # the endpoint actually makes them.

        exact_empty = MagicMock()
        exact_empty.data = []  # twilio_number exact match misses (no provisioned number)

        call_count = {"n": 0}
        results_by_order = [
            # 1st table() call — tenants exact twilio_number lookup (G3 Phase 2)
            exact_empty,
            # 2nd — tenants suffix-scan fallback in _find_tenant_by_phone
            tenant_result,
            # 3rd — leads select in _find_or_create_lead
            lead_select_result,
            # 4th — leads insert in _find_or_create_lead
            lead_insert_result,
            # 5th — calls insert
            call_insert_result,
            # 6th — chat_messages insert
            chat_insert_result,
        ]

        def _table_side_effect(name):
            idx = call_count["n"]
            call_count["n"] += 1
            mock_chain = MagicMock()
            # Whichever terminal .execute() is called, return the right result
            if idx < len(results_by_order):
                target = results_by_order[idx]
            else:
                target = MagicMock()
                target.data = []
            # Wire all common chains to the result
            mock_chain.select.return_value.limit.return_value.execute.return_value = target
            mock_chain.select.return_value.range.return_value.execute.return_value = target
            mock_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = target
            mock_chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = target
            mock_chain.insert.return_value.execute.return_value = target
            return mock_chain

        mock_supabase.table.side_effect = _table_side_effect

    def test_returns_gather_speech(self, mock_supabase):
        """AI-mode tenant → TwiML with <Gather input=\"speech\">."""
        self._wire_ai_mode(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        body = resp.text
        assert 'input="speech"' in body
        assert "<Gather" in body
        assert "<Say" in body
        assert resp.headers["content-type"].startswith("application/xml")

    def test_response_is_valid_xml(self, mock_supabase):
        import xml.etree.ElementTree as ET

        self._wire_ai_mode(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        ET.fromstring(resp.text)

    def test_greeting_includes_business_name(self, mock_supabase):
        self._wire_ai_mode(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert "Test Plumbing" in resp.text

    def test_respond_url_points_to_correct_endpoint(self, mock_supabase):
        """The <Gather> action URL must point to the /voice/respond endpoint."""
        self._wire_ai_mode(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert "/api/v1/calls/voice/respond" in resp.text


# ---------------------------------------------------------------------------
# Test 4: AI mode + DB failure during call-open → graceful fallback TwiML
# ---------------------------------------------------------------------------


class TestAIModeDBFailure:
    """DB failure during call-record creation must NOT return a 500 to Twilio.

    The endpoint has explicit try/except blocks around the DB calls in AI mode
    (lines 269-319 of calls.py).  If get_service_supabase() itself throws, the
    outer try/except at line 269 catches it, logs it, and the code still falls
    through to build and return TwiML with <Gather>.
    """

    def _wire_db_failure(self, mock_supabase):
        """Tenant lookup succeeds; every subsequent DB call raises."""
        tenant_result = MagicMock()
        tenant_result.data = [_TENANT_AI_MODE]

        call_count = {"n": 0}

        exact_empty = MagicMock()
        exact_empty.data = []

        def _table_side_effect(name):
            idx = call_count["n"]
            call_count["n"] += 1
            if idx == 0:
                # First call — exact twilio_number lookup misses (G3 Phase 2)
                mock_chain = MagicMock()
                mock_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = exact_empty
                return mock_chain
            elif idx == 1:
                # Second call — suffix-scan tenant lookup, must succeed
                mock_chain = MagicMock()
                mock_chain.select.return_value.limit.return_value.execute.return_value = tenant_result
                return mock_chain
            else:
                # All subsequent DB calls raise (simulates DB outage mid-call)
                raise RuntimeError("DB connection lost")

        mock_supabase.table.side_effect = _table_side_effect

    def test_db_failure_still_returns_twiml(self, mock_supabase):
        """DB failure during AI-mode setup → valid TwiML <Gather>, not 500."""
        self._wire_db_failure(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Must NEVER be a 500
        assert resp.status_code == 200
        body = resp.text
        # Must be valid TwiML with Gather (AI greeting)
        assert "<Response>" in body
        assert "<Gather" in body or "<Say" in body
        # Must not be Python traceback / HTML error page
        assert "traceback" not in body.lower()
        assert resp.headers["content-type"].startswith("application/xml")

    def test_db_failure_response_is_valid_xml(self, mock_supabase):
        import xml.etree.ElementTree as ET

        self._wire_db_failure(mock_supabase)
        client = _make_client()

        resp = client.post(
            _ENDPOINT,
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert resp.status_code == 200
        ET.fromstring(resp.text)
