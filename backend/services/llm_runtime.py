"""Shared Anthropic runtime helpers for timing and structured logging."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from functools import partial
from typing import Any

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCallResult:
    text: str
    duration_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    stop_reason: str | None = None
    raw_response: Any = None


def resolve_string_setting(name: str, fallback: str) -> str:
    """Read a settings value safely even when tests patch settings with MagicMock."""
    value = getattr(settings, name, None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def resolve_int_setting(name: str, fallback: int, minimum: int = 1) -> int:
    """Read an integer setting safely even when tests patch settings with MagicMock."""
    value = getattr(settings, name, None)
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int) and value >= minimum:
        return value
    return fallback


def _extract_usage_value(usage: Any, field: str) -> int | None:
    if usage is None:
        return None
    value = getattr(usage, field, None)
    if isinstance(value, int):
        return value
    return None


def _extract_text(response: Any) -> str:
    blocks = getattr(response, "content", None) or []
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts).strip()


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_l = str(key).lower()
        if any(token in key_l for token in ("message", "content", "text", "body", "api_key", "token", "secret", "password", "cookie", "authorization")):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 200:
                safe[key] = value[:197] + "..."
            else:
                safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = {"type": type(value).__name__, "len": len(value)}
        elif isinstance(value, dict):
            safe[key] = {"type": "dict", "keys": sorted(str(k) for k in value.keys())[:20]}
        else:
            safe[key] = {"type": type(value).__name__}
    return safe


def _message_role_counts(messages: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for msg in messages:
        role = str(msg.get("role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def _requires_sampling_omission(model: str) -> bool:
    """Claude Opus 4.7 rejects non-default sampling params; omit them entirely."""
    return model == "claude-opus-4-7"


def _log_start(
    call_id: str,
    operation: str,
    model: str,
    max_tokens: int,
    temperature: float | None,
    output_config: dict[str, Any] | None,
    system: str | None,
    messages: list[dict[str, str]],
    metadata: dict[str, Any] | None,
) -> None:
    system_chars = len(system or "")
    message_chars = sum(len(msg.get("content") or "") for msg in messages)
    temperature_label = "omitted" if temperature is None else f"{temperature:.2f}"
    logger.info(
        "llm.call.start id=%s op=%s model=%s max_tokens=%d temperature=%s "
        "output_config=%s message_count=%d role_counts=%s system_chars=%d message_chars=%d metadata=%s",
        call_id,
        operation,
        model,
        max_tokens,
        temperature_label,
        _safe_metadata(output_config),
        len(messages),
        _message_role_counts(messages),
        system_chars,
        message_chars,
        _safe_metadata(metadata),
    )


def _log_finish(
    call_id: str,
    operation: str,
    model: str,
    duration_ms: int,
    result: ClaudeCallResult,
    metadata: dict[str, Any] | None,
) -> None:
    logger.info(
        "llm.call.finish id=%s op=%s model=%s duration_ms=%d input_tokens=%s output_tokens=%s "
        "cache_create_tokens=%s cache_read_tokens=%s response_chars=%d stop_reason=%s metadata=%s",
        call_id,
        operation,
        model,
        duration_ms,
        result.input_tokens,
        result.output_tokens,
        result.cache_creation_input_tokens,
        result.cache_read_input_tokens,
        len(result.text),
        result.stop_reason,
        _safe_metadata(metadata),
    )


def _log_error(
    call_id: str,
    operation: str,
    model: str,
    duration_ms: int,
    messages: list[dict[str, str]],
    system: str | None,
    metadata: dict[str, Any] | None,
    exc: Exception,
) -> None:
    logger.warning(
        "llm.call.error id=%s op=%s model=%s duration_ms=%d message_count=%d role_counts=%s system_chars=%d "
        "message_chars=%d error_type=%s error=%s metadata=%s",
        call_id,
        operation,
        model,
        duration_ms,
        len(messages),
        _message_role_counts(messages),
        len(system or ""),
        sum(len(msg.get("content") or "") for msg in messages),
        type(exc).__name__,
        str(exc)[:300],
        _safe_metadata(metadata),
        exc_info=True,
    )


def _should_retry(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    return any(token in name for token in ("ratelimit", "overloaded", "timeout", "apiconnection", "internalserver"))


def call_claude_messages_sync(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, str]],
    temperature: float | None = 0.0,
    output_config: dict[str, Any] | None = None,
    system: str | None = None,
    timeout: float = 30.0,
    metadata: dict[str, Any] | None = None,
    max_retries: int = 0,
    retry_delay_seconds: float = 0.75,
) -> ClaudeCallResult:
    """Run a Claude messages.create call with timing and structured logs."""
    call_id = uuid.uuid4().hex[:12]
    request_temperature = None if _requires_sampling_omission(model) else temperature
    _log_start(
        call_id,
        operation,
        model,
        max_tokens,
        request_temperature,
        output_config,
        system,
        messages,
        metadata,
    )
    started = time.perf_counter()
    attempts = 0

    while True:
        attempts += 1
        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=timeout)
            request_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if request_temperature is not None:
                request_kwargs["temperature"] = request_temperature
            if output_config:
                request_kwargs["extra_body"] = {"output_config": output_config}
            if system is not None:
                request_kwargs["system"] = system

            response = client.messages.create(
                **request_kwargs,
            )
            break
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            retryable = _should_retry(exc) and attempts <= max_retries
            logger.warning(
                "llm.call.retry_decision id=%s op=%s attempt=%d max_retries=%d retryable=%s error_type=%s",
                call_id,
                operation,
                attempts,
                max_retries,
                retryable,
                type(exc).__name__,
            )
            if retryable:
                time.sleep(retry_delay_seconds * attempts)
                continue
            _log_error(call_id, operation, model, duration_ms, messages, system, metadata, exc)
            raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    usage = getattr(response, "usage", None)
    result = ClaudeCallResult(
        text=_extract_text(response),
        duration_ms=duration_ms,
        input_tokens=_extract_usage_value(usage, "input_tokens"),
        output_tokens=_extract_usage_value(usage, "output_tokens"),
        cache_creation_input_tokens=_extract_usage_value(usage, "cache_creation_input_tokens"),
        cache_read_input_tokens=_extract_usage_value(usage, "cache_read_input_tokens"),
        stop_reason=getattr(response, "stop_reason", None),
        raw_response=response,
    )
    _log_finish(call_id, operation, model, duration_ms, result, metadata)
    return result


async def call_claude_messages(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, str]],
    temperature: float | None = 0.0,
    output_config: dict[str, Any] | None = None,
    system: str | None = None,
    timeout: float = 30.0,
    metadata: dict[str, Any] | None = None,
) -> ClaudeCallResult:
    """Async wrapper for Claude messages.create that avoids blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(
            call_claude_messages_sync,
            operation=operation,
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            temperature=temperature,
            output_config=output_config,
            system=system,
            timeout=timeout,
            metadata=metadata,
        ),
    )
