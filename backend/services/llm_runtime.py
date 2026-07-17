"""Shared Anthropic runtime helpers for timing and structured logging."""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

_TRACE_DIR_ENV = "LLM_TRACE_DIR"
_TRACE_ENABLED_ENV = "LLM_TRACE_ENABLED"
_DEFAULT_TRACE_DIR = "logs/llm_traces"


def _trace_enabled() -> bool:
    flag = os.environ.get(_TRACE_ENABLED_ENV, "1").strip().lower()
    return flag not in ("0", "false", "no", "off", "")


def _trace_path() -> Path:
    base = os.environ.get(_TRACE_DIR_ENV) or _DEFAULT_TRACE_DIR
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path(base) / f"{day}.jsonl"


def _write_trace(record: dict[str, Any]) -> None:
    if not _trace_enabled():
        return
    try:
        path = _trace_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("llm.trace.write_failed error=%s", exc)


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


def _message_role_counts(messages: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for msg in messages:
        role = str(msg.get("role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def _content_length(content: Any) -> int:
    """Best-effort text length for a message `content` payload.

    `content` is a plain string for text-only calls (the common case), or a
    list of multimodal blocks for vision calls — like this:
    `[{"type": "text", "text": "..."}, {"type": "image", "source": {...}}]`.
    Image blocks count as a fixed small marker rather than their (large,
    base64) payload, so logs stay cheap and this never crashes on non-string
    content. Anything else (None, unexpected shape) contributes 0.
    """
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text":
                total += len(block.get("text") or "")
            elif block_type == "image":
                total += len("[image]")
            else:
                total += len(str(block_type or "block"))
        return total
    return 0


def _message_chars(messages: list[dict[str, Any]]) -> int:
    return sum(_content_length(msg.get("content")) for msg in messages)


# Reasoning-tier models (adaptive thinking) reject non-default sampling params
# (temperature/top_p/top_k) — sending them returns a 400. Opus 4.7 was the
# first; Opus 4.8 and Sonnet 5 (2026-06-30) follow the same contract. Omitting
# a sampling param is always safe (the API falls back to its default), so when
# in doubt about a new reasoning model, add it here rather than risk a 400 on
# the live widget path.
_SAMPLING_OMISSION_MODELS = frozenset(
    {"claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-5"}
)


def _requires_sampling_omission(model: str) -> bool:
    """Reasoning models reject non-default sampling params; omit them entirely."""
    return model in _SAMPLING_OMISSION_MODELS


# Beta header required ONLY for the 1-hour cache TTL opt-in (`cache_ttl="1h"`).
# The default 5-minute ephemeral cache (`cache_control: {"type": "ephemeral"}`
# with no `ttl` field, i.e. `cache_ttl=None`) needs no beta header on current
# Anthropic API versions — the `system` block's `cache_control` marker alone
# is enough. Verified against the pinned `anthropic` SDK (0.116.0):
# `anthropic.types.anthropic_beta_param.AnthropicBetaParam` is a `Literal`
# that includes `"extended-cache-ttl-2025-04-11"` alongside other real betas
# already in use in this codebase (e.g. `managed-agents-2026-04-01` in
# backend/services/managed_agents.py). `anthropic.types.cache_control_
# ephemeral_param.CacheControlEphemeralParam` confirms `ttl: Literal["5m",
# "1h"]`, default `"5m"`.
EXTENDED_CACHE_TTL_BETA = "extended-cache-ttl-2025-04-11"


def _merge_structured_output_config(
    output_config: dict[str, Any] | None,
    response_schema: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge an opt-in JSON-schema `format` into `output_config` without
    clobbering any `effort` (or other) key the caller already set.

    `response_schema` is the raw JSON Schema for the expected response body
    (e.g. `{"type": "object", "properties": {...}}`) — this wraps it in the
    Anthropic Structured Outputs envelope: `output_config.format = {"type":
    "json_schema", "schema": <response_schema>}`. Confirmed shape against the
    installed `anthropic` SDK (0.116.0): `anthropic.types.output_config_
    param.OutputConfigParam.format` is `Optional[JSONOutputFormatParam]`, and
    `anthropic.types.json_output_format_param.JSONOutputFormatParam` requires
    `type: Literal["json_schema"]` + `schema: Dict[str, object]`. This is a
    top-level (non-beta) Messages API param — no `anthropic-beta` header
    needed, unlike the 1-hour cache TTL opt-in elsewhere in this file.

    `response_schema=None` (the default for every existing caller) returns
    `output_config` untouched — zero behavior change unless a caller opts in.
    """
    if response_schema is None:
        return output_config
    merged = dict(output_config or {})
    merged["format"] = {"type": "json_schema", "schema": response_schema}
    return merged


def _build_cached_system(
    system: str | list[dict[str, Any]] | None,
    cache_system: bool,
    cache_ttl: str | None,
) -> str | list[dict[str, Any]] | None:
    """Wrap a plain-string system prompt in Anthropic's cached content-block
    form — like this: `[{"type": "text", "text": <prompt>, "cache_control":
    {"type": "ephemeral"}}]`. Repeated calls with the same block re-use the
    cached prefix; cache reads bill at 0.1x normal input tokens.

    OPT-IN ONLY. `cache_system=False` (the default) returns `system`
    untouched — every existing caller keeps today's plain-string behavior
    byte-for-byte. When `system` is already a list (a caller building the
    block form itself), it is returned unchanged too — this function never
    double-wraps.

    TENANT ISOLATION: Anthropic caches on the exact hash of the block's text.
    Two tenants with different KB/persona text produce different cache
    entries automatically. There is no shared/global cache key here, and none
    should ever be added — that would be a cross-tenant leak vector.
    """
    if not cache_system or not system:
        return system
    if isinstance(system, list):
        return system
    cache_control: dict[str, Any] = {"type": "ephemeral"}
    if cache_ttl:
        cache_control["ttl"] = cache_ttl
    return [{"type": "text", "text": system, "cache_control": cache_control}]


def _log_start(
    call_id: str,
    operation: str,
    model: str,
    max_tokens: int,
    temperature: float | None,
    output_config: dict[str, Any] | None,
    system: str | None,
    messages: list[dict[str, Any]],
    metadata: dict[str, Any] | None,
) -> None:
    system_chars = len(system or "")
    message_chars = _message_chars(messages)
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
    _write_trace({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "finish",
        "id": call_id,
        "op": operation,
        "model": model,
        "duration_ms": duration_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cache_creation_input_tokens": result.cache_creation_input_tokens,
        "cache_read_input_tokens": result.cache_read_input_tokens,
        "stop_reason": result.stop_reason,
        "response_chars": len(result.text),
        "metadata": _safe_metadata(metadata),
    })


def _log_error(
    call_id: str,
    operation: str,
    model: str,
    duration_ms: int,
    messages: list[dict[str, Any]],
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
        _message_chars(messages),
        type(exc).__name__,
        str(exc)[:300],
        _safe_metadata(metadata),
        exc_info=True,
    )
    _write_trace({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "error",
        "id": call_id,
        "op": operation,
        "model": model,
        "duration_ms": duration_ms,
        "error_type": type(exc).__name__,
        "error": str(exc)[:300],
        "message_count": len(messages),
        "role_counts": _message_role_counts(messages),
        "system_chars": len(system or ""),
        "message_chars": _message_chars(messages),
        "metadata": _safe_metadata(metadata),
    })


def _should_retry(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    return any(token in name for token in ("ratelimit", "overloaded", "timeout", "apiconnection", "internalserver"))


def _call_single_model(
    *,
    call_id: str,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
    temperature: float | None,
    output_config: dict[str, Any] | None,
    system: str | list[dict[str, Any]] | None,
    timeout: float,
    metadata: dict[str, Any] | None,
    max_retries: int,
    retry_delay_seconds: float,
    started: float,
    cache_system: bool = False,
    cache_ttl: str | None = None,
) -> ClaudeCallResult:
    """Run the retry loop for a single model. Raises the last exception on
    exhausted retries so the caller (fallback loop or direct caller) decides
    what to do next."""
    request_temperature = None if _requires_sampling_omission(model) else temperature
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
            cached_system = _build_cached_system(system, cache_system, cache_ttl)
            if cached_system is not None:
                request_kwargs["system"] = cached_system
            if cache_system and cache_ttl == "1h":
                # Only the extended (1h) TTL needs a beta header; default 5-min
                # ephemeral caching works with no extra header on this SDK/API
                # version — see EXTENDED_CACHE_TTL_BETA comment above.
                request_kwargs["extra_headers"] = {"anthropic-beta": EXTENDED_CACHE_TTL_BETA}

            response = client.messages.create(
                **request_kwargs,
            )
            break
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            retryable = _should_retry(exc) and attempts <= max_retries
            logger.warning(
                "llm.call.retry_decision id=%s op=%s model=%s attempt=%d max_retries=%d retryable=%s error_type=%s",
                call_id,
                operation,
                model,
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


def call_claude_messages_sync(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
    temperature: float | None = 0.0,
    output_config: dict[str, Any] | None = None,
    system: str | list[dict[str, Any]] | None = None,
    timeout: float = 30.0,
    metadata: dict[str, Any] | None = None,
    max_retries: int = 0,
    retry_delay_seconds: float = 0.75,
    fallback_models: list[str] | None = None,
    graceful_reply: str | None = None,
    cache_system: bool = False,
    cache_ttl: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> ClaudeCallResult:
    """Run a Claude messages.create call with timing and structured logs.

    `fallback_models` (optional) — when the primary `model` fails after its
    own `max_retries`, try each fallback model in order with the same
    messages/system/max_tokens before giving up. Existing callers that don't
    pass `fallback_models` see zero behavior change: single model, raise on
    failure.

    `graceful_reply` (optional) — if every model (primary + fallbacks) fails,
    return a canned `ClaudeCallResult` instead of raising. Leave unset to
    keep today's behavior (raise the last exception).

    `cache_system` (optional, default False) — OPT-IN Anthropic prompt
    caching for the `system` prompt. False (default): `system` is sent
    exactly as passed — zero behavior change for every existing caller. True:
    a plain-string `system` is wrapped as a cached content block (see
    `_build_cached_system`) so repeated calls with the identical prefix reuse
    the cache — cache reads bill at 0.1x normal input tokens. A `system`
    already passed as a list is left untouched either way.

    `cache_ttl` (optional) — `None`/omitted uses Anthropic's default 5-minute
    ephemeral TTL with no extra header. `"1h"` requests the extended 1-hour
    TTL and requires (and automatically sends) the
    `anthropic-beta: extended-cache-ttl-2025-04-11` header. Only meaningful
    when `cache_system=True`.

    `response_schema` (optional, default None) — OPT-IN Anthropic Structured
    Outputs. `None` (the default): zero behavior change, `output_config` is
    used exactly as passed. A JSON Schema dict: the model is constrained to
    emit output matching that schema (schema-guaranteed JSON, no markdown
    fences, no prose) — see `_merge_structured_output_config` for the exact
    envelope and SDK verification. Composes with `output_config={"effort":
    ...}` — effort is preserved, only `format` is added/overwritten.
    """
    call_id = uuid.uuid4().hex[:12]
    request_temperature = None if _requires_sampling_omission(model) else temperature
    merged_output_config = _merge_structured_output_config(output_config, response_schema)
    _log_start(
        call_id,
        operation,
        model,
        max_tokens,
        request_temperature,
        merged_output_config,
        system,
        messages,
        metadata,
    )
    started = time.perf_counter()

    models_to_try = [model, *(fallback_models or [])]
    last_exc: Exception | None = None

    for attempt_index, candidate_model in enumerate(models_to_try):
        if attempt_index > 0:
            logger.warning(
                "llm.call.fallback id=%s op=%s model=%s from=%s",
                call_id,
                operation,
                candidate_model,
                model,
            )
        try:
            return _call_single_model(
                call_id=call_id,
                operation=operation,
                model=candidate_model,
                max_tokens=max_tokens,
                messages=messages,
                temperature=temperature,
                output_config=merged_output_config,
                system=system,
                timeout=timeout,
                metadata=metadata,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                started=started,
                cache_system=cache_system,
                cache_ttl=cache_ttl,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: try next model
            last_exc = exc
            continue

    if graceful_reply is not None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "llm.call.graceful_fallback id=%s op=%s models_tried=%s error_type=%s",
            call_id,
            operation,
            models_to_try,
            type(last_exc).__name__ if last_exc else None,
        )
        return ClaudeCallResult(
            text=graceful_reply,
            duration_ms=duration_ms,
            stop_reason="fallback_graceful",
        )

    assert last_exc is not None  # models_to_try always has >=1 entry
    raise last_exc


async def call_claude_messages(
    *,
    operation: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
    temperature: float | None = 0.0,
    output_config: dict[str, Any] | None = None,
    system: str | list[dict[str, Any]] | None = None,
    timeout: float = 30.0,
    metadata: dict[str, Any] | None = None,
    max_retries: int = 0,
    retry_delay_seconds: float = 0.75,
    fallback_models: list[str] | None = None,
    graceful_reply: str | None = None,
    cache_system: bool = False,
    cache_ttl: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> ClaudeCallResult:
    """Async wrapper for Claude messages.create that avoids blocking the event loop.

    Retries (and their backoff sleeps) run inside the executor thread, so the
    event loop stays free even when max_retries > 0. `fallback_models`,
    `graceful_reply`, `cache_system`, `cache_ttl`, and `response_schema` pass
    straight through to `call_claude_messages_sync` — see that function's
    docstring for the caching + Structured Outputs opt-in contracts.
    """
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
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            fallback_models=fallback_models,
            graceful_reply=graceful_reply,
            cache_system=cache_system,
            cache_ttl=cache_ttl,
            response_schema=response_schema,
        ),
    )
