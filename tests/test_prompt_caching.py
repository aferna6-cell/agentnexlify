"""Prompt caching (#F4) — the opt-in tenant-KB-prefix cache in llm_runtime.

Contracts:
  - `_build_cached_system` wraps the system string into Anthropic's cache-block
    list form ONLY when cache_system=True and system is non-empty; otherwise it
    returns the input unchanged (default off = byte-for-byte prior behavior).
  - The 1-hour TTL opt-in adds the extended-cache-ttl beta header; the default
    5-minute ephemeral cache needs no header.
  - Tenant isolation is by exact content (Anthropic hashes the block); there is
    no shared cache key in our code — asserted structurally (each distinct
    system string produces its own distinct block).
"""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.llm_runtime import (
    EXTENDED_CACHE_TTL_BETA,
    _build_cached_system,
    call_claude_messages_sync,
)


# ---------------------------------------------------------------------------
# _build_cached_system — pure function
# ---------------------------------------------------------------------------


def test_cache_off_returns_system_unchanged():
    assert _build_cached_system("SYSTEM", False, None) == "SYSTEM"


def test_cache_on_wraps_string_in_ephemeral_block():
    out = _build_cached_system("TENANT KB + PERSONA", True, None)
    assert out == [
        {"type": "text", "text": "TENANT KB + PERSONA", "cache_control": {"type": "ephemeral"}}
    ]


def test_cache_on_with_1h_ttl_sets_ttl_field():
    out = _build_cached_system("KB", True, "1h")
    assert out[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_cache_on_but_empty_system_not_wrapped():
    # No prefix to cache -> pass through unchanged, no crash.
    assert _build_cached_system("", True, None) == ""
    assert _build_cached_system(None, True, None) is None


def test_cache_on_already_list_passes_through():
    blocks = [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}]
    assert _build_cached_system(blocks, True, None) == blocks


def test_distinct_tenants_get_distinct_blocks():
    # No shared/global cache key: two tenants' prompts produce independent
    # blocks keyed only on their own text (Anthropic hashes content).
    a = _build_cached_system("TENANT A KB", True, None)
    b = _build_cached_system("TENANT B KB", True, None)
    assert a[0]["text"] != b[0]["text"]


# ---------------------------------------------------------------------------
# call_claude_messages_sync — request payload wiring
# ---------------------------------------------------------------------------


def _fake_response():
    return SimpleNamespace(
        content=[SimpleNamespace(text="ok")],
        usage=SimpleNamespace(
            input_tokens=10, output_tokens=5,
            cache_creation_input_tokens=0, cache_read_input_tokens=0,
        ),
        stop_reason="end_turn",
    )


def _run(**kwargs):
    with patch("backend.services.llm_runtime.anthropic.Anthropic") as cls:
        client = MagicMock()
        cls.return_value = client
        client.messages.create.return_value = _fake_response()
        call_claude_messages_sync(
            operation="unit.cache",
            model="claude-sonnet-5",
            max_tokens=256,
            messages=[{"role": "user", "content": "hi"}],
            system="TENANT SYSTEM PROMPT",
            **kwargs,
        )
    return client.messages.create.call_args.kwargs


def test_cache_system_true_sends_cache_block_no_beta_header():
    kwargs = _run(cache_system=True)
    assert isinstance(kwargs["system"], list)
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    # Default 5-min ephemeral needs no beta header.
    assert "extra_headers" not in kwargs or "anthropic-beta" not in kwargs.get("extra_headers", {})


def test_cache_system_true_1h_adds_beta_header():
    kwargs = _run(cache_system=True, cache_ttl="1h")
    assert kwargs["system"][0]["cache_control"]["ttl"] == "1h"
    assert kwargs["extra_headers"]["anthropic-beta"] == EXTENDED_CACHE_TTL_BETA


def test_cache_system_false_sends_plain_string_unchanged():
    kwargs = _run(cache_system=False)
    assert kwargs["system"] == "TENANT SYSTEM PROMPT"
