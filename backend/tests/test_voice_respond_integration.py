"""Integration tests for POST /api/v1/calls/voice/respond.

Drives the full webhook through the ASGI app (slowapi limiter needs a real
Starlette Request), same strategy as test_voice_incoming_call.py:
signature dependency overridden, Supabase singleton is the conftest MagicMock,
tenant routing / LLM / KB / booking internals patched at module boundaries.

Covers the G3 Phase 1 hooks that unit tests can't reach:
  - normal reply round returns <Gather> TwiML with the AI text
  - booking intent injects slots into the system prompt and a BOOK_JSON
    marker in Claude's reply books the appointment + confirms aloud
  - KB grounding lands in the system prompt
  - round cap ends the call with goodbye TwiML (+ inline finalize)
  - missing speech / unknown tenant return safe goodbyes
"""

import os
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.main import app
from backend.routers.automations import verify_twilio_request
from backend.tests.conftest import SyncASGITestClient

_ENDPOINT = "/api/v1/calls/voice/respond"
_CALLER = "+15555550100"
_CALLED = "+15555550200"
_CALL_SID = "CAtest_respond_001"
_TENANT_ID = "00000000-0000-0000-0000-000000000099"

_TENANT = {
    "id": _TENANT_ID,
    "business_name": "Test Plumbing",
    "business_type": "plumber",
    "owner_email": "owner@testplumbing.com",
    "notification_phone": _CALLED,
    "plan": "agent_os",
    "voice_ai_enabled": True,
}


def _llm_result(text):
    result = MagicMock()
    result.text = text
    result.duration_ms = 12
    return result


def _post(client, speech, round_num=1):
    body = urllib.parse.urlencode(
        {
            "SpeechResult": speech,
            "CallSid": _CALL_SID,
            "From": _CALLER,
            "To": _CALLED,
        }
    )
    return client.post(
        f"{_ENDPOINT}?round={round_num}",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.fixture(autouse=True)
def _bypass_twilio_signature():
    app.dependency_overrides[verify_twilio_request] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(verify_twilio_request, None)


@pytest.fixture()
def respond_client(mock_supabase):
    """ASGI client + permissive per-table DB chains."""

    def _chain(rows):
        result = MagicMock()
        result.data = rows
        chain = MagicMock()
        for m in ("select", "eq", "order", "limit", "insert", "update", "gte", "lt"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = result
        return chain

    tables = {
        "chat_messages": _chain([]),
        "tenants": _chain([_TENANT]),
        "faq_entries": _chain([{"question": "Hours?", "answer": "9-5 weekdays"}]),
        "widget_configs": _chain([{"booking_enabled": True}]),
    }
    mock_supabase.table.side_effect = lambda name: tables.get(name, _chain([]))

    client = SyncASGITestClient(app)
    try:
        yield client, tables
    finally:
        client.close()


def _base_patches(llm_text, kb_articles=None):
    """Common patch set: tenant routing, LLM, KB retrieval, vertical guidance."""
    return (
        patch("backend.routers.calls._find_tenant_by_phone", return_value=_TENANT),
        patch(
            "backend.routers.calls.call_claude_messages",
            new=AsyncMock(return_value=_llm_result(llm_text)),
        ),
        patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=kb_articles or []),
        ),
        patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]),
    )


class TestRespondBasics:
    def test_normal_round_returns_gather_with_ai_text(self, respond_client):
        client, _ = respond_client
        p1, p2, p3, p4 = _base_patches("We are open nine to five on weekdays.")
        with p1, p2, p3, p4:
            resp = _post(client, "what are your hours")
        assert resp.status_code == 200
        assert "<Gather" in resp.text
        assert "nine to five" in resp.text

    def test_missing_speech_ends_gracefully(self, respond_client):
        client, _ = respond_client
        resp = _post(client, "")
        assert resp.status_code == 200
        assert "<Gather" not in resp.text
        assert "Goodbye" in resp.text

    def test_unknown_tenant_ends_gracefully(self, respond_client):
        client, _ = respond_client
        with patch("backend.routers.calls._find_tenant_by_phone", return_value=None):
            resp = _post(client, "hello")
        assert resp.status_code == 200
        assert "<Gather" not in resp.text

    def test_round_cap_returns_goodbye_and_finalizes(self, respond_client):
        client, _ = respond_client
        p1, p2, p3, p4 = _base_patches("Thanks for the chat.")
        with p1, p2, p3, p4, patch(
            "backend.routers.calls._finalize_ai_call", new=AsyncMock()
        ) as finalize, patch(
            "backend.services.voice_booking.booking_prompt_context", return_value=None
        ):
            resp = _post(client, "ok thanks bye", round_num=3)
        assert resp.status_code == 200
        assert "<Gather" not in resp.text
        assert "Goodbye" in resp.text
        finalize.assert_awaited_once()


