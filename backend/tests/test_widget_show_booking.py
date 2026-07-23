"""Tests for the SHOW_BOOKING_PANEL marker (GH #573).

The widget's native booking panel previously opened only on a user-text
keyword regex; the AI had no way to open it, so booking CTAs degraded to an
external link. The model now appends SHOW_BOOKING_PANEL when the visitor is
ready to pick a time; the backend strips the marker and returns
show_booking=True so the widget calls showBooking().

Run: pytest backend/tests/test_widget_show_booking.py --noconftest -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.models.schemas import WidgetChatResponse
from backend.routers.widget_chat_booking_action import detect_show_booking
from backend.services.booking_prompt import booking_prompt_suffix


class TestDetectShowBooking:
    def test_marker_stripped_and_flag_set(self):
        text, flag = detect_show_booking(
            "Great, let's get you scheduled! SHOW_BOOKING_PANEL", booking_enabled=True
        )
        assert flag is True
        assert "SHOW_BOOKING_PANEL" not in text
        assert text == "Great, let's get you scheduled!"

    def test_no_marker_passthrough(self):
        text, flag = detect_show_booking("We open at 9am.", booking_enabled=True)
        assert flag is False
        assert text == "We open at 9am."

    def test_marker_stripped_but_flag_suppressed_when_booking_disabled(self):
        # A hallucinated marker on a booking-disabled tenant must never leak
        # to the visitor NOR open a panel the tenant can't serve.
        text, flag = detect_show_booking(
            "Sure! SHOW_BOOKING_PANEL", booking_enabled=False
        )
        assert flag is False
        assert "SHOW_BOOKING_PANEL" not in text

    def test_mid_text_marker_stripped_cleanly(self):
        text, flag = detect_show_booking(
            "Let me open the scheduler. SHOW_BOOKING_PANEL Pick any slot.",
            booking_enabled=True,
        )
        assert flag is True
        assert "SHOW_BOOKING_PANEL" not in text
        assert "Pick any slot." in text


class TestResponseModel:
    def test_show_booking_defaults_false(self):
        resp = WidgetChatResponse(
            response="hi",
            session_id="s1",
            lead_captured=False,
            show_watermark=True,
        )
        assert resp.show_booking is False


class TestPromptInstructsMarker:
    def test_prompt_mentions_marker_when_booking_enabled(self):
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug="acme", frontend_url=None
        )
        assert "SHOW_BOOKING_PANEL" in out

    def test_prompt_mentions_marker_even_without_slug(self):
        # The native panel does not need a booking page/slug — slot data comes
        # from the appointments API, so slug-less tenants get the panel too.
        out = booking_prompt_suffix(
            booking_enabled=True, business_slug=None, frontend_url=None
        )
        assert "SHOW_BOOKING_PANEL" in out

    def test_prompt_silent_when_booking_disabled(self):
        assert booking_prompt_suffix(
            booking_enabled=False, business_slug=None, frontend_url=None
        ) == ""
