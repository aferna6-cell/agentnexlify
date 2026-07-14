"""Structured Outputs (#F9) — opt-in strict-JSON via output_config.format.

Contracts:
  - `_merge_structured_output_config` wraps a raw JSON Schema into the Anthropic
    `format` envelope and merges it into output_config WITHOUT clobbering
    `effort`; response_schema=None returns output_config untouched (zero change
    for every existing caller).
  - `call_claude_messages_sync(response_schema=...)` sends the schema through in
    the request's output_config (extra_body); omitting it sends no `format`.
"""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.llm_runtime import (
    _merge_structured_output_config,
    call_claude_messages_sync,
)

_SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string"}}, "required": ["verdict"]}


# ---------------------------------------------------------------------------
# _merge_structured_output_config — pure function
# ---------------------------------------------------------------------------


def test_no_schema_returns_output_config_unchanged():
    assert _merge_structured_output_config(None, None) is None
    assert _merge_structured_output_config({"effort": "high"}, None) == {"effort": "high"}


def test_schema_wrapped_in_json_schema_envelope():
    out = _merge_structured_output_config(None, _SCHEMA)
    assert out == {"format": {"type": "json_schema", "schema": _SCHEMA}}


def test_schema_merge_preserves_effort():
    out = _merge_structured_output_config({"effort": "xhigh"}, _SCHEMA)
    assert out["effort"] == "xhigh"
    assert out["format"] == {"type": "json_schema", "schema": _SCHEMA}


def test_merge_does_not_mutate_caller_output_config():
    original = {"effort": "high"}
    _merge_structured_output_config(original, _SCHEMA)
    assert original == {"effort": "high"}  # no in-place mutation


# ---------------------------------------------------------------------------
# call_claude_messages_sync — request payload wiring
# ---------------------------------------------------------------------------


def _fake_response():
    return SimpleNamespace(
        content=[SimpleNamespace(text='{"verdict":"ok"}')],
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
            operation="unit.structured",
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": "judge this"}],
            **kwargs,
        )
    return client.messages.create.call_args.kwargs


def test_response_schema_sent_in_output_config():
    kwargs = _run(response_schema=_SCHEMA, output_config={"effort": "low"})
    oc = kwargs["extra_body"]["output_config"]
    assert oc["format"] == {"type": "json_schema", "schema": _SCHEMA}
    assert oc["effort"] == "low"  # existing effort preserved alongside format


def test_no_response_schema_sends_no_format():
    kwargs = _run(output_config={"effort": "low"})
    # extra_body present only because output_config was passed; it must carry no format
    oc = kwargs.get("extra_body", {}).get("output_config", {})
    assert "format" not in oc


def test_no_output_config_at_all_sends_no_extra_body_format():
    kwargs = _run()
    assert "format" not in kwargs.get("extra_body", {}).get("output_config", {})
