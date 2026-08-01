"""Tests for inbound-email AI triage (Phase 2 — Gmail connector + triage).

Contracts:
  - spam / info_only -> tag the OS thread, stop (no draft, no send)
  - escalate -> hands off via the escalations lane wrapper
  - answerable -> drafts a grounded reply; auto-sends only when the
    deliverable-status gate resolves 'approved' (tenant opt-in AND
    confidence clears the bar), otherwise stores a pending_approval
    deliverable on os_agent_runs (same shape the dashboard already renders)
  - a low-confidence or failed draft escalates instead of guessing
  - the escalations-lane import is lazy + best-effort: missing module logs
    and returns None rather than raising
"""

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import inbox_triage
from backend.tests.fake_supabase import db as fake_db

TENANT_ID = "00000000-0000-0000-0000-000000000001"
OS_THREAD_ID = "thread-abc"


def _parsed_email(**overrides):
    base = {
        "provider_message_id": "msg-1",
        "thread_id": "gmail-thread-1",
        "sender_email": "customer@example.com",
        "sender_name": "Customer",
        "recipient": "support@tenant.com",
        "subject": "Do you open on weekends?",
        "body_text": "Hey, are you open Saturdays?",
        "headers": {},
    }
    base.update(overrides)
    return base


def _classify_result(category, confidence=0.9, reason="ok"):
    import json

    return SimpleNamespace(
        text=json.dumps({"category": category, "confidence": confidence, "reason": reason})
    )


def _draft_result(answer="We're open 9-5 Saturdays.", confidence="high", escalate_reason=None):
    import json

    return SimpleNamespace(
        text=json.dumps(
            {"answer": answer, "confidence": confidence, "escalate_reason": escalate_reason}
        )
    )


def _std_db():
    return fake_db(
        {
            "os_agent_runs": [{"id": "run-1"}],
            "os_threads": [{"source_metadata": {}}],
            "os_action_runs": [{"id": "action-1"}],
        }
    )


# ---------------------------------------------------------------------------
# spam / info_only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spam_tags_thread_and_stops(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage, "call_claude_messages", AsyncMock(return_value=_classify_result("spam"))
    )
    draft_mock = AsyncMock()
    monkeypatch.setattr(inbox_triage, "_draft_reply", draft_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["category"] == "spam"
    assert result["action"] == "tagged"
    draft_mock.assert_not_called()
    # tag_thread issued an update call against os_threads
    assert any(call[0] == "os_threads" and call[1] == "update" for call in db._sink)


@pytest.mark.asyncio
async def test_info_only_tags_thread_and_stops(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("info_only")),
    )

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["category"] == "info_only"
    assert result["action"] == "tagged"


# ---------------------------------------------------------------------------
# escalate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classifier_escalate_calls_escalation_wrapper(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("escalate", reason="angry customer")),
    )
    escalate_mock = MagicMock(return_value={"id": "esc-1"})
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["category"] == "escalate"
    assert result["action"] == "escalated"
    assert result["escalation"] == {"id": "esc-1"}
    escalate_mock.assert_called_once()
    kwargs = escalate_mock.call_args.kwargs
    assert kwargs["client_id"] == TENANT_ID
    assert kwargs["os_thread_id"] == OS_THREAD_ID
    assert kwargs["reason"] == "angry customer"


@pytest.mark.asyncio
async def test_classify_call_failure_escalates(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage, "call_claude_messages", AsyncMock(side_effect=RuntimeError("api down"))
    )
    escalate_mock = MagicMock(return_value=None)
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "escalated"
    assert result["reason"] == "classification_failed"
    escalate_mock.assert_called_once()


