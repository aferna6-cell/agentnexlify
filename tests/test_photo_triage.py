"""Photo-triage (#R1) — unit tests.

Contracts:
  - triage_photos assesses via Claude vision (Sonnet 5) and returns
    {urgency, category, scope_summary, recommended_action}.
  - urgency is normalized to the allowed set; junk defaults to "medium".
  - triage_photos never raises: no usable images, LLM failure, and an
    unparseable response all return None (the widget treats None as
    "unavailable" and its normal flow is unaffected).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import backend.services.photo_triage as photo_triage
from backend.services.photo_triage import _validate_urgency, triage_photos

IMG = {"media_type": "image/jpeg", "data": "ZmFrZWJhc2U2NA=="}


def _llm(text):
    r = MagicMock()
    r.text = text
    return r


def test_validate_urgency_normalizes_and_defaults():
    assert _validate_urgency("EMERGENCY") == "emergency"
    assert _validate_urgency("  High ") == "high"
    assert _validate_urgency(None) == "medium"
    assert _validate_urgency(42) == "medium"


def test_triage_happy_path_returns_structured_dict():
    payload = (
        '{"urgency": "emergency", "category": "burst pipe", '
        '"scope_summary": "Water actively leaking from a joint under the sink.", '
        '"recommended_action": "Shut the main valve and book an emergency visit."}'
    )
    with patch.object(
        photo_triage, "call_claude_messages", new=AsyncMock(return_value=_llm(payload))
    ) as call:
        result = asyncio.run(triage_photos(business_type="plumber", images=[IMG], note="help"))
    assert result == {
        "urgency": "emergency",
        "category": "burst pipe",
        "scope_summary": "Water actively leaking from a joint under the sink.",
        "recommended_action": "Shut the main valve and book an emergency visit.",
    }
    # ran on the vision model
    assert call.await_args.kwargs["model"] == "claude-sonnet-5"
    # content was multimodal (list of blocks, incl. an image block)
    sent = call.await_args.kwargs["messages"][0]["content"]
    assert isinstance(sent, list)
    assert any(b.get("type") == "image" for b in sent)


def test_triage_bad_urgency_defaults_to_medium():
    payload = (
        '{"urgency": "catastrophic", "category": "roof", '
        '"scope_summary": "s", "recommended_action": "a"}'
    )
    with patch.object(
        photo_triage, "call_claude_messages", new=AsyncMock(return_value=_llm(payload))
    ):
        result = asyncio.run(triage_photos(business_type="roofer", images=[IMG]))
    assert result["urgency"] == "medium"


def test_triage_no_usable_images_returns_none():
    result = asyncio.run(triage_photos(business_type="plumber", images=[{"data": ""}]))
    assert result is None


def test_triage_llm_failure_returns_none():
    with patch.object(
        photo_triage, "call_claude_messages", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        result = asyncio.run(triage_photos(business_type="plumber", images=[IMG]))
    assert result is None


def test_triage_unparseable_returns_none():
    with patch.object(
        photo_triage, "call_claude_messages", new=AsyncMock(return_value=_llm("not json"))
    ):
        result = asyncio.run(triage_photos(business_type="plumber", images=[IMG]))
    assert result is None
