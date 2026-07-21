"""Tests for the photo-quote assessment service (#37 core).

All deps injected (model call, #38 prompt builder + threshold resolver, db), so
this runs standalone with no app boot, no network, and without requiring the #38
module to be present:
    python3 -m pytest backend/tests/test_photo_quote_service.py -v --noconftest
"""

import asyncio
import json
from datetime import datetime, timezone

from backend.services import photo_quote_service as svc

# Fixed per-vertical floor so parsing tests never touch the #38 module.
_THRESHOLD = lambda row: 0.7  # noqa: E731


# --------------------------------------------------------------------------- #
# validate_image                                                               #
# --------------------------------------------------------------------------- #
def test_validate_image_accepts_jpeg_and_png():
    assert svc.validate_image("image/jpeg", 1000) is None
    assert svc.validate_image("image/png", 1000) is None


def test_validate_image_rejects_bad_type_empty_and_oversize():
    assert svc.validate_image("image/gif", 1000) == "unsupported_media_type"
    assert svc.validate_image(None, 1000) == "unsupported_media_type"
    assert svc.validate_image("image/jpeg", 0) == "empty_image"
    assert svc.validate_image("image/jpeg", svc.MAX_IMAGE_BYTES + 1) == "image_too_large"


# --------------------------------------------------------------------------- #
# parse_quote_response                                                          #
# --------------------------------------------------------------------------- #
def test_parse_happy_path_confident_quote():
    raw = json.dumps({"severity": "minor", "quote_low": 150, "quote_high": 400,
                      "confidence": 0.9, "summary": "Small leak under the sink."})
    out = svc.parse_quote_response(raw, {}, "plumbing", resolve_threshold=_THRESHOLD)
    assert out["needs_human"] is False
    assert out["severity"] == "minor"
    assert out["quote_low"] == 150 and out["quote_high"] == 400
    assert out["confidence"] == 0.9


def test_parse_low_confidence_forces_needs_human_and_zeroes_price():
    raw = json.dumps({"severity": "major", "quote_low": 800, "quote_high": 2000,
                      "confidence": 0.5, "summary": "Hard to tell from this angle."})
    out = svc.parse_quote_response(raw, {}, "plumbing", resolve_threshold=_THRESHOLD)
    # 0.5 < 0.7 floor -> needs_human, price zeroed
    assert out["needs_human"] is True
    assert out["severity"] == "needs_human"
    assert out["quote_low"] == 0 and out["quote_high"] == 0


def test_parse_explicit_needs_human_severity():
    raw = json.dumps({"severity": "needs_human", "quote_low": 0, "quote_high": 0,
                      "confidence": 0.95, "summary": "Photo too blurry to price."})
    out = svc.parse_quote_response(raw, {}, "roofing", resolve_threshold=_THRESHOLD)
    assert out["needs_human"] is True


def test_parse_swaps_inverted_range():
    raw = json.dumps({"severity": "minor", "quote_low": 500, "quote_high": 200,
                      "confidence": 0.9, "summary": "x"})
    out = svc.parse_quote_response(raw, {}, "hvac", resolve_threshold=_THRESHOLD)
    assert out["quote_low"] == 200 and out["quote_high"] == 500


def test_parse_unparseable_response_falls_back_to_needs_human():
    out = svc.parse_quote_response("not json at all", {}, "pest", resolve_threshold=_THRESHOLD)
    assert out["needs_human"] is True
    assert out["quote_low"] == 0


def test_parse_strips_markdown_fence():
    raw = "```json\n" + json.dumps({"severity": "minor", "quote_low": 10,
                                    "quote_high": 20, "confidence": 0.9, "summary": "x"}) + "\n```"
    out = svc.parse_quote_response(raw, {}, "plumbing", resolve_threshold=_THRESHOLD)
    assert out["needs_human"] is False and out["quote_high"] == 20


# --------------------------------------------------------------------------- #
# is_over_daily_quota                                                           #
# --------------------------------------------------------------------------- #
class FakeCountChain:
    def __init__(self, count, fail=False):
        self._count = count
        self._fail = fail

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        if self._fail:
            raise RuntimeError("count failed")
        return type("R", (), {"count": self._count, "data": []})()


class FakeDB:
    def __init__(self, count, fail=False):
        self._chain = FakeCountChain(count, fail)

    def table(self, name):
        return self._chain


NOW = datetime(2026, 7, 21, 15, 0, 0, tzinfo=timezone.utc)


def test_quota_not_exceeded_under_limit():
    assert svc.is_over_daily_quota(FakeDB(10), "t1", limit=50, now=NOW) is False


def test_quota_exceeded_at_limit():
    assert svc.is_over_daily_quota(FakeDB(50), "t1", limit=50, now=NOW) is True


def test_quota_check_fails_open_on_error():
    assert svc.is_over_daily_quota(FakeDB(0, fail=True), "t1", now=NOW) is False


# --------------------------------------------------------------------------- #
# assess_photo (fully injected)                                                 #
# --------------------------------------------------------------------------- #
def test_assess_photo_builds_prompt_calls_model_and_parses():
    captured = {}

    def fake_build_prompt(rules_row, industry):
        captured["industry"] = industry
        return "SYSTEM PROMPT"

    async def fake_llm(**kwargs):
        captured["system"] = kwargs.get("system")
        captured["model"] = kwargs.get("model")
        # image block present in the user content
        content = kwargs["messages"][0]["content"]
        captured["has_image"] = any(b.get("type") == "image" for b in content)
        return type("R", (), {"text": json.dumps(
            {"severity": "minor", "quote_low": 100, "quote_high": 300,
             "confidence": 0.9, "summary": "ok"})})()

    out = asyncio.new_event_loop().run_until_complete(
        svc.assess_photo(
            "BASE64DATA", "image/jpeg", {"industry": "plumbing"}, "plumbing",
            llm_call=fake_llm, build_prompt=fake_build_prompt, resolve_threshold=_THRESHOLD,
        )
    )
    assert out["needs_human"] is False and out["quote_high"] == 300
    assert captured["system"] == "SYSTEM PROMPT"
    assert captured["model"] == svc.MODEL
    assert captured["has_image"] is True
    assert captured["industry"] == "plumbing"
