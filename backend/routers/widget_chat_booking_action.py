"""SHOW_BOOKING_PANEL marker detection for widget chat (GH #573).

Pure string helper, own module per Rule 12. The widget's native booking panel
used to open only on a user-text keyword regex (book/appointment/schedule/…),
so the AI could never open it — visitors got an external booking-page link
instead, and in-chat bookings never happened (funnel audit 2026-07-23: zero
real bookings platform-wide). booking_prompt.py now tells the model to append
the SHOW_BOOKING_PANEL token when the visitor is ready to pick a time; this
strips the token and surfaces a structured flag the widget acts on. Same
marker pattern as HANDOFF_REQUESTED (widget_chat_effects.handle_handoff_detection).
"""

import re

SHOW_BOOKING_MARKER = "SHOW_BOOKING_PANEL"

# Collapse the space left behind by a mid-text marker ("a. MARKER b." → "a. b.")
_MARKER_RE = re.compile(r"\s*" + re.escape(SHOW_BOOKING_MARKER) + r"\s*")


def detect_show_booking(assistant_text: str, *, booking_enabled: bool) -> tuple[str, bool]:
    """Strip SHOW_BOOKING_PANEL from the model reply.

    Returns (clean_text, show_booking). The marker is ALWAYS stripped (it must
    never render to a visitor), but the flag only fires when the tenant has
    booking enabled — a hallucinated marker on a booking-disabled tenant is
    swallowed silently. The widget double-gates on its own bookingEnabled.
    """
    if SHOW_BOOKING_MARKER not in assistant_text:
        return assistant_text, False

    clean = _MARKER_RE.sub(" ", assistant_text).strip()
    return clean, bool(booking_enabled)
