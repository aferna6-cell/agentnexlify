"""AI-powered intent detection for widget conversations.

Uses lightweight classification to route conversations appropriately
instead of relying on brittle regex patterns.
"""

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    BOOKING = "booking"
    PRICING = "pricing"
    HOURS = "hours"
    SERVICES = "services"
    SUPPORT = "support"
    GENERAL = "general"
    COMPLAINT = "complaint"
    GOODBYE = "goodbye"


# Lightweight regex-based fallback classifier (fast, no LLM cost)
# Order matters — more specific patterns should come first
_INTENT_PATTERNS = [
    (UserIntent.GOODBYE, re.compile(
        r"\b(thank you|thanks\b.*bye|goodbye|see you|talk later|have a good|appreciate it)\b",
        re.IGNORECASE,
    )),
    (UserIntent.COMPLAINT, re.compile(
        r"\b(angry|unhappy|dissatisfied|terrible(?!.*service\b)|worst|horrible|disgusting|scam|fraud|lawyer|sue|bad review)\b",
        re.IGNORECASE,
    )),
    (UserIntent.PRICING, re.compile(
        r"(price|cost|how much|rate|rates|fee|pricing|charge|afford|cheap|expensive|discount|quote|estimate)",
        re.IGNORECASE,
    )),
    (UserIntent.BOOKING, re.compile(
        r"\b(book|appointment|schedule\b|reserve|slot|calendar|time slot)\b",
        re.IGNORECASE,
    )),
    (UserIntent.HOURS, re.compile(
        r"\b(when.*open|when.*close|business hours|what.*hour|what.*time.*open)\b",
        re.IGNORECASE,
    )),
    (UserIntent.SERVICES, re.compile(
        r"\b(what.*service|what.*offer|do you (do|provide|handle|work on)|specialize)\b",
        re.IGNORECASE,
    )),
    (UserIntent.SUPPORT, re.compile(
        r"\b(help|issue|problem|broken|not working|error|complaint|refund|cancel)\b",
        re.IGNORECASE,
    )),
]


def detect_intent(message: str, conversation_context: list[dict] | None = None) -> UserIntent:
    """Detect user intent from message text with optional conversation context.

    Uses a two-pass approach:
    1. Check for explicit patterns (regex-based, fast)
    2. Consider conversation context for disambiguation

    Args:
        message: The user's message text
        conversation_context: Recent conversation turns for context

    Returns:
        Detected UserIntent enum value
    """
    if not message or not message.strip():
        return UserIntent.GENERAL

    message = message.strip()

    # Pass 1: Check explicit patterns (ordered list — first match wins)
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(message):
            detected = [intent]
            break
    else:
        # No pattern matched — check for question patterns
        if message.endswith("?"):
            if any(word in message.lower() for word in ["how much", "cost", "price"]):
                return UserIntent.PRICING
            if any(word in message.lower() for word in ["when", "what time", "hour"]):
                return UserIntent.HOURS
        return UserIntent.GENERAL

    # Pass 2: Disambiguate with context (if multiple could apply)
    primary = detected[0]

    # Special case: "schedule" in a question about availability should NOT trigger booking
    if primary == UserIntent.BOOKING and "?" in message:
        lower = message.lower()
        if "available" in lower or "availability" in lower:
            if not any(word in lower for word in ["book", "appointment", "reserve"]):
                return UserIntent.HOURS

    return primary


def _disambiguate_with_context(
    detected: list[UserIntent], message: str, context: list[dict]
) -> UserIntent:
    """Use conversation context to pick the most likely intent."""
    # Check recent assistant messages for cues
    recent_assistant = [
        m for m in reversed(context) if m.get("role") == "assistant"
    ][:3]

    assistant_text = " ".join(
        m.get("content", "") for m in recent_assistant
    ).lower()

    # If assistant just mentioned pricing, and user says "how much" → pricing
    if UserIntent.PRICING in detected and any(
        word in assistant_text for word in ["price", "cost", "rate", "fee", "$"]
    ):
        return UserIntent.PRICING

    # If assistant offered times/slots, and user picks one → booking
    if UserIntent.BOOKING in detected and any(
        word in assistant_text for word in ["available", "slot", "time", "book", "appointment"]
    ):
        return UserIntent.BOOKING

    # Default to first detected intent
    return detected[0]


def should_trigger_booking(message: str, context: list[dict] | None = None) -> bool:
    """Determine if the message should trigger the booking UI.

    More conservative than detect_intent() — only returns True for
    clear booking intent, not ambiguous inquiries.
    """
    intent = detect_intent(message, context)
    if intent != UserIntent.BOOKING:
        return False

    # Extra guard: don't hijack the conversation if the user is asking
    # a question about availability without clear booking intent
    lower = message.lower()
    if "?" in message and not any(
        word in lower for word in ["book", "appointment", "schedule", "reserve", "slot"]
    ):
        return False

    return True


def get_intent_summary(intent: UserIntent) -> str:
    """Get a human-readable summary of the detected intent."""
    summaries = {
        UserIntent.BOOKING: "User wants to book/schedule something",
        UserIntent.PRICING: "User is asking about pricing",
        UserIntent.HOURS: "User is asking about business hours",
        UserIntent.SERVICES: "User is asking about services offered",
        UserIntent.SUPPORT: "User needs help or has an issue",
        UserIntent.COMPLAINT: "User is expressing dissatisfaction",
        UserIntent.GOODBYE: "User is ending the conversation",
        UserIntent.GENERAL: "General inquiry or statement",
    }
    return summaries.get(intent, "Unknown intent")
