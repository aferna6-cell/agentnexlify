"""Tests for centralized LLM runtime logging/safety behavior."""

import os
os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.services.llm_runtime import (
    _message_role_counts,
    _requires_sampling_omission,
    _safe_metadata,
    _should_retry,
    call_claude_messages,
    call_claude_messages_sync,
)


def test_safe_metadata_redacts_sensitive_contentish_fields():
    metadata = {
        "tenant_id": "tenant-123",
        "prompt_profile": {"faq_count": 3, "has_kb": True},
        "message_body": "secret prompt text",
        "api_key": "secret",
        "token": "secret-token",
        "content_preview": "do not log this",
        "ok": True,
    }

    safe = _safe_metadata(metadata)

    assert safe["tenant_id"] == "tenant-123"
    assert safe["prompt_profile"] == {"type": "dict", "keys": ["faq_count", "has_kb"]}
    assert safe["ok"] is True
    assert "message_body" not in safe
    assert "api_key" not in safe
    assert "token" not in safe
    assert "content_preview" not in safe


def test_message_role_counts_summarizes_roles():
    counts = _message_role_counts([
        {"role": "system", "content": "a"},
        {"role": "user", "content": "b"},
        {"role": "assistant", "content": "c"},
        {"role": "user", "content": "d"},
    ])
    assert counts == {"system": 1, "user": 2, "assistant": 1}


def test_call_claude_messages_sync_logs_and_returns_result():
    fake_usage = SimpleNamespace(
        input_tokens=111,
        output_tokens=22,
        cache_creation_input_tokens=5,
        cache_read_input_tokens=7,
    )
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="Hello world")],
        usage=fake_usage,
        stop_reason="end_turn",
    )

    with patch("backend.services.llm_runtime.anthropic.Anthropic") as mock_client_cls, \
         patch("backend.services.llm_runtime.logger") as mock_logger:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = fake_response

        result = call_claude_messages_sync(
            operation="unit.test",
            model="claude-sonnet-4-6",
            max_tokens=128,
            temperature=0.1,
            system="system rules",
            messages=[{"role": "user", "content": "hello"}],
            metadata={
                "tenant_id": "tenant-123",
                "prompt_profile": {"faq_count": 2},
                "message_body": "should not appear",
            },
        )

        assert result.text == "Hello world"
        assert result.input_tokens == 111
        assert result.output_tokens == 22
        assert result.stop_reason == "end_turn"

        start_call = mock_logger.info.call_args_list[0]
        finish_call = mock_logger.info.call_args_list[-1]
        start_args = start_call[0]
        finish_args = finish_call[0]

        assert start_args[0].startswith("llm.call.start")
        assert finish_args[0].startswith("llm.call.finish")
        assert "message_body" not in str(start_args)
        assert "message_body" not in str(finish_args)
        assert "tenant-123" in str(start_args)


def test_opus_4_7_omits_sampling_params_and_sends_effort_config():
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="Advisor brief")],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        stop_reason="end_turn",
    )

    with patch("backend.services.llm_runtime.anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.return_value = fake_response

        result = call_claude_messages_sync(
            operation="unit.opus47",
            model="claude-opus-4-7",
            max_tokens=1024,
            temperature=0.0,
            output_config={"effort": "xhigh"},
            messages=[{"role": "user", "content": "plan this"}],
        )

    assert result.text == "Advisor brief"
    assert _requires_sampling_omission("claude-opus-4-7") is True
    assert _requires_sampling_omission("claude-sonnet-4-6") is False
    # Sonnet 5 + Opus 4.8 (2026-06-30) are reasoning-tier and reject sampling
    # params too — the widget defaults to Sonnet 5, so this guards the live path.
    assert _requires_sampling_omission("claude-sonnet-5") is True
    assert _requires_sampling_omission("claude-opus-4-8") is True
    kwargs = mock_client.messages.create.call_args.kwargs
    assert "temperature" not in kwargs
    assert "top_p" not in kwargs
    assert "top_k" not in kwargs
    assert kwargs["extra_body"] == {"output_config": {"effort": "xhigh"}}


def test_should_retry_matches_transient_error_types():
    class RateLimitError(Exception):
        pass

    class TimeoutError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    assert _should_retry(RateLimitError()) is True
    assert _should_retry(TimeoutError()) is True
    assert _should_retry(BadRequestError()) is False


def test_call_claude_messages_sync_logs_error_with_safe_metadata():
    with patch("backend.services.llm_runtime.anthropic.Anthropic") as mock_client_cls, \
         patch("backend.services.llm_runtime.logger") as mock_logger:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            call_claude_messages_sync(
                operation="unit.error",
                model="claude-sonnet-4-6",
                max_tokens=128,
                messages=[{"role": "user", "content": "hello"}],
                metadata={"tenant_id": "tenant-123", "text": "hide me"},
            )

        warning_args = mock_logger.warning.call_args[0]
        assert warning_args[0].startswith("llm.call.retry_decision") or warning_args[0].startswith("llm.call.error")
        logged = " ".join(str(call[0][0]) for call in mock_logger.warning.call_args_list)
        assert "llm.call.error" in logged
        assert "hide me" not in str(mock_logger.warning.call_args_list)
        assert "tenant-123" in str(mock_logger.warning.call_args_list)


def test_call_claude_messages_sync_retries_transient_failures():
    class RateLimitError(Exception):
        pass

    fake_usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="Recovered")],
        usage=fake_usage,
        stop_reason="end_turn",
    )

    with patch("backend.services.llm_runtime.anthropic.Anthropic") as mock_client_cls, \
         patch("backend.services.llm_runtime.time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [RateLimitError("slow down"), fake_response]

        result = call_claude_messages_sync(
            operation="unit.retry",
            model="claude-sonnet-4-6",
            max_tokens=32,
            messages=[{"role": "user", "content": "hello"}],
            max_retries=1,
        )

        assert result.text == "Recovered"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_call_claude_messages_async_accepts_and_passes_retry_params():
    """Regression: async wrapper must accept max_retries/retry_delay_seconds.

    Before the passthrough existed, local_seo_ai + orchestrator call sites that
    passed max_retries=1 raised TypeError at runtime (masked by their except
    blocks). The retry sleep runs inside the executor thread, off the loop.
    """

    class RateLimitError(Exception):
        pass

    fake_usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="Recovered async")],
        usage=fake_usage,
        stop_reason="end_turn",
    )

    with patch("backend.services.llm_runtime.anthropic.Anthropic") as mock_client_cls, \
         patch("backend.services.llm_runtime.time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [RateLimitError("slow down"), fake_response]

        result = await call_claude_messages(
            operation="unit.retry_async",
            model="claude-sonnet-4-6",
            max_tokens=32,
            messages=[{"role": "user", "content": "hello"}],
            max_retries=1,
            retry_delay_seconds=0.5,
        )

        assert result.text == "Recovered async"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once_with(0.5)
