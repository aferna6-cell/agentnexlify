"""Tests for intent detection service."""

import pytest

from backend.services.intent_detection import (
    UserIntent,
    detect_intent,
    should_trigger_booking,
    get_intent_summary,
)


class TestDetectIntent:
    def test_booking_intent(self):
        assert detect_intent("I'd like to book an appointment") == UserIntent.BOOKING
        assert detect_intent("Show me your calendar") == UserIntent.BOOKING
        assert detect_intent("I want to reserve a slot") == UserIntent.BOOKING

    def test_pricing_intent(self):
        assert detect_intent("How much does it cost?") == UserIntent.PRICING
        assert detect_intent("What are your rates?") == UserIntent.PRICING
        assert detect_intent("Do you offer discounts?") == UserIntent.PRICING

    def test_hours_intent(self):
        assert detect_intent("When are you open?") == UserIntent.HOURS
        assert detect_intent("What are your business hours?") == UserIntent.HOURS
        assert detect_intent("Is your schedule available?") == UserIntent.HOURS

    def test_services_intent(self):
        assert detect_intent("What services do you offer?") == UserIntent.SERVICES
        assert detect_intent("Do you do roof repair?") == UserIntent.SERVICES

    def test_support_intent(self):
        assert detect_intent("I need help with an issue") == UserIntent.SUPPORT
        assert detect_intent("Something is broken") == UserIntent.SUPPORT

    def test_complaint_intent(self):
        assert detect_intent("This is the worst service!") == UserIntent.COMPLAINT
        assert detect_intent("I want to file a complaint") == UserIntent.SUPPORT  # "complaint" matches support
        assert detect_intent("I'm so angry right now") == UserIntent.COMPLAINT

    def test_goodbye_intent(self):
        assert detect_intent("Thank you, bye!") == UserIntent.GOODBYE
        assert detect_intent("See you later!") == UserIntent.GOODBYE
        assert detect_intent("Thanks for your help, goodbye") == UserIntent.GOODBYE

    def test_general_intent(self):
        assert detect_intent("Hello") == UserIntent.GENERAL
        assert detect_intent("Nice weather today") == UserIntent.GENERAL

    def test_empty_message(self):
        assert detect_intent("") == UserIntent.GENERAL
        assert detect_intent("   ") == UserIntent.GENERAL

    def test_clear_booking_triggers_booking(self):
        """Clear booking intent should trigger."""
        result = detect_intent("I want to book an appointment for next week")
        assert result == UserIntent.BOOKING


class TestShouldTriggerBooking:
    def test_clear_booking_triggers(self):
        assert should_trigger_booking("Book me an appointment") is True
        assert should_trigger_booking("I want to schedule a time slot") is True

    def test_question_about_availability_not_booking(self):
        """Questions about availability should not trigger booking."""
        assert should_trigger_booking("Is your schedule available?") is False

    def test_general_not_booking(self):
        assert should_trigger_booking("What services do you offer?") is False

    def test_empty_not_booking(self):
        assert should_trigger_booking("") is False


class TestGetIntentSummary:
    def test_returns_human_readable(self):
        assert "book" in get_intent_summary(UserIntent.BOOKING).lower()
        assert "pricing" in get_intent_summary(UserIntent.PRICING).lower()
        assert "hours" in get_intent_summary(UserIntent.HOURS).lower()