class TestKbGrounding:
    def test_kb_summaries_land_in_system_prompt(self, respond_client):
        client, _ = respond_client
        llm = AsyncMock(return_value=_llm_result("A burst pipe needs the main valve off."))
        articles = [
            {"title": "Burst pipe first steps", "summary": "Shut off the main water valve."}
        ]
        with patch(
            "backend.routers.calls._find_tenant_by_phone", return_value=_TENANT
        ), patch("backend.routers.calls.call_claude_messages", new=llm), patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=articles),
        ), patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]):
            resp = _post(client, "my pipe burst what do I do")
        assert resp.status_code == 200
        system_prompt = llm.await_args.kwargs["system"]
        assert "Knowledge base:" in system_prompt
        assert "Shut off the main water valve" in system_prompt


class TestBookingFlow:
    _SLOT = {
        "start": "09:00",
        "end": "09:30",
        "start_utc": "2026-07-14T13:00:00+00:00",
        "end_utc": "2026-07-14T13:30:00+00:00",
    }

    def test_booking_intent_injects_slots_into_prompt(self, respond_client):
        client, tables = respond_client
        tables["chat_messages"].execute.return_value.data = [
            {"role": "user", "content": "can I book an appointment tomorrow"}
        ]
        llm = AsyncMock(return_value=_llm_result("I can book you in at 9 AM."))
        with patch(
            "backend.routers.calls._find_tenant_by_phone", return_value=_TENANT
        ), patch("backend.routers.calls.call_claude_messages", new=llm), patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ), patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]), patch(
            "backend.services.voice_booking.generate_available_slots",
            return_value=[self._SLOT],
        ):
            resp = _post(client, "can I book an appointment tomorrow")
        assert resp.status_code == 200
        system_prompt = llm.await_args.kwargs["system"]
        assert "APPOINTMENT BOOKING" in system_prompt
        assert "BOOK_JSON" in system_prompt

    def test_marker_reply_books_and_confirms_aloud(self, respond_client):
        client, tables = respond_client
        tables["chat_messages"].execute.return_value.data = [
            {"role": "user", "content": "book me for nine tomorrow, this is Jane Doe"}
        ]
        marker_reply = (
            "Perfect, Jane. "
            'BOOK_JSON: {"name": "Jane Doe", "date": "2026-07-14", "start": "09:00"}'
        )
        appt = {"id": "appt-1", "lead_id": None}
        with patch(
            "backend.routers.calls._find_tenant_by_phone", return_value=_TENANT
        ), patch(
            "backend.routers.calls.call_claude_messages",
            new=AsyncMock(return_value=_llm_result(marker_reply)),
        ), patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ), patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]), patch(
            "backend.services.voice_booking.generate_available_slots",
            return_value=[self._SLOT],
        ), patch(
            "backend.services.voice_booking.create_appointment", return_value=appt
        ) as create:
            resp = _post(client, "book me for nine tomorrow, this is Jane Doe")
        assert resp.status_code == 200
        # Marker never spoken; confirmation is
        assert "BOOK_JSON" not in resp.text
        assert "booked and confirmed" in resp.text
        create.assert_called_once()
        assert create.call_args.kwargs["customer_phone"] == _CALLER

    def test_booking_flow_raises_round_cap_floor(self, respond_client):
        client, tables = respond_client
        tables["chat_messages"].execute.return_value.data = [
            {"role": "user", "content": "I want to book an appointment"}
        ]
        p1, p2, p3, p4 = _base_patches("Which time works for you?")
        with p1, p2, p3, p4, patch(
            "backend.services.voice_booking.generate_available_slots",
            return_value=[self._SLOT],
        ):
            # Round 3 would end a non-booking call; booking floors the cap at 5
            resp = _post(client, "I want to book an appointment", round_num=3)
        assert resp.status_code == 200
        assert "<Gather" in resp.text
