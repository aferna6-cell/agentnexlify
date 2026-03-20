"""Tests for lead info extraction from chat messages.

These test the _extract_lead_info function in widget.py which parses
names, emails, and phone numbers from user messages.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.routers.widget_helpers import _extract_lead_info, PHONE_RE, EMAIL_RE


# ── Phone regex tests ────────────────────────────────────────


class TestPhoneRegex:
    """Test the phone number regex matches international formats."""

    def test_us_standard(self):
        assert PHONE_RE.search("555-123-4567")

    def test_us_with_parens(self):
        assert PHONE_RE.search("(555) 123-4567")

    def test_us_with_country_code(self):
        assert PHONE_RE.search("+1 555-123-4567")

    def test_us_dots(self):
        assert PHONE_RE.search("555.123.4567")

    def test_uk_number(self):
        assert PHONE_RE.search("+44 20 1234 5678")

    def test_india_number(self):
        assert PHONE_RE.search("+91 98765 43210")

    def test_germany_number(self):
        assert PHONE_RE.search("+49 30 12345678")

    def test_short_number_rejected(self):
        """Numbers with fewer than 7 digits should not be captured as phone."""
        info = _extract_lead_info("call me at 12 34")
        assert "phone" not in info

    def test_embedded_in_text(self):
        info = _extract_lead_info("my number is +44 20 7946 0958 thanks")
        assert "phone" in info
        assert "+44" in info["phone"]

    def test_us_embedded_in_text(self):
        info = _extract_lead_info("You can reach me at (555) 123-4567")
        assert "phone" in info
        assert "555" in info["phone"]


# ── Email extraction tests ───────────────────────────────────


class TestEmailExtraction:
    """Test email parsing from chat messages."""

    def test_simple_email(self):
        info = _extract_lead_info("my email is john@example.com")
        assert info.get("email") == "john@example.com"

    def test_email_with_plus(self):
        info = _extract_lead_info("john+test@example.com")
        assert info.get("email") == "john+test@example.com"

    def test_email_with_spaces_around_at(self):
        """The extractor normalizes spaces around @."""
        info = _extract_lead_info("sara @ test.com")
        assert info.get("email") == "sara@test.com"

    def test_no_email_in_text(self):
        info = _extract_lead_info("I just want to ask a question")
        assert "email" not in info

    def test_email_case_normalized(self):
        info = _extract_lead_info("John@Example.COM")
        assert info.get("email") == "john@example.com"


# ── Name extraction tests ───────────────────────────────────


class TestNameExtraction:
    """Test name parsing from chat messages."""

    def test_name_with_greeting(self):
        info = _extract_lead_info("Hi, I'm John Smith")
        assert info.get("name") == "John Smith"

    def test_name_with_my_name_is(self):
        info = _extract_lead_info("My name is Jane Doe")
        assert info.get("name") == "Jane Doe"

    def test_standalone_name(self):
        """A message that is just a capitalized name."""
        info = _extract_lead_info("John Smith")
        assert info.get("name") == "John Smith"

    def test_no_name_in_question(self):
        info = _extract_lead_info("What are your prices?")
        assert "name" not in info


# ── Combined extraction tests ────────────────────────────────


class TestCombinedExtraction:
    """Test extracting multiple fields from a single message."""

    def test_email_and_phone(self):
        info = _extract_lead_info("john@test.com and my phone is 555-123-4567")
        assert info.get("email") == "john@test.com"
        assert "phone" in info

    def test_all_fields(self):
        info = _extract_lead_info("I'm John, email john@test.com, phone 555-123-4567")
        assert info.get("name") == "John"
        assert info.get("email") == "john@test.com"
        assert "phone" in info

    def test_empty_message(self):
        info = _extract_lead_info("")
        assert info == {}

    def test_whitespace_only(self):
        info = _extract_lead_info("   ")
        assert info == {}


# ── Partial info tests (backlog item) ────────────────────────


class TestPartialInfo:
    """Test lead capture with partial information — name only, no email."""

    def test_name_only(self):
        info = _extract_lead_info("My name is Sarah")
        assert info.get("name") == "Sarah"
        assert "email" not in info
        assert "phone" not in info

    def test_phone_only(self):
        info = _extract_lead_info("+1 555 987 6543")
        assert "phone" in info
        assert "email" not in info

    def test_email_only(self):
        info = _extract_lead_info("test@example.org")
        assert info.get("email") == "test@example.org"
        assert "phone" not in info
