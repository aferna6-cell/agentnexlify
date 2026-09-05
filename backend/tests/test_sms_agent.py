"""Tests for backend/services/sms_agent.py + the tenants.sms_agent_enabled
gate wired into backend/routers/twilio_webhooks.py POST /sms-reply.

Two layers:
  - TestSmsAgentGateEndpoint — endpoint-level: flag off preserves the
    existing 410-Gone characterization exactly; flag on routes through
    sms_agent and sends the reply via the tenant-aware send path.
  - TestHandleInboundSms — unit-level: sms_agent.handle_inbound_sms in
    isolation (STOP before AI, suppression, rate limit, handoff lockout,
    multi-turn reply, handoff-marker escalation, reply length cap).

Supabase mocked via a small FakeDB (per-table select/insert/update state) —
the shared unittest.mock.MagicMock fixture (mock_supabase) can't
distinguish "select returns []" from "insert returns a new row" on the same
table within one test, which several sms_agent code paths need.
"""

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sms_agent
from backend.services.ai_usage_guard import AIUsageReservation


# ---------------------------------------------------------------------------
# FakeDB — per-table select/insert/update state, chainable query builder
# ---------------------------------------------------------------------------


class _FakeTable:
    def __init__(self, state: dict):
        self._state = state
        self._op = None

    def select(self, *_a, **_kw):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self._state.setdefault("inserted", []).append(row)
        return self

    def update(self, values):
        self._op = "update"
        self._state.setdefault("updated", []).append(values)
        return self

    def eq(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def order(self, *_a, **_kw):
        return self

    def execute(self):
        if self._op == "select":
            if self._state.get("raise_select"):
                raise RuntimeError("fake db select raised")
            return SimpleNamespace(data=self._state.get("select_data", []))
        if self._op == "insert":
            if self._state.get("raise_insert"):
                raise RuntimeError("fake db insert raised")
            return SimpleNamespace(data=self._state.get("insert_return", [{}]))
        if self._op == "update":
            if self._state.get("raise_update"):
                raise RuntimeError("fake db update raised")
            return SimpleNamespace(data=self._state.get("update_return", []))
        return SimpleNamespace(data=[])


class FakeDB:
    """Minimal fake Supabase client — db.table(name) yields a _FakeTable
    backed by per-table state so select/insert/update behave independently
    within the same test."""

    def __init__(self, tables: dict | None = None):
        self.tables = tables or {}

    def table(self, name):
        state = self.tables.setdefault(name, {})
        return _FakeTable(state)


def _base_tables(**overrides) -> dict:
    """Default empty-ish state for every table sms_agent touches."""
    tables = {
        "conversations": {"select_data": [], "insert_return": [{"id": "conv-1", "tags": []}]},
        "leads": {"select_data": [], "insert_return": [{"id": "lead-1"}]},
        "widget_configs": {"select_data": []},
        "faq_entries": {"select_data": []},
        "business_hours": {"select_data": []},
        "chat_messages": {"select_data": [], "insert_return": [{"id": "msg-1"}]},
        "tenants": {
            "select_data": [
                {
                    "id": "tenant-1",
                    "plan": "chatbot",
                    "ai_monthly_token_alert_threshold": None,
                    "ai_monthly_token_hard_limit": None,
                }
            ]
        },
    }
    tables.update(overrides)
    return tables


TENANT = {"id": "tenant-1", "plan": "chatbot", "business_name": "Test Co"}
FROM_NUMBER = "+15555550123"
TO_NUMBER = "+15555559999"


def _patch_common(monkeypatch, *, claude_text: str = "Sure, we're open 9-5.", raise_on_claude=False):
    """Patch KB retrieval + the Claude call so no network/DB embedding calls fire."""
    async def _fake_kb(*_a, **_kw):
        return []

    monkeypatch.setattr(sms_agent, "_query_kb_articles", _fake_kb)

    if raise_on_claude:
        async def _fake_claude(*_a, **_kw):
            raise RuntimeError("boom")
    else:
        async def _fake_claude(*_a, **_kw):
            return SimpleNamespace(text=claude_text)

    monkeypatch.setattr(sms_agent, "call_claude_messages", _fake_claude)
    monkeypatch.setattr(
        sms_agent,
        "reserve_ai_tokens",
        lambda **_k: AIUsageReservation(
            allowed=True,
            tenant_id=TENANT["id"],
            period_month="2026-09-01",
            estimated_tokens=500,
            alert_threshold_tokens=640_000,
            hard_limit_tokens=800_000,
            reason="",
        ),
    )
    monkeypatch.setattr(sms_agent, "record_ai_usage", lambda **_k: None)
    monkeypatch.setattr(sms_agent, "release_ai_token_reservation", lambda *_a, **_k: None)

    async def _new_delivery(*_a, **_k):
        return True, None

    async def _noop_idempotency(*_a, **_k):
        return None

    monkeypatch.setattr(sms_agent, "check_and_record", _new_delivery)
    monkeypatch.setattr(sms_agent, "record_response", _noop_idempotency)
    monkeypatch.setattr(sms_agent, "delete_key", _noop_idempotency)


def _install_fake_escalations(monkeypatch):
    """Register a fake backend.services.escalations module so the lazy
    import in sms_agent._create_sms_escalation succeeds regardless of
    whether the real module (built by a different lane) has landed."""
    fake_mod = types.ModuleType("backend.services.escalations")
    fake_mod.create_escalation = MagicMock(return_value={"id": "esc-1"})
    monkeypatch.setitem(sys.modules, "backend.services.escalations", fake_mod)
    return fake_mod.create_escalation


# ---------------------------------------------------------------------------
# Unit tests — sms_agent.handle_inbound_sms
# ---------------------------------------------------------------------------


class TestHandleInboundSms:
    def test_stop_keyword_handled_before_ai_no_reply(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch)
        record_opt_out = MagicMock()
        monkeypatch.setattr(sms_agent.sms_compliance, "record_opt_out", record_opt_out)

        with patch.object(sms_agent, "call_claude_messages") as mock_claude:
            result = _run(
                sms_agent.handle_inbound_sms(
                    db,
                    tenant=TENANT,
                    from_number=FROM_NUMBER,
                    to_number=TO_NUMBER,
                    body="STOP",
                    provider_message_id="SM1",
                )
            )

        assert result is None
        record_opt_out.assert_called_once()
        mock_claude.assert_not_called()

    def test_start_keyword_records_opt_in_no_reply(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch)
        record_opt_in = MagicMock()
        monkeypatch.setattr(sms_agent.sms_compliance, "record_opt_in", record_opt_in)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="START",
                provider_message_id="SM2",
            )
        )

        assert result is None
        record_opt_in.assert_called_once()

    def test_suppressed_recipient_returns_none_before_ai(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: True)

        with patch.object(sms_agent, "call_claude_messages") as mock_claude:
            result = _run(
                sms_agent.handle_inbound_sms(
                    db,
                    tenant=TENANT,
                    from_number=FROM_NUMBER,
                    to_number=TO_NUMBER,
                    body="Hi, do you have openings Friday?",
                    provider_message_id="SM3",
                )
            )

        assert result is None
        mock_claude.assert_not_called()

    def test_rate_limited_returns_none_before_ai(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: False
        )

        with patch.object(sms_agent, "call_claude_messages") as mock_claude:
            result = _run(
                sms_agent.handle_inbound_sms(
                    db,
                    tenant=TENANT,
                    from_number=FROM_NUMBER,
                    to_number=TO_NUMBER,
                    body="Hello there",
                    provider_message_id="SM4",
                )
            )

        assert result is None
        mock_claude.assert_not_called()

    def test_handoff_lockout_stays_silent_and_saves_message(self, monkeypatch):
        tables = _base_tables(
            conversations={
                "select_data": [{"id": "conv-locked", "tags": ["handoff"]}],
                "insert_return": [{"id": "conv-locked", "tags": ["handoff"]}],
            }
        )
        db = FakeDB(tables)
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        save_calls = []
        monkeypatch.setattr(
            sms_agent,
            "_save_chat_messages",
            lambda tid, sid, u, a: save_calls.append((tid, sid, u, a)),
        )

        with patch.object(sms_agent, "call_claude_messages") as mock_claude:
            result = _run(
                sms_agent.handle_inbound_sms(
                    db,
                    tenant=TENANT,
                    from_number=FROM_NUMBER,
                    to_number=TO_NUMBER,
                    body="Still waiting on a reply",
                    provider_message_id="SM5",
                )
            )

        assert result is None
        mock_claude.assert_not_called()
        assert len(save_calls) == 1
        assert save_calls[0][2] == "Still waiting on a reply"
        assert save_calls[0][3] is None

    def test_multi_turn_reply_normal_saves_both_messages(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch, claude_text="We're open 9-5 Mon-Fri!")
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        save_calls = []
        monkeypatch.setattr(
            sms_agent,
            "_save_chat_messages",
            lambda tid, sid, u, a: save_calls.append((tid, sid, u, a)),
        )

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="What are your hours?",
                provider_message_id="SM6",
            )
        )

        assert result == "We're open 9-5 Mon-Fri!"
        assert len(save_calls) == 1
        assert save_calls[0][2] == "What are your hours?"
        assert save_calls[0][3] == "We're open 9-5 Mon-Fri!"
        # Lead was created since none existed
        assert db.tables["leads"]["inserted"]
        assert db.tables["leads"]["inserted"][0]["phone"] == FROM_NUMBER
        assert db.tables["leads"]["inserted"][0]["client_id"] == TENANT["id"]

    def test_reply_length_capped_under_450_chars(self, monkeypatch):
        long_text = "A" * 900
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch, claude_text=long_text)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Tell me everything",
                provider_message_id="SM7",
            )
        )

        assert result is not None
        assert len(result) <= sms_agent.SMS_MAX_CHARS

    def test_handoff_marker_triggers_escalation_and_tags_conversation(self, monkeypatch):
        tables = _base_tables()
        db = FakeDB(tables)
        _patch_common(
            monkeypatch,
            claude_text="Let me get a team member for you.\nHANDOFF_REQUESTED",
        )
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)
        create_escalation = _install_fake_escalations(monkeypatch)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="I need to talk to a real person",
                provider_message_id="SM8",
            )
        )

        assert result == sms_agent._HANDOFF_ACK
        assert "HANDOFF_REQUESTED" not in result
        create_escalation.assert_called_once()
        _, kwargs = create_escalation.call_args
        assert kwargs["client_id"] == TENANT["id"]
        assert kwargs["source"] == "sms"

        # Conversation tagged handoff via an update call.
        updates = tables["conversations"].get("updated", [])
        assert updates, "expected a conversations UPDATE tagging handoff"
        assert "handoff" in updates[-1]["tags"]

    def test_claude_failure_returns_fallback_text(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(monkeypatch, raise_on_claude=True)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Hello?",
                provider_message_id="SM9",
            )
        )

        assert result == sms_agent._CLAUDE_ERROR_FALLBACK

    def test_conversation_lookup_and_insert_raise_falls_back_to_stable_session(
        self, monkeypatch
    ):
        """Both the select and the insert on conversations blow up -- the
        function must still fall back to the stable session_id/tags shape
        and complete the turn instead of crashing."""
        tables = _base_tables(conversations={"select_data": [], "raise_select": True, "raise_insert": True})
        db = FakeDB(tables)
        _patch_common(monkeypatch, claude_text="We're open weekdays 9-5.")
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="What are your hours?",
                provider_message_id="SM10",
            )
        )

        assert result == "We're open weekdays 9-5."

    def test_handoff_tag_update_exception_swallowed_ack_still_returned(self, monkeypatch):
        """conversations.update() raising while tagging handoff must not
        break the handoff acknowledgement reply."""
        tables = _base_tables(conversations={"select_data": [], "raise_update": True})
        db = FakeDB(tables)
        _patch_common(
            monkeypatch,
            claude_text="Let me get a team member for you.\nHANDOFF_REQUESTED",
        )
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)
        _install_fake_escalations(monkeypatch)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="I need to talk to a real person",
                provider_message_id="SM11",
            )
        )

        assert result == sms_agent._HANDOFF_ACK

    def test_lead_lookup_finds_existing_lead_skips_insert(self, monkeypatch):
        tables = _base_tables(
            leads={"select_data": [{"id": "lead-99", "name": "Bob", "phone": FROM_NUMBER}]}
        )
        db = FakeDB(tables)
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Still there?",
                provider_message_id="SM12",
            )
        )

        assert result is not None
        assert not tables["leads"].get("inserted")

    def test_lead_lookup_exception_returns_none_no_insert_attempted(self, monkeypatch):
        tables = _base_tables(leads={"select_data": [], "raise_select": True})
        db = FakeDB(tables)
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Still there?",
                provider_message_id="SM13",
            )
        )

        # Lead mapping is best-effort -- the reply must still go out.
        assert result is not None
        assert not tables["leads"].get("inserted")

    def test_lead_insert_exception_still_replies(self, monkeypatch):
        tables = _base_tables(leads={"select_data": [], "raise_insert": True})
        db = FakeDB(tables)
        _patch_common(monkeypatch)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Still there?",
                provider_message_id="SM14",
            )
        )

        assert result is not None

    def test_widget_config_faq_hours_lookup_exceptions_still_replies(self, monkeypatch):
        """Grounding loads are all best-effort -- a blown-up widget_configs,
        faq_entries, or business_hours lookup must never block the reply."""
        tables = _base_tables(
            widget_configs={"select_data": [], "raise_select": True},
            faq_entries={"select_data": [], "raise_select": True},
            business_hours={"select_data": [], "raise_select": True},
        )
        db = FakeDB(tables)
        _patch_common(monkeypatch, claude_text="We can help with that!")
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Do you do custom orders?",
                provider_message_id="SM15",
            )
        )

        assert result == "We can help with that!"

    def test_kb_article_retrieval_exception_still_replies(self, monkeypatch):
        db = FakeDB(_base_tables())

        async def _fake_kb_raises(*_a, **_kw):
            raise RuntimeError("kb search exploded")

        monkeypatch.setattr(sms_agent, "_query_kb_articles", _fake_kb_raises)

        async def _fake_claude(*_a, **_kw):
            return SimpleNamespace(text="Sure, happy to help!")

        monkeypatch.setattr(sms_agent, "call_claude_messages", _fake_claude)
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="What's on the menu?",
                provider_message_id="SM16",
            )
        )

        assert result == "Sure, happy to help!"

    def test_escalation_create_raising_does_not_break_handoff_ack(self, monkeypatch):
        db = FakeDB(_base_tables())
        _patch_common(
            monkeypatch,
            claude_text="Connecting you with a team member.\nHANDOFF_REQUESTED",
        )
        monkeypatch.setattr(sms_agent.sms_compliance, "is_suppressed", lambda *a, **k: False)
        monkeypatch.setattr(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", lambda *a, **k: True
        )
        monkeypatch.setattr(sms_agent, "_save_chat_messages", lambda *a, **k: None)

        fake_mod = types.ModuleType("backend.services.escalations")
        fake_mod.create_escalation = MagicMock(side_effect=RuntimeError("escalations down"))
        monkeypatch.setitem(sys.modules, "backend.services.escalations", fake_mod)

        result = _run(
            sms_agent.handle_inbound_sms(
                db,
                tenant=TENANT,
                from_number=FROM_NUMBER,
                to_number=TO_NUMBER,
                body="Get me a human please",
                provider_message_id="SM17",
            )
        )

        assert result == sms_agent._HANDOFF_ACK