# ---------------------------------------------------------------------------
# answerable — draft + auto-send gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answerable_low_confidence_stores_pending_draft(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(
            side_effect=[
                _classify_result("answerable", confidence=0.5),
            ]
        ),
    )
    monkeypatch.setattr(
        inbox_triage,
        "_draft_reply",
        AsyncMock(return_value={"answer": "We're open Saturdays.", "confidence": "medium", "escalate_reason": None}),
    )
    resolve_mock = MagicMock(return_value="pending_approval")
    monkeypatch.setattr(inbox_triage, "resolve_deliverable_status", resolve_mock)
    send_reply_mock = MagicMock()
    monkeypatch.setattr(inbox_triage.gmail_connector, "send_reply", send_reply_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["category"] == "answerable"
    assert result["action"] == "drafted"
    assert result["agent_run_id"] == "run-1"
    send_reply_mock.assert_not_called()
    # requires_approval=True was passed because auto_send_ok was False
    assert resolve_mock.call_args.kwargs["requires_approval"] is True


@pytest.mark.asyncio
async def test_answerable_high_confidence_auto_sends(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("answerable", confidence=0.95)),
    )
    monkeypatch.setattr(
        inbox_triage,
        "_draft_reply",
        AsyncMock(
            return_value={
                "answer": "We're open 9-5 Saturdays.",
                "confidence": "high",
                "escalate_reason": None,
            }
        ),
    )
    monkeypatch.setattr(inbox_triage, "resolve_deliverable_status", MagicMock(return_value="approved"))
    send_reply_mock = MagicMock(
        return_value={"success": True, "detail": "sent", "message_id": "m1", "thread_id": "t1"}
    )
    monkeypatch.setattr(inbox_triage.gmail_connector, "send_reply", send_reply_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "sent"
    send_reply_mock.assert_called_once()
    call_kwargs = send_reply_mock.call_args.kwargs
    assert call_kwargs["thread_id"] == "gmail-thread-1"
    assert call_kwargs["to"] == "customer@example.com"
    # an os_action_runs audit row was written for the auto-send
    assert any(call[0] == "os_action_runs" and call[1] == "insert" for call in db._sink)


@pytest.mark.asyncio
async def test_answerable_default_off_never_autosends_even_at_high_confidence(monkeypatch):
    """Drafts-only default: resolve_deliverable_status is the single gate —
    when it resolves pending (tenant never opted in), a high-confidence
    draft still does not send."""
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("answerable", confidence=0.99)),
    )
    monkeypatch.setattr(
        inbox_triage,
        "_draft_reply",
        AsyncMock(
            return_value={"answer": "Yes we are.", "confidence": "high", "escalate_reason": None}
        ),
    )
    # Simulate the real gate's default-off behavior regardless of confidence.
    monkeypatch.setattr(
        inbox_triage, "resolve_deliverable_status", MagicMock(return_value="pending_approval")
    )
    send_reply_mock = MagicMock()
    monkeypatch.setattr(inbox_triage.gmail_connector, "send_reply", send_reply_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "drafted"
    send_reply_mock.assert_not_called()


@pytest.mark.asyncio
async def test_draft_escalate_reason_escalates_instead_of_drafting(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("answerable", confidence=0.9)),
    )
    monkeypatch.setattr(
        inbox_triage,
        "_draft_reply",
        AsyncMock(
            return_value={
                "answer": "",
                "confidence": "low",
                "escalate_reason": "low_confidence_or_missing_kb_support",
            }
        ),
    )
    escalate_mock = MagicMock(return_value={"id": "esc-2"})
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)
    resolve_mock = MagicMock()
    monkeypatch.setattr(inbox_triage, "resolve_deliverable_status", resolve_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "escalated"
    escalate_mock.assert_called_once()
    resolve_mock.assert_not_called()  # never reached the deliverable gate


@pytest.mark.asyncio
async def test_persist_deliverable_failure_escalates(monkeypatch):
    """os_agent_runs insert raising must escalate instead of crashing."""
    db = _std_db()
    original_table_side_effect = db.table.side_effect

    def table_side_effect(name):
        if name == "os_agent_runs":
            chain = MagicMock()
            chain.insert.side_effect = RuntimeError("db insert failed")
            return chain
        return original_table_side_effect(name)

    db.table.side_effect = table_side_effect

    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("answerable", confidence=0.95)),
    )
    monkeypatch.setattr(
        inbox_triage,
        "_draft_reply",
        AsyncMock(
            return_value={"answer": "hi", "confidence": "high", "escalate_reason": None}
        ),
    )
    monkeypatch.setattr(
        inbox_triage, "resolve_deliverable_status", MagicMock(return_value="approved")
    )
    escalate_mock = MagicMock(return_value={"id": "esc-9"})
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "escalated"
    assert result["escalation"] == {"id": "esc-9"}
    escalate_mock.assert_called_once()
    kwargs = escalate_mock.call_args.kwargs
    assert kwargs["reason"] == "triage_deliverable_persist_failed"


