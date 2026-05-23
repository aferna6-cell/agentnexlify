"""Targeted tests for centralized onboarding AI paths and parser behavior."""

import os

os.environ["TESTING"] = "1"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("backend.routers.onboarding.call_claude_messages", new_callable=AsyncMock)
async def test_generate_ai_content_parses_expected_sections(mock_call):
    from backend.routers.onboarding import _generate_ai_content

    mock_call.return_value = MagicMock(
        text=(
            "HERO: Miami Plumbing Done Right\n"
            "ABOUT: We help Miami homeowners with fast plumbing service.\n"
            "SERVICES: Emergency repair, drain cleaning, and inspections.\n"
            "FAQ1Q: Do you offer same-day service?\n"
            "FAQ1A: Yes, when availability allows.\n"
            "FAQ2Q: What areas do you serve?\n"
            "FAQ2A: We serve Miami and nearby neighborhoods.\n"
            "FAQ3Q: Are estimates free?\n"
            "FAQ3A: Yes, basic estimates are free."
        )
    )

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

    kb, custom_instructions, faqs, _services, _hours = _parse_auto_kb_response(raw)
    assert kb.startswith("## About")
    assert custom_instructions.startswith("You are the Test Plumbing assistant")
    assert len(faqs) == 2
    assert faqs[0].question == "Do you offer emergency service?"
    assert faqs[1].category == "location"


def test_parse_auto_kb_response_falls_back_when_markers_missing():
    from backend.routers.onboarding import _parse_auto_kb_response

    raw = "Plain fallback text without section markers"
    kb, custom_instructions, faqs, _services, _hours = _parse_auto_kb_response(raw)
    assert kb == raw
    assert custom_instructions == ""
    assert faqs == []


def test_expand_hours_from_text_parses_day_ranges():
    from backend.services.onboarding_ai import expand_hours_from_text

    out = expand_hours_from_text("Open Mon-Fri 8am-6pm, Sat 9am-2pm.")
    assert out["Mon"].lower().startswith("8")
    assert "Mon" in out and "Tue" in out and "Wed" in out
    assert "Thu" in out and "Fri" in out and "Sat" in out
    assert "Sun" not in out
    assert "9am-2pm".replace(" ", "") in out["Sat"].replace(" ", "")


def test_expand_hours_from_text_handles_closed_marker():
    from backend.services.onboarding_ai import expand_hours_from_text

    out = expand_hours_from_text("Sunday hours: Sun closed.")
    assert out.get("Sun", "").lower() == "closed"


def test_parse_auto_kb_response_extracts_services_block():
    from backend.services.onboarding_ai import parse_auto_kb_response

    raw = (
        "===KNOWLEDGE_BASE===\n"
        "About paragraph here\n"
        "===CUSTOM_INSTRUCTIONS===\n"
        "Identity instructions\n"
        "===SERVICES===\n"
        "- Drain cleaning\n"
        "- Water heater repair\n"
        "* Pipe leaks\n"
        "===FAQ_START===\n"
        "Q: Q1?\nA: A1.\nC: cat\n"
        "===FAQ_END==="
    )
    _kb, _ci, _faqs, services, _hours = parse_auto_kb_response(raw)
    assert services == ["Drain cleaning", "Water heater repair", "Pipe leaks"]


def test_parse_auto_kb_response_falls_back_to_kb_services_section():
    from backend.services.onboarding_ai import parse_auto_kb_response

    raw = (
        "===KNOWLEDGE_BASE===\n"
        "## About\nWe do plumbing.\n"
        "## Services\n"
        "- Drain cleaning\n"
        "- Sewer line\n"
        "===CUSTOM_INSTRUCTIONS===\n"
        "Be helpful\n"
        "===FAQ_START===\n"
        "===FAQ_END==="
    )
    _kb, _ci, _faqs, services, _hours = parse_auto_kb_response(raw)
    assert "Drain cleaning" in services
    assert "Sewer line" in services


def test_parse_auto_kb_response_parses_hours_block():
    from backend.services.onboarding_ai import parse_auto_kb_response

    raw = (
        "===KNOWLEDGE_BASE===\nKB\n"
        "===CUSTOM_INSTRUCTIONS===\nCI\n"
        "===HOURS===\n"
        "Mon: 8am-6pm\n"
        "Tue: 8am-6pm\n"
        "Sat: closed\n"
        "===FAQ_START===\n"
        "===FAQ_END==="
    )
    _kb, _ci, _faqs, _services, hours = parse_auto_kb_response(raw)
    assert hours.get("Mon") == "8am-6pm"
    assert hours.get("Tue") == "8am-6pm"
    assert hours.get("Sat") == "closed"
