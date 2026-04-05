"""Targeted tests for centralized onboarding AI paths and parser behavior."""

import os
os.environ["TESTING"] = "1"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("backend.routers.onboarding.call_claude_messages", new_callable=AsyncMock)
async def test_generate_ai_content_parses_expected_sections(mock_call):
    from backend.routers.onboarding import _generate_ai_content

    mock_call.return_value = MagicMock(text=(
        "HERO: Miami Plumbing Done Right\n"
        "ABOUT: We help Miami homeowners with fast plumbing service.\n"
        "SERVICES: Emergency repair, drain cleaning, and inspections.\n"
        "FAQ1Q: Do you offer same-day service?\n"
        "FAQ1A: Yes, when availability allows.\n"
        "FAQ2Q: What areas do you serve?\n"
        "FAQ2A: We serve Miami and nearby neighborhoods.\n"
        "FAQ3Q: Are estimates free?\n"
        "FAQ3A: Yes, basic estimates are free."
    ))

    result = await _generate_ai_content(
        business_name="Test Plumbing",
        business_type="plumbing",
        city="Miami",
        services=["drain cleaning"],
    )

    assert result is not None
    assert result["hero_headline"] == "Miami Plumbing Done Right"
    assert len(result["faqs"]) == 3
    assert mock_call.await_count == 1


def test_parse_auto_kb_response_extracts_sections_and_faqs():
    from backend.routers.onboarding import _parse_auto_kb_response

    raw = (
        "===KNOWLEDGE_BASE===\n"
        "## About\nHelpful KB\n"
        "===CUSTOM_INSTRUCTIONS===\n"
        "You are the Test Plumbing assistant.\n"
        "===FAQ_START===\n"
        "Q: Do you offer emergency service?\n"
        "A: Yes, 24/7.\n"
        "C: services\n"
        "Q: Where are you located?\n"
        "A: Miami.\n"
        "C: location\n"
        "===FAQ_END==="
    )

    kb, custom_instructions, faqs = _parse_auto_kb_response(raw)
    assert kb.startswith("## About")
    assert custom_instructions.startswith("You are the Test Plumbing assistant")
    assert len(faqs) == 2
    assert faqs[0].question == "Do you offer emergency service?"
    assert faqs[1].category == "location"


def test_parse_auto_kb_response_falls_back_when_markers_missing():
    from backend.routers.onboarding import _parse_auto_kb_response

    raw = "Plain fallback text without section markers"
    kb, custom_instructions, faqs = _parse_auto_kb_response(raw)
    assert kb == raw
    assert custom_instructions == ""
    assert faqs == []
