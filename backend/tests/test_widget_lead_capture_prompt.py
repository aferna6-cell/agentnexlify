"""Lane 1 — widget lead-capture conversion fixes.

Prod funnel showed 2,717 chat_messages -> 27 leads (~1%). Root cause was the
system prompt only asking for contact info on explicit buying intent and only
accepting email. The fix makes the AI proactively ask for name + email OR phone
after 3+ messages, and accept phone-only contact.

These assert the prompt-level contract. The lead-save path (phone-only dedup +
insert) is already covered by widget_lead_helpers and exercised separately.
"""

from backend.routers.widget_chat_helpers import _build_system_prompt

_TENANT = {"business_name": "Acme Salon", "business_type": "salon"}


def _prompt() -> str:
    return _build_system_prompt(_TENANT, [])


def test_prompt_asks_for_email_or_phone():
    """Contact ask must accept phone OR email, not email only."""
    p = _prompt().lower()
    assert "email or phone" in p


def test_prompt_has_proactive_three_message_nudge():
    """After 3+ messages with no contact, the AI should gently ask."""
    p = _prompt().lower()
    assert "3 or more messages" in p


def test_prompt_still_guards_first_message():
    """Don't ask for contact on the very first message / casual greeting."""
    p = _prompt().lower()
    assert "first message" in p


def test_prompt_does_not_reask_after_contact_given():
    """Once contact is shared, never re-ask."""
    p = _prompt().lower()
    assert "never ask for contact info again" in p


def test_prompt_triggers_on_pricing_intent():
    """Pricing/services/availability/quote should trigger the contact ask."""
    p = _prompt().lower()
    assert "pricing" in p and "quote" in p
