"""Tests for per-vertical confidence constants + vision prompt builder (#38).

Pure functions — no DB, no API, no app boot. Runs standalone:
    python3 -m pytest backend/tests/test_photo_quote_prompts.py -v --noconftest
"""

import json

from backend.services.photo_quote_prompts import (
    VERTICAL_CONFIDENCE_DEFAULTS,
    build_vision_prompt,
    resolve_confidence_threshold,
)


# --------------------------------------------------------------------------- #
# resolve_confidence_threshold                                                 #
# --------------------------------------------------------------------------- #
def test_each_vertical_default_returned_when_no_override():
    for industry, floor in VERTICAL_CONFIDENCE_DEFAULTS.items():
        row = {"industry": industry, "min_confidence_threshold": None}
        assert resolve_confidence_threshold(row) == floor


def test_override_wins_over_vertical_default():
    row = {"industry": "plumbing", "min_confidence_threshold": 0.95}
    # plumbing default is 0.7, but the explicit override must win
    assert VERTICAL_CONFIDENCE_DEFAULTS["plumbing"] == 0.7
    assert resolve_confidence_threshold(row) == 0.95


def test_zero_override_is_respected_not_treated_as_missing():
    # 0.0 is a valid, meaningful override — must not fall through to the default
    row = {"industry": "roofing", "min_confidence_threshold": 0.0}
    assert resolve_confidence_threshold(row) == 0.0


def test_unknown_vertical_no_override_falls_back_to_safe_floor():
    row = {"industry": "electrical", "min_confidence_threshold": None}
    result = resolve_confidence_threshold(row)
    assert 0.0 <= result <= 1.0
    # conservative middle floor, not a vertical value
    assert result not in VERTICAL_CONFIDENCE_DEFAULTS.values() or result == 0.75


def test_none_rules_row_falls_back_to_safe_floor():
    assert 0.0 <= resolve_confidence_threshold(None) <= 1.0


def test_missing_industry_key_falls_back():
    assert 0.0 <= resolve_confidence_threshold({"min_confidence_threshold": None}) <= 1.0


# --------------------------------------------------------------------------- #
# build_vision_prompt                                                          #
# --------------------------------------------------------------------------- #
def test_injects_pricing_json():
    pricing = {"drain_snake": {"low": 150, "high": 350}}
    row = {"industry": "plumbing", "rules_jsonb": pricing,
           "min_confidence_threshold": None}
    prompt = build_vision_prompt(row, "plumbing")
    # the pricing payload is present in the prompt (as JSON)
    assert "drain_snake" in prompt
    assert "150" in prompt and "350" in prompt


def test_includes_all_three_severity_tiers():
    row = {"industry": "roofing", "rules_jsonb": {}, "min_confidence_threshold": None}
    prompt = build_vision_prompt(row, "roofing")
    for sev in ("minor", "major", "needs_human"):
        assert sev in prompt


def test_includes_json_output_schema_fields():
    row = {"industry": "hvac", "rules_jsonb": {}, "min_confidence_threshold": None}
    prompt = build_vision_prompt(row, "hvac")
    for field in ("severity", "quote_low", "quote_high", "confidence"):
        assert field in prompt


def test_includes_resolved_confidence_floor():
    # override present -> that exact value should surface in the instructions
    row = {"industry": "pest", "rules_jsonb": {}, "min_confidence_threshold": 0.6}
    prompt = build_vision_prompt(row, "pest")
    assert "0.6" in prompt


def test_none_rules_row_still_builds_valid_prompt():
    prompt = build_vision_prompt(None, "landscaping")
    assert isinstance(prompt, str) and prompt
    # schema still present even with no pricing rules
    assert "quote_low" in prompt
    # empty pricing renders as an empty JSON object, never a crash
    assert "{}" in prompt


def test_disclaimer_text_injected_when_present():
    row = {"industry": "auto_body", "rules_jsonb": {},
           "disclaimer_text": "Estimate only — final price after inspection.",
           "min_confidence_threshold": None}
    prompt = build_vision_prompt(row, "auto_body")
    assert "Estimate only" in prompt


def test_pricing_json_is_valid_json_roundtrip():
    pricing = {"tune_up": {"low": 89, "high": 200}, "note": "seasonal"}
    row = {"industry": "hvac", "rules_jsonb": pricing,
           "min_confidence_threshold": None}
    prompt = build_vision_prompt(row, "hvac")
    # the exact serialized pricing block round-trips back to the same object
    serialized = json.dumps(pricing, indent=2)
    assert serialized in prompt
