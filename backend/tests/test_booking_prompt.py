"""Tests for the widget booking system-prompt suffix.

Regression for the money-path bug found 2026-07-15: the widget AI was told to
"offer the booking link" but the URL was never injected, so a fully-configured
customer (MTOptions: 21 leads, booking_enabled + hours + slug) got 0 bookings.
"""

from backend.services.booking_prompt import booking_prompt_suffix


class TestBookingDisabled:
    def test_returns_empty_when_disabled(self):
        assert booking_prompt_suffix(
            booking_enabled=False, business_slug="x", frontend_url=None
        ) == ""


class TestSlugPresent:
    def test_real_url_injected_verbatim(self):
        out = booking_prompt_suffix(
            booking_enabled=True,
            business_slug="mtoptions",
            frontend_url="https://app.agentnexlify.com",
        )
        assert "https://app.agentnexlify.com/api/v1/book/mtoptions" in out
        assert "never invent a different URL" in out

    def test_trailing_slash_on_base_url_normalised(self):
        out = booking_prompt_suffix(
            booking_enabled=True,
            business_slug="acme",
            frontend_url="https://app.agentnexlify.com/",
        )
        assert "https://app.agentnexlify.com/api/v1/book/acme" in out
        assert "book//acme" not in out

    def test_default_base_url_when_frontend_url_missing(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug="acme", frontend_url=None
        )
        assert "https://app.agentnexlify.com/api/v1/book/acme" in out

    def test_whitespace_slug_treated_as_present_after_strip(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug="  acme  ", frontend_url=None
        )
        assert "/api/v1/book/acme" in out


class TestSlugMissing:
    def test_no_link_promised_and_captures_contact(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug=None, frontend_url=None
        )
        assert "no public booking page is configured" in out
        assert "Do not invent a booking URL" in out
        assert "/api/v1/book/" not in out

    def test_empty_string_slug_is_missing(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug="", frontend_url=None
        )
        assert "/api/v1/book/" not in out

    def test_whitespace_only_slug_is_missing(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug="   ", frontend_url=None
        )
        assert "/api/v1/book/" not in out