@pytest.mark.asyncio
async def test_classify_invalid_category_defaults_to_escalate(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("not_a_real_category")),
    )
    escalate_mock = MagicMock(return_value={"id": "esc-x"})
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["category"] == "escalate"
    escalate_mock.assert_called_once()


@pytest.mark.asyncio
async def test_draft_failure_escalates(monkeypatch):
    db = _std_db()
    monkeypatch.setattr(
        inbox_triage,
        "call_claude_messages",
        AsyncMock(return_value=_classify_result("answerable", confidence=0.9)),
    )
    monkeypatch.setattr(
        inbox_triage, "_draft_reply", AsyncMock(side_effect=RuntimeError("llm down"))
    )
    escalate_mock = MagicMock(return_value=None)
    monkeypatch.setattr(inbox_triage, "_create_escalation_safe", escalate_mock)

    result = await inbox_triage.triage_inbound_email(
        db, tenant=TENANT_ID, parsed_email=_parsed_email(), os_thread_id=OS_THREAD_ID
    )

    assert result["action"] == "escalated"
    escalate_mock.assert_called_once()


# ---------------------------------------------------------------------------
# escalations-lane wrapper — lazy import, best-effort
# ---------------------------------------------------------------------------


class TestEscalationWrapper:
    def test_missing_escalations_module_returns_none_without_raising(self):
        # Force the "module unavailable" path deterministically regardless
        # of whether backend.services.escalations has landed from its own
        # lane yet — sys.modules[name] = None makes `import` raise
        # ImportError, the standard import-blocking sentinel.
        with patch.dict(sys.modules, {"backend.services.escalations": None}):
            result = inbox_triage._create_escalation_safe(
                MagicMock(),
                client_id=TENANT_ID,
                source_ref="email:msg-1",
                os_thread_id=OS_THREAD_ID,
                reason="test",
            )
        assert result is None

    def test_calls_create_escalation_when_module_available(self):
        stub_module = types.ModuleType("backend.services.escalations")
        create_escalation_mock = MagicMock(return_value={"id": "esc-3"})
        stub_module.create_escalation = create_escalation_mock
        fake_db_arg = MagicMock()
        with patch.dict(sys.modules, {"backend.services.escalations": stub_module}):
            result = inbox_triage._create_escalation_safe(
                fake_db_arg,
                client_id=TENANT_ID,
                source_ref="email:msg-1",
                os_thread_id=OS_THREAD_ID,
                reason="test reason",
                priority="high",
            )
        assert result == {"id": "esc-3"}
        create_escalation_mock.assert_called_once_with(
            fake_db_arg,
            client_id=TENANT_ID,
            source="email",
            source_ref="email:msg-1",
            os_thread_id=OS_THREAD_ID,
            reason="test reason",
            priority="high",
        )

    def test_create_escalation_raising_is_swallowed(self):
        stub_module = types.ModuleType("backend.services.escalations")
        stub_module.create_escalation = MagicMock(side_effect=RuntimeError("db down"))
        with patch.dict(sys.modules, {"backend.services.escalations": stub_module}):
            result = inbox_triage._create_escalation_safe(
                MagicMock(),
                client_id=TENANT_ID,
                source_ref="email:msg-1",
                os_thread_id=OS_THREAD_ID,
                reason="test",
            )
        assert result is None


# ---------------------------------------------------------------------------
# _draft_reply — direct unit tests (always mocked out in the flows above)
# ---------------------------------------------------------------------------


