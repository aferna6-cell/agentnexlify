"""Provider usage normalization and provider-error diagnostics.

A real Anthropic Usage object leaves optional cache counters as None when
no prompt-cache activity occurred. That absence is zero. Missing or
malformed core counters stay unproved and are not coerced to zero.
Provider failures log a safe exception type and a proved HTTP status only.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import Usage

from backend.services.ai_usage_guard import (
    AIUsageAccountingDebt,
    AIUsageRecord,
    AIUsageReservation,
    record_ai_usage,
)
from backend.services.llm_runtime import call_claude_messages_sync

_CACHE_FIELDS = ("cache_creation_input_tokens", "cache_read_input_tokens")
_CORE_FIELDS = ("input_tokens", "output_tokens")


class _Block:
    def __init__(self, text):
        self.text = text


class _Response:
    def __init__(self, usage, text="keywords"):
        self.usage = usage
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"


class _Usage:
    def __init__(self, **fields):
        for name, value in fields.items():
            setattr(self, name, value)


class _FakeMessages:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _FakeAnthropic:
    def __init__(self, outcome):
        self.messages = _FakeMessages(outcome)

    def __call__(self, *_args, **_kwargs):
        return self


def _reservation():
    return AIUsageReservation(
        allowed=True,
        tenant_id="tenant-runtime-usage",
        period_month="2026-10-01",
        estimated_tokens=823,
        alert_threshold_tokens=800_000,
        hard_limit_tokens=1_000_000,
        reason="",
    )


def _call(outcome):
    fake = _FakeAnthropic(outcome)
    with patch("backend.services.llm_runtime.anthropic.Anthropic", fake):
        result = call_claude_messages_sync(
            operation="seo.generate_keywords",
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": "keywords"}],
        )
    return result, fake.messages.calls


def _record(result):
    calls = []

    def rpc(name, payload):
        calls.append({"name": name, **payload})
        response = MagicMock()
        response.execute.return_value.data = {
            "total_tokens": payload["p_input_tokens"] + payload["p_output_tokens"],
            "alert_triggered": False,
            "hard_limit_reached": False,
        }
        return response

    with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=result,
            operation="seo.generate_keywords",
            session_id="sess-runtime-usage",
            model="claude-sonnet-4-6",
        )
    return recorded, calls


def _assert_builtin_int(value, expected):
    assert type(value) is int
    assert value == expected


def test_real_sdk_absent_cache_normalizes_to_zero_and_records_once():
    usage = Usage(input_tokens=4, output_tokens=2)
    assert usage.cache_creation_input_tokens is None
    assert usage.cache_read_input_tokens is None

    result, provider_calls = _call(_Response(usage))
    _assert_builtin_int(result.input_tokens, 4)
    _assert_builtin_int(result.output_tokens, 2)
    _assert_builtin_int(result.cache_creation_input_tokens, 0)
    _assert_builtin_int(result.cache_read_input_tokens, 0)
    assert result.text == "keywords"
    assert len(provider_calls) == 1

    recorded, calls = _record(result)
    assert isinstance(recorded, AIUsageRecord)
    assert not isinstance(recorded, AIUsageAccountingDebt)
    assert len(calls) == 1
    assert calls[0]["name"] == "record_ai_token_usage"
    assert calls[0]["p_reserved_tokens"] == 823
    assert calls[0]["p_input_tokens"] == 4
    assert calls[0]["p_output_tokens"] == 2
    assert calls[0]["p_cache_creation_input_tokens"] == 0
    assert calls[0]["p_cache_read_input_tokens"] == 0


@pytest.mark.parametrize("field", _CACHE_FIELDS)
@pytest.mark.parametrize("bad", (True, "0", 1.5, -3))
def test_malformed_cache_counter_stays_unproved(field, bad):
    fields = {
        "input_tokens": 4,
        "output_tokens": 2,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    fields[field] = bad
    result, _provider_calls = _call(_Response(_Usage(**fields)))
    proved = type(getattr(result, field)) is int and getattr(result, field) >= 0
    assert proved is False
    recorded, calls = _record(result)
    assert calls == []
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert recorded.reason == "provider_usage_unproved"
    assert recorded.estimated_tokens == 823


@pytest.mark.parametrize("field", _CORE_FIELDS)
@pytest.mark.parametrize("bad", (None, True, "4", 1.5, -3))
def test_missing_or_malformed_core_usage_stays_unproved(field, bad):
    fields = {
        "input_tokens": 4,
        "output_tokens": 2,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": None,
    }
    fields[field] = bad
    result, _provider_calls = _call(_Response(_Usage(**fields)))
    assert type(getattr(result, field)) is not int or getattr(result, field) < 0
    recorded, calls = _record(result)
    assert calls == []
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert recorded.reason == "provider_usage_unproved"


def test_explicit_zero_usage_records_once():
    usage = Usage(
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    result, _provider_calls = _call(_Response(usage, text="[]"))
    for name in (*_CORE_FIELDS, *_CACHE_FIELDS):
        _assert_builtin_int(getattr(result, name), 0)
    recorded, calls = _record(result)
    assert isinstance(recorded, AIUsageRecord)
    assert len(calls) == 1
    assert calls[0]["p_input_tokens"] == 0
    assert calls[0]["p_output_tokens"] == 0
    assert calls[0]["p_cache_creation_input_tokens"] == 0
    assert calls[0]["p_cache_read_input_tokens"] == 0


def test_empty_text_with_valid_sdk_usage_still_records():
    result, _provider_calls = _call(_Response(Usage(input_tokens=4, output_tokens=2), text=""))
    assert result.text == ""
    _assert_builtin_int(result.input_tokens, 4)
    _assert_builtin_int(result.output_tokens, 2)
    _assert_builtin_int(result.cache_creation_input_tokens, 0)
    _assert_builtin_int(result.cache_read_input_tokens, 0)
    recorded, calls = _record(result)
    assert isinstance(recorded, AIUsageRecord)
    assert len(calls) == 1
    assert calls[0]["p_input_tokens"] == 4
    assert calls[0]["p_output_tokens"] == 2


def test_graceful_reply_is_not_a_proved_zero_usage_record():
    fake = _FakeAnthropic(RuntimeError("provider down"))
    with patch("backend.services.llm_runtime.anthropic.Anthropic", fake):
        result = call_claude_messages_sync(
            operation="seo.generate_keywords",
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": "keywords"}],
            graceful_reply="try again later",
        )
    assert len(fake.messages.calls) == 1
    assert result.text == "try again later"
    assert result.stop_reason == "fallback_graceful"
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.cache_creation_input_tokens is None
    assert result.cache_read_input_tokens is None
    recorded, calls = _record(result)
    assert calls == []
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert recorded.reason == "provider_usage_unproved"


_PRIVACY_CANARY = "visitor@example.com\r\nINJECTED authorization=Bearer sentinel-token"
_CANARY_PIECES = (
    "visitor@example.com",
    "INJECTED",
    "authorization=Bearer",
    "sentinel-token",
    "Traceback",
    "response body",
    "\r",
)


class _StatusError(Exception):
    def __init__(self, status_code):
        super().__init__(_PRIVACY_CANARY + " response body")
        self.status_code = status_code


class _BadStatus:
    def __str__(self):
        return _PRIVACY_CANARY


def _trace_text(directory: Path) -> str:
    chunks = []
    for path in directory.glob("*.jsonl"):
        chunks.append(path.read_text(encoding="utf-8"))
    return "".join(chunks)


def _runtime_blob(caplog, directory: Path) -> str:
    parts = [_trace_text(directory)]
    for record in caplog.records:
        if not record.name.startswith("backend.services.llm_runtime"):
            continue
        parts.append(record.getMessage())
        if record.exc_text:
            parts.append(record.exc_text)
        if record.exc_info:
            parts.append("exc_info")
    return "\n".join(parts)


def _assert_canaries_absent(blob: str, caplog) -> None:
    for piece in _CANARY_PIECES:
        assert piece not in blob
    for record in caplog.records:
        if not record.name.startswith("backend.services.llm_runtime"):
            continue
        message = record.getMessage()
        assert "\n" not in message
        assert "\r" not in message
        assert record.exc_info is None


def _raise_provider(monkeypatch, tmp_path, caplog, exc):
    monkeypatch.setenv("LLM_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_TRACE_ENABLED", "1")
    caplog.set_level(logging.DEBUG)
    fake = _FakeAnthropic(exc)
    with patch("backend.services.llm_runtime.anthropic.Anthropic", fake):
        with pytest.raises(type(exc)):
            call_claude_messages_sync(
                operation="seo.generate_keywords",
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": "keywords"}],
            )
    assert len(fake.messages.calls) == 1
    return _runtime_blob(caplog, tmp_path)


def test_provider_error_log_keeps_type_and_proved_status_only(monkeypatch, tmp_path, caplog):
    blob = _raise_provider(monkeypatch, tmp_path, caplog, _StatusError(429))
    _assert_canaries_absent(blob, caplog)
    assert "error_type=_StatusError" in blob
    assert "status=429" in blob
    error_rows = [json.loads(line) for line in _trace_text(tmp_path).splitlines() if line.strip()]
    assert error_rows[-1]["error_type"] == "_StatusError"
    assert error_rows[-1]["status_code"] == 429
    assert "error" not in error_rows[-1]


@pytest.mark.parametrize("bad", (True, "401", 1.5, _BadStatus(), -1, 99, 600))
def test_provider_error_omits_unproved_status(monkeypatch, tmp_path, caplog, bad):
    blob = _raise_provider(monkeypatch, tmp_path, caplog, _StatusError(bad))
    _assert_canaries_absent(blob, caplog)
    assert "error_type=_StatusError" in blob
    assert "status=" not in blob
    error_rows = [json.loads(line) for line in _trace_text(tmp_path).splitlines() if line.strip()]
    assert "status_code" not in error_rows[-1]


def test_provider_error_replaces_unsafe_exception_type_name(monkeypatch, tmp_path, caplog):
    class _Named(Exception):
        pass

    _Named.__name__ = "Bad\r\nINJECTED authorization=Bearer sentinel-token visitor@example.com"
    blob = _raise_provider(monkeypatch, tmp_path, caplog, _Named(_PRIVACY_CANARY))
    _assert_canaries_absent(blob, caplog)
    assert "error_type=Exception" in blob
