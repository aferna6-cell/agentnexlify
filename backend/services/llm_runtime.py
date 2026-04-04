"""Shared Anthropic runtime helpers for timing and structured logging."""

import asyncio
import logging
import time
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


def _log_start(
    operation: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system: str | None,
    messages: list[dict[str, str]],
    metadata: dict[str, Any] | None,
) -> None:
    system_chars = len(system or "")
    message_chars = sum(len(msg.get("content") or "") for msg in messages)
    extra = metadata or {}
    logger.info(
        "llm.call.start op=%s model=%s max_tokens=%d temperature=%.2f "
        "message_count=%d system_chars=%d message_chars=%d metadata=%s",
        operation,
        model,
        max_tokens,
        temperature,
        len(messages),
        system_chars,
        message_chars,
        extra,
    )


def _log_finish(
    operation: str,
    model: str,
    duration_ms: int,
    result: ClaudeCallResult,
    metadata: dict[str, Any] | None,
) -> None:
    logger.info(
        "llm.call.finish op=%s model=%s duration_ms=%d input_tokens=%s output_tokens=%s "
        "cache_create_tokens=%s cache_read_tokens=%s response_chars=%d stop_reason=%s metadata=%s",
        operation,
        model,
        duration_ms,
        result.input_tokens,
        result.output_tokens,
        result.cache_creation_input_tokens,
        result.cache_read_input_tokens,
        len(result.text),
        result.stop_reason,
        metadata or {},
    )


def _log_error(
    operation: str,
    model: str,
    duration_ms: int,
    messages: list[dict[str, str]],
    system: str | None,
    metadata: dict[str, Any] | None,
    exc: Exception,
) -> None:
    logger.warning(
        "llm.call.error op=%s model=%s duration_ms=%d message_count=%d system_chars=%d "
        "message_chars=%d error_type=%s metadata=%s",
        operation,
        model,
        duration_ms,
        len(messages),
        len(system or ""),
        sum(len(msg.get("content") or "") for msg in messages),
        type(exc).__name__,
        metadata or {},
        exc_info=True,
    )


def call_claude_messages_sync(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    system: str | None = None,
    timeout: float = 30.0,
    metadata: dict[str, Any] | None = None,
) -> ClaudeCallResult:
    """Run a Claude messages.create call with timing and structured logs."""
    _log_start(operation, model, max_tokens, temperature, system, messages, metadata)
    started = time.perf_counter()

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=timeout)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system is not None:
            request_kwargs["system"] = system

        response = client.messages.create(
            **request_kwargs,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_error(operation, model, duration_ms, messages, system, metadata, exc)
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
    _log_finish(operation, model, duration_ms, result, metadata)
    return result


async def call_claude_messages(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
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
            system=system,
            timeout=timeout,
            metadata=metadata,
        ),
    )
