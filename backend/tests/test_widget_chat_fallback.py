"""Tests for the widget chat managed-agent fallback helper.

Covers `_run_support_fallback` in backend.routers.widget_chat — the
second-tier escalation path that calls the support_agent managed agent
when first-tier Claude emits the FALLBACK_TO_SUPPORT_AGENT marker.

These are unit tests on the helper directly. The widget_chat endpoint
orchestration (history load, origin check, usage counter, etc.) is
covered in test_widget_chat.py; this file isolates the fallback
decision/execution logic so we can assert:

- marker absent → no-op, flag state irrelevant
- marker present + flag off → marker stripped, no fallback call
- marker present + flag on + high confidence → reply swapped
- marker present + flag on + low confidence → HANDOFF_REQUESTED appended
- timeout, ManagedAgentNotConfigured, generic Exception → force handoff
- log_activity called with the right metadata in every fallback branch

Patching strategy: `backend.services.support_agent.run_support_query`
is accessed lazily via the `_support_agent_mod` module reference inside
the helper, so patching the module attribute on the already-imported
service module is enough — the helper re-resolves it on every call.
"""

import asyncio
from unittest.mock import patch

import pytest

from backend.routers import widget_chat


@pytest.fixture
def tenant_id():
    return "00000000-0000-0000-0000-000000000aaa"


@pytest.fixture
def session_id():
    return "sess-fallback-test"


@pytest.fixture
def customer_message():
    return "What is your refund policy for custom orders placed during holidays?"


def _run(coro):
    """Run an async coroutine to completion for a sync test body."""
    return asyncio.run(coro)


class TestFallbackDisabled:
    """Marker absent OR flag off — happy path, no support_agent call."""

    def test_no_marker_returns_unchanged(
        self, tenant_id, session_id, customer_message
    ):
        """Common case: first-tier Claude answered fine, no fallback."""
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query"
        ) as mock_run:
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="Our hours are 9 to 5 Monday through Friday.",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is False
        assert new_text == "Our hours are 9 to 5 Monday through Friday."
        mock_run.assert_not_called()
        mock_log.assert_not_called()

    def test_marker_present_but_flag_off_strips_marker(
        self, tenant_id, session_id, customer_message
    ):
        """Claude leaked the marker but tenant hasn't opted in — strip it."""
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query"
        ) as mock_run:
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text=(
                        "I'm not sure about that.\nFALLBACK_TO_SUPPORT_AGENT"
                    ),
                    widget={"enable_ai_fallback": False},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is False
        assert "FALLBACK_TO_SUPPORT_AGENT" not in new_text
        assert new_text == "I'm not sure about that."
        mock_run.assert_not_called()
        mock_log.assert_not_called()

    def test_flag_missing_treated_as_off(
        self, tenant_id, session_id, customer_message
    ):
        """Legacy widget configs without enable_ai_fallback default to off."""
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ), patch(
            "backend.services.support_agent.run_support_query"
        ) as mock_run:
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="Hello FALLBACK_TO_SUPPORT_AGENT",
                    widget={},  # no key at all
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is False
        assert "FALLBACK_TO_SUPPORT_AGENT" not in new_text
        mock_run.assert_not_called()


class TestFallbackSuccess:
    """Flag on + marker present → support_agent call succeeds."""

    def test_high_confidence_replaces_reply(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": "Custom holiday orders are non-refundable after 48 hours.",
                "confidence": "high",
                "escalate_reason": None,
            },
        ) as mock_run:
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text=(
                        "I don't have that info.\nFALLBACK_TO_SUPPORT_AGENT"
                    ),
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text == (
            "Custom holiday orders are non-refundable after 48 hours."
        )
        assert "HANDOFF_REQUESTED" not in new_text
        assert "FALLBACK_TO_SUPPORT_AGENT" not in new_text
        mock_run.assert_called_once_with(
            tenant_id, customer_message, session_id
        )
        mock_log.assert_called_once()

    def test_medium_confidence_replaces_reply(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ), patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": "Based on our FAQ, refunds are processed within 5 days.",
                "confidence": "medium",
                "escalate_reason": None,
            },
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text == (
            "Based on our FAQ, refunds are processed within 5 days."
        )
        assert "HANDOFF_REQUESTED" not in new_text

    def test_activity_log_metadata_on_success(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": "Yes, we offer 24/7 support.",
                "confidence": "high",
                "escalate_reason": None,
            },
        ):
            _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )

        mock_log.assert_called_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["tenant_id"] == tenant_id
        assert kwargs["activity_type"] == "ai_fallback_fired"
        metadata = kwargs["metadata"]
        assert metadata["session_id"] == session_id
        assert metadata["confidence"] == "high"
        assert metadata["escalate_reason"] is None
        assert metadata["success"] is True
        assert metadata["error"] is None
        assert isinstance(metadata["duration_ms"], int)
        assert metadata["duration_ms"] >= 0


