"""Focused parser tests for local SEO AI JSON helpers."""

import os
os.environ["TESTING"] = "1"

import json
import pytest

from backend.routers.local_seo import (
    _strip_json_fences,
    _parse_json_array_response,
    _parse_json_object_response,
)


def test_strip_json_fences_handles_plain_json_block():
    raw = "```json\n{\"a\": 1}\n```"
    assert _strip_json_fences(raw) == '{"a": 1}'


def test_strip_json_fences_handles_generic_code_block():
    raw = "```\n[1, 2, 3]\n```"
    assert _strip_json_fences(raw) == "[1, 2, 3]"


def test_parse_json_object_response_accepts_object():
    raw = json.dumps({"overall_score": 88, "recommendations": ["Fix titles"]})
    parsed = _parse_json_object_response(raw)
    assert parsed["overall_score"] == 88


def test_parse_json_object_response_accepts_fenced_object():
    raw = "```json\n{\"overall_score\": 91}\n```"
    parsed = _parse_json_object_response(raw)
    assert parsed["overall_score"] == 91


def test_parse_json_object_response_rejects_array():
    with pytest.raises(ValueError):
        _parse_json_object_response("[1, 2, 3]")


def test_parse_json_array_response_accepts_array():
    parsed = _parse_json_array_response('["kw1", "kw2"]')
    assert parsed == ["kw1", "kw2"]


def test_parse_json_array_response_accepts_fenced_array():
    parsed = _parse_json_array_response("```json\n[\"kw1\", \"kw2\"]\n```")
    assert parsed == ["kw1", "kw2"]


def test_parse_json_array_response_rejects_object():
    with pytest.raises(ValueError):
        _parse_json_array_response('{"kw": 1}')
