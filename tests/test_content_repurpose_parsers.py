"""Focused tests for content repurposer JSON parsing / repair helpers."""

import os
os.environ["TESTING"] = "1"

import pytest

from backend.services.content_repurposer import (
    _strip_json_fences,
    _repair_truncated_json,
    _parse_repurpose_json,
)


def test_strip_json_fences_removes_markdown_wrapper():
    raw = "```json\n{\"x_thread\": []}\n```"
    assert _strip_json_fences(raw) == '{"x_thread": []}'


def test_repair_truncated_json_closes_open_structures():
    raw = '{"x_thread": [{"tweet": "hello"}, {"tweet": "world"}'
    repaired = _repair_truncated_json(raw)
    assert repaired.endswith("]}")


def test_parse_repurpose_json_accepts_fenced_json():
    raw = "```json\n{\"x_thread\": [{\"tweet\": \"hello\"}]}\n```"
    parsed = _parse_repurpose_json(raw)
    assert "x_thread" in parsed


def test_parse_repurpose_json_repairs_truncated_payload():
    raw = '{"x_thread": [{"tweet": "hello"}, {"tweet": "world"}]'
    parsed = _parse_repurpose_json(raw)
    assert len(parsed["x_thread"]) == 2


def test_parse_repurpose_json_rejects_non_object():
    with pytest.raises(ValueError):
        _parse_repurpose_json('[{"tweet": "hello"}]')