class TestFallbackLowConfidenceForcesHandoff:
    """support_agent returned — but confidence low → human handoff."""

    def test_low_confidence_appends_handoff(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ), patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": (
                    "I'm not certain about custom holiday policies."
                ),
                "confidence": "low",
                "escalate_reason": "kb_gap",
            },
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text=(
                        "Let me check.\nFALLBACK_TO_SUPPORT_AGENT"
                    ),
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text.endswith("HANDOFF_REQUESTED")
        assert "I'm not certain about custom holiday policies." in new_text

    def test_low_confidence_no_answer_uses_generic_prefix(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ), patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": None,
                "confidence": "low",
                "escalate_reason": "insufficient_context",
            },
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text.endswith("HANDOFF_REQUESTED")
        assert "connect you with our team" in new_text

    def test_activity_log_records_low_confidence(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": "Unsure.",
                "confidence": "low",
                "escalate_reason": "kb_gap",
            },
        ):
            _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        metadata = mock_log.call_args.kwargs["metadata"]
        assert metadata["confidence"] == "low"
        assert metadata["escalate_reason"] == "kb_gap"
        assert metadata["success"] is False
        assert metadata["error"] is None


class TestFallbackErrors:
    """Timeout / not-configured / generic exceptions → force handoff."""

    def test_timeout_forces_handoff(
        self, tenant_id, session_id, customer_message
    ):
        def _hang(*_args, **_kwargs):
            # Pretend the managed agent is stuck. The helper wraps the call
            # in asyncio.wait_for with an 8s timeout — but to keep the test
            # fast, we directly raise TimeoutError from inside the run to
            # short-circuit the wait.
            raise asyncio.TimeoutError()

        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            side_effect=_hang,
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text.endswith("HANDOFF_REQUESTED")
        metadata = mock_log.call_args.kwargs["metadata"]
        assert metadata["error"] == "timeout"
        assert metadata["success"] is False

    def test_not_configured_forces_handoff(
        self, tenant_id, session_id, customer_message
    ):
        from backend.services.managed_agents_registry import (
            ManagedAgentNotConfigured,
        )

        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            side_effect=ManagedAgentNotConfigured("support_agent"),
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text.endswith("HANDOFF_REQUESTED")
        metadata = mock_log.call_args.kwargs["metadata"]
        assert metadata["error"].startswith("not_configured")
        assert metadata["success"] is False

    def test_generic_exception_forces_handoff(
        self, tenant_id, session_id, customer_message
    ):
        with patch(
            "backend.routers.widget_chat_fallback.log_activity"
        ) as mock_log, patch(
            "backend.services.support_agent.run_support_query",
            side_effect=RuntimeError("anthropic 500"),
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text.endswith("HANDOFF_REQUESTED")
        metadata = mock_log.call_args.kwargs["metadata"]
        assert metadata["error"] == "exception: RuntimeError"
        assert metadata["success"] is False

    def test_log_activity_failure_does_not_break_helper(
        self, tenant_id, session_id, customer_message
    ):
        """If log_activity itself raises, the helper still returns cleanly."""
        with patch(
            "backend.routers.widget_chat_fallback.log_activity",
            side_effect=RuntimeError("activity log down"),
        ), patch(
            "backend.services.support_agent.run_support_query",
            return_value={
                "answer": "Our hours are 9-5.",
                "confidence": "high",
                "escalate_reason": None,
            },
        ):
            new_text, fired = _run(
                widget_chat._run_support_fallback(
                    assistant_text="FALLBACK_TO_SUPPORT_AGENT",
                    widget={"enable_ai_fallback": True},
                    tenant_id=tenant_id,
                    session_id=session_id,
                    customer_message=customer_message,
                )
            )
        assert fired is True
        assert new_text == "Our hours are 9-5."