def _run(coro):
    """Run an async sms_agent call synchronously (no running loop in tests)."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Unit tests -- sms_agent.send_sms_agent_reply (BYO Twilio vs platform pool
# provider dispatch order)
# ---------------------------------------------------------------------------


class TestSendSmsAgentReply:
    def test_byo_connected_and_send_succeeds_skips_platform_send(self, monkeypatch):
        monkeypatch.setattr(sms_agent.twilio_tenant, "is_connected", lambda *_a: True)
        byo_send = AsyncMock(return_value={"success": True})
        monkeypatch.setattr(sms_agent.twilio_tenant, "send_sms_via_tenant", byo_send)
        platform_send = AsyncMock(return_value=True)
        monkeypatch.setattr(sms_agent, "send_sms", platform_send)

        result = _run(sms_agent.send_sms_agent_reply(TENANT["id"], FROM_NUMBER, "hi there"))

        assert result is True
        byo_send.assert_awaited_once_with(
            tenant_id=TENANT["id"], to=FROM_NUMBER, body="hi there"
        )
        platform_send.assert_not_called()

    def test_byo_connected_but_send_fails_falls_back_to_platform(self, monkeypatch):
        monkeypatch.setattr(sms_agent.twilio_tenant, "is_connected", lambda *_a: True)
        byo_send = AsyncMock(return_value={"success": False, "detail": "no number"})
        monkeypatch.setattr(sms_agent.twilio_tenant, "send_sms_via_tenant", byo_send)
        platform_send = AsyncMock(return_value=True)
        monkeypatch.setattr(sms_agent, "send_sms", platform_send)

        result = _run(sms_agent.send_sms_agent_reply(TENANT["id"], FROM_NUMBER, "hi there"))

        assert result is True
        byo_send.assert_awaited_once()
        platform_send.assert_awaited_once_with(
            to=FROM_NUMBER, body="hi there", tenant_id=TENANT["id"]
        )

    def test_byo_dispatch_raises_falls_back_to_platform(self, monkeypatch):
        monkeypatch.setattr(sms_agent.twilio_tenant, "is_connected", lambda *_a: True)

        async def _boom(*_a, **_kw):
            raise RuntimeError("byo dispatch exploded")

        monkeypatch.setattr(sms_agent.twilio_tenant, "send_sms_via_tenant", _boom)
        platform_send = AsyncMock(return_value=True)
        monkeypatch.setattr(sms_agent, "send_sms", platform_send)

        _run(sms_agent.send_sms_agent_reply(TENANT["id"], FROM_NUMBER, "hi there"))

        platform_send.assert_awaited_once()

    def test_byo_not_connected_uses_platform_send_directly(self, monkeypatch):
        monkeypatch.setattr(sms_agent.twilio_tenant, "is_connected", lambda *_a: False)
        byo_send = AsyncMock()
        monkeypatch.setattr(sms_agent.twilio_tenant, "send_sms_via_tenant", byo_send)
        platform_send = AsyncMock(return_value=True)
        monkeypatch.setattr(sms_agent, "send_sms", platform_send)

        _run(sms_agent.send_sms_agent_reply(TENANT["id"], FROM_NUMBER, "hi there"))

        byo_send.assert_not_called()
        platform_send.assert_awaited_once_with(
            to=FROM_NUMBER, body="hi there", tenant_id=TENANT["id"]
        )

    def test_platform_send_failure_does_not_raise(self, monkeypatch):
        """A False from the platform send_sms fallback (both providers
        exhausted) must be logged, never raised -- the webhook uses the
        bool to leave the MessageSid pending for retry."""
        monkeypatch.setattr(sms_agent.twilio_tenant, "is_connected", lambda *_a: False)
        platform_send = AsyncMock(return_value=False)
        monkeypatch.setattr(sms_agent, "send_sms", platform_send)

        result = _run(
            sms_agent.send_sms_agent_reply(TENANT["id"], FROM_NUMBER, "hi there")
        )

        assert result is False
        platform_send.assert_awaited_once()


# ---------------------------------------------------------------------------
# Endpoint-level tests — tenants.sms_agent_enabled gate in twilio_webhooks.py
# ---------------------------------------------------------------------------


def _make_form_body(*, from_number=FROM_NUMBER, to_number=TO_NUMBER, msg_body="Hi there", sid="SM-test"):
    from urllib.parse import urlencode

    return urlencode(
        {"From": from_number, "To": to_number, "Body": msg_body, "MessageSid": sid}
    ).encode()


def _patch_sig_verify(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.twilio_webhooks._verify_twilio_signature",
        lambda request, body: True,
    )


class TestSmsAgentGateEndpoint:
    def test_flag_off_returns_410_same_as_before(self, client, mock_supabase, monkeypatch):
        """No matching tenant (default legacy path) -> 410, unchanged."""
        _patch_sig_verify(monkeypatch)
        with patch(
            "backend.routers.twilio_webhooks._find_tenant_by_phone", return_value=None
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.handle_inbound_sms",
            new_callable=AsyncMock,
        ) as mock_agent:
            resp = client.post(
                "/api/v1/twilio/sms-reply",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 410
        mock_agent.assert_not_called()

    def test_flag_explicitly_false_returns_410(self, client, mock_supabase, monkeypatch):
        """Tenant exists but sms_agent_enabled=False (or missing) -> 410, unchanged."""
        _patch_sig_verify(monkeypatch)
        tenant = {**TENANT, "sms_agent_enabled": False}
        with patch(
            "backend.routers.twilio_webhooks._find_tenant_by_phone", return_value=tenant
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.handle_inbound_sms",
            new_callable=AsyncMock,
        ) as mock_agent:
            resp = client.post(
                "/api/v1/twilio/sms-reply",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 410
        mock_agent.assert_not_called()

    def test_bad_signature_still_403_regardless_of_flag(self, client, mock_supabase, monkeypatch):
        monkeypatch.setattr(
            "backend.routers.twilio_webhooks._verify_twilio_signature",
            lambda request, body: False,
        )
        resp = client.post(
            "/api/v1/twilio/sms-reply",
            content=_make_form_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 403

    def test_flag_on_routes_through_agent_and_sends_reply(self, client, mock_supabase, monkeypatch):
        _patch_sig_verify(monkeypatch)
        tenant = {**TENANT, "sms_agent_enabled": True}
        with patch(
            "backend.routers.twilio_webhooks._find_tenant_by_phone", return_value=tenant
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.handle_inbound_sms",
            new_callable=AsyncMock,
            return_value="We're open until 5pm!",
        ) as mock_agent, patch(
            "backend.routers.twilio_webhooks.sms_agent.send_sms_agent_reply",
            new_callable=AsyncMock,
        ) as mock_send:
            resp = client.post(
                "/api/v1/twilio/sms-reply",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        assert resp.text == "OK"
        mock_agent.assert_called_once()
        call_kwargs = mock_agent.call_args.kwargs
        assert call_kwargs["tenant"] == tenant
        assert call_kwargs["from_number"] == FROM_NUMBER
        assert call_kwargs["to_number"] == TO_NUMBER
        assert call_kwargs["body"] == "Hi there"
        mock_send.assert_called_once_with(tenant["id"], FROM_NUMBER, "We're open until 5pm!")

    def test_flag_on_agent_returns_none_no_send_no_error(self, client, mock_supabase, monkeypatch):
        """Agent stays silent (e.g. STOP, handoff lockout) -> no outbound send, still 200 OK."""
        _patch_sig_verify(monkeypatch)
        tenant = {**TENANT, "sms_agent_enabled": True}
        with patch(
            "backend.routers.twilio_webhooks._find_tenant_by_phone", return_value=tenant
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.handle_inbound_sms",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.send_sms_agent_reply",
            new_callable=AsyncMock,
        ) as mock_send:
            resp = client.post(
                "/api/v1/twilio/sms-reply",
                content=_make_form_body(msg_body="STOP"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        assert resp.text == "OK"
        mock_send.assert_not_called()

    def test_flag_on_agent_raises_falls_back_to_ok_no_crash(self, client, mock_supabase, monkeypatch):
        """sms_agent raising unexpectedly must not 500 the Twilio webhook."""
        _patch_sig_verify(monkeypatch)
        tenant = {**TENANT, "sms_agent_enabled": True}
        with patch(
            "backend.routers.twilio_webhooks._find_tenant_by_phone", return_value=tenant
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.handle_inbound_sms",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ), patch(
            "backend.routers.twilio_webhooks.sms_agent.send_sms_agent_reply",
            new_callable=AsyncMock,
        ) as mock_send:
            resp = client.post(
                "/api/v1/twilio/sms-reply",
                content=_make_form_body(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 200
        mock_send.assert_not_called()
