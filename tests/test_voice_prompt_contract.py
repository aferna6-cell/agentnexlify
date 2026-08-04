"""Voice AI prompt-contract evals — the quality guard for live phone answering.

Deterministic tests pinning what the phone AI is TOLD (system prompt
composition: business identity, vertical guidance, lead-capture directive,
tenant FAQs), how the call flow behaves (Gather loop, max-rounds finalize),
and the safety contracts (XML escaping of model output, graceful TwiML on
Claude failure). Claude is mocked — these eval the prompt + mechanics, not
model output.
"""

import os

os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch, AsyncMock
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.services.voice_twiml import MAX_VOICE_ROUNDS

settings.twilio_auth_token = None  # bypass Twilio signature verification

client = TestClient(app)


def _table_mock(db_mock, table_responses):
    def mock_table(name):
        data = table_responses.get(name, [])
        table = MagicMock()
        for method in [
            "select",
            "insert",
            "update",
            "eq",
            "neq",
            "gte",
            "lte",
            "limit",
            "order",
            "in_",
            "is_",
        ]:
            getattr(table, method).return_value = table
        result = MagicMock()
        result.data = data
        result.count = len(data)
        table.execute.return_value = result
        return table

    db_mock.table = mock_table


def _respond(round_num=1, speech="I have a leaking water heater."):
    form_data = urlencode(
        {
            "SpeechResult": speech,
            "CallSid": "CA-contract-001",
            "From": "+15559998888",
            "To": "+15551234567",
        }
    )
    return client.post(
        f"/api/v1/calls/voice/respond?round={round_num}",
        content=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _tenant(business_type, business_name):
    return {
        "id": "tenant-001",
        "business_name": business_name,
        "business_type": business_type,
        "plan": "professional",
        "voice_ai_enabled": True,
    }


def _tables(business_type, business_name, faqs=None):
    return {
        "chat_messages": [{"role": "user", "content": "hello"}],
        "tenants": [
            {
                "business_name": business_name,
                "business_type": business_type,
                "owner_email": "owner@example.com",
            }
        ],
        "faq_entries": faqs or [],
    }


class TestPromptContract:
    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_plumbing_tenant_gets_trade_guidance_and_lead_directive(
        self, mock_find, mock_db, mock_claude
    ):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("plumbing", "Acme Plumbing"))
        mock_claude.return_value = MagicMock(text="Happy to help.", duration_ms=80)

        resp = _respond()
        assert resp.status_code == 200

        kwargs = mock_claude.await_args.kwargs
        system = kwargs["system"]
        # Business identity
        assert "Acme Plumbing" in system
        # Lead-capture directive (exact contract from calls.py)
        assert "collect their name" in system
        assert "the best time to reach them" in system
        # Vertical guidance: home_services pack reaches the phone AI
        assert "Operating guidance:" in system
        from backend.services.os_kb_feed import vertical_guidance

        first_pack_answer = vertical_guidance("plumbing")[0]["answer"][:120]
        assert first_pack_answer[:60] in system

    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_salon_tenant_gets_salon_guidance_not_contractor_guidance(
        self, mock_find, mock_db, mock_claude
    ):
        mock_find.return_value = _tenant("salon", "Luxe Salon")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("salon", "Luxe Salon"))
        mock_claude.return_value = MagicMock(text="Happy to help.", duration_ms=80)

        resp = _respond(speech="Do you have any openings for a haircut?")
        assert resp.status_code == 200

        system = mock_claude.await_args.kwargs["system"]
        from backend.services.os_kb_feed import vertical_guidance

        salon_first = vertical_guidance("salon")[0]["answer"][:60]
        contractor_first = vertical_guidance("plumbing")[0]["answer"][:60]
        assert salon_first in system
        assert contractor_first not in system

    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_tenant_faqs_reach_the_prompt(self, mock_find, mock_db, mock_claude):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(
            db,
            _tables(
                "plumbing",
                "Acme Plumbing",
                faqs=[
                    {
                        "question": "Do you serve Riverside?",
                        "answer": "Yes, the whole metro.",
                    }
                ],
            ),
        )
        mock_claude.return_value = MagicMock(text="Happy to help.", duration_ms=80)

        _respond()
        system = mock_claude.await_args.kwargs["system"]
        assert "Frequently Asked Questions:" in system
        assert "Do you serve Riverside?" in system
        assert "Yes, the whole metro." in system


class TestSafetyContract:
    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_model_output_is_xml_escaped_into_twiml(
        self, mock_find, mock_db, mock_claude
    ):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("plumbing", "Acme Plumbing"))
        # A hostile/buggy model reply trying to break out of <Say> and dial out
        mock_claude.return_value = MagicMock(
            text="Sure! </Say><Dial>+15550000000</Dial><Say>", duration_ms=80
        )

        resp = _respond()
        assert resp.status_code == 200
        assert "<Dial>" not in resp.text
        assert "&lt;Dial&gt;" in resp.text

    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_claude_failure_returns_graceful_twiml_not_5xx(
        self, mock_find, mock_db, mock_claude
    ):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("plumbing", "Acme Plumbing"))
        mock_claude.side_effect = RuntimeError("api down")

        resp = _respond()
        # Twilio must always get valid TwiML — a 5xx drops the live call
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "having a little trouble" in resp.text
        assert "call you back" in resp.text


class TestFlowContract:
    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_mid_conversation_round_gathers_with_next_round(
        self, mock_find, mock_db, mock_claude
    ):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("plumbing", "Acme Plumbing"))
        mock_claude.return_value = MagicMock(
            text="What is your address?", duration_ms=80
        )

        resp = _respond(round_num=1)
        assert "<Gather" in resp.text
        assert "round=2" in resp.text

    @patch("backend.routers.calls_webhooks._finalize_ai_call", new_callable=AsyncMock)
    @patch(
        "backend.routers.calls_webhooks.call_claude_messages", new_callable=AsyncMock
    )
    @patch("backend.routers.calls_webhooks.get_service_supabase")
    @patch("backend.routers.calls_webhooks._find_tenant_by_phone")
    def test_max_rounds_says_goodbye_and_finalizes(
        self, mock_find, mock_db, mock_claude, mock_finalize
    ):
        mock_find.return_value = _tenant("plumbing", "Acme Plumbing")
        db = MagicMock()
        mock_db.return_value = db
        _table_mock(db, _tables("plumbing", "Acme Plumbing"))
        mock_claude.return_value = MagicMock(
            text="Someone will call you back.", duration_ms=80
        )

        resp = _respond(round_num=MAX_VOICE_ROUNDS)
        assert resp.status_code == 200
        assert "<Gather" not in resp.text
        assert "Goodbye" in resp.text
        mock_finalize.assert_awaited_once()