class TestDraftReply:
    @pytest.mark.asyncio
    async def test_builds_prompt_and_parses_response(self):
        build_prompt = MagicMock(return_value="PROMPT TEXT")
        call_mock = AsyncMock(return_value=_draft_result())
        parse_mock = MagicMock(
            return_value={"answer": "hi", "confidence": "high", "escalate_reason": None}
        )
        with patch.object(
            inbox_triage.support_agent, "build_support_prompt", build_prompt
        ), patch.object(inbox_triage, "call_claude_messages", call_mock), patch.object(
            inbox_triage.support_agent, "parse_support_reply", parse_mock
        ):
            result = await inbox_triage._draft_reply(TENANT_ID, _parsed_email())

        build_prompt.assert_called_once_with(
            TENANT_ID, "Hey, are you open Saturdays?"
        )
        call_mock.assert_awaited_once()
        parse_mock.assert_called_once_with(call_mock.return_value.text)
        assert result == {"answer": "hi", "confidence": "high", "escalate_reason": None}

    @pytest.mark.asyncio
    async def test_falls_back_to_subject_when_body_blank(self):
        build_prompt = MagicMock(return_value="PROMPT")
        call_mock = AsyncMock(return_value=_draft_result())
        with patch.object(
            inbox_triage.support_agent, "build_support_prompt", build_prompt
        ), patch.object(inbox_triage, "call_claude_messages", call_mock), patch.object(
            inbox_triage.support_agent, "parse_support_reply", MagicMock(return_value={})
        ):
            await inbox_triage._draft_reply(
                TENANT_ID, _parsed_email(body_text="   ", subject="Pricing?")
            )

        question = build_prompt.call_args.args[1]
        assert question == "(no body) Subject: Pricing?"


# ---------------------------------------------------------------------------
# _confidence_to_float
# ---------------------------------------------------------------------------


class TestConfidenceToFloat:
    def test_numeric_clamped_to_0_1(self):
        assert inbox_triage._confidence_to_float(0.5) == 0.5
        assert inbox_triage._confidence_to_float(5) == 1.0
        assert inbox_triage._confidence_to_float(-5) == 0.0

    def test_string_levels(self):
        assert inbox_triage._confidence_to_float("high") == 0.9
        assert inbox_triage._confidence_to_float("Medium") == 0.6
        assert inbox_triage._confidence_to_float("low") == 0.3

    def test_unrecognized_value_defaults_to_half(self):
        assert inbox_triage._confidence_to_float("garbage") == 0.5
        assert inbox_triage._confidence_to_float(None) == 0.5


# ---------------------------------------------------------------------------
# _reply_subject
# ---------------------------------------------------------------------------


class TestReplySubject:
    def test_blank_subject_returns_generic_reply(self):
        assert inbox_triage._reply_subject("   ") == "Re: your message"

    def test_already_prefixed_subject_is_unchanged(self):
        assert inbox_triage._reply_subject("Re: Pricing") == "Re: Pricing"

    def test_normal_subject_gets_prefixed(self):
        assert inbox_triage._reply_subject("Pricing question") == "Re: Pricing question"


# ---------------------------------------------------------------------------
# _body_to_html
# ---------------------------------------------------------------------------


class TestBodyToHtml:
    def test_blank_body_returns_empty_paragraph(self):
        assert inbox_triage._body_to_html("") == "<p></p>"
        # Whitespace-only body has no non-blank paragraph after splitting on
        # "\n\n", so it hits the same fallback branch — original (unstripped)
        # body is escaped into the single <p> tag.
        assert inbox_triage._body_to_html("   ") == "<p>   </p>"

    def test_multi_paragraph_body_wraps_each_paragraph(self):
        html = inbox_triage._body_to_html("Hi there.\n\nThanks!")
        assert html == "<p>Hi there.</p><p>Thanks!</p>"


# ---------------------------------------------------------------------------
# _tag_thread / _log_action_run — best-effort exception swallowing
# ---------------------------------------------------------------------------


class TestTagThreadExceptionSwallowed:
    def test_db_failure_does_not_raise(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        inbox_triage._tag_thread(db, TENANT_ID, OS_THREAD_ID, "spam")


class TestLogActionRunExceptionSwallowed:
    def test_db_failure_does_not_raise(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        inbox_triage._log_action_run(
            db, TENANT_ID, "deliv-1", {"success": True, "detail": "sent"}
        )
