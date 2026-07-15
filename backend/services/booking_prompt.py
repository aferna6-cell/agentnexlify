"""Booking system-prompt suffix for the widget AI.

Pure string builder, extracted from the widget_chat god file (user-rules Rule 9)
so it is unit-testable in isolation.

Why this exists: the widget AI's only way to let a visitor book is the public
booking page, addressed by ``business_slug`` (``/api/v1/book/{slug}``). The
original prompt told the AI to "offer the booking link" but never gave it the
URL — so the AI had no link to share and bookings stalled even when booking was
fully enabled (found 2026-07-15: MTOptions had 21 leads / 0 appointments with
booking_enabled + hours + slug all set). This builds the real URL into the
prompt, and — when no slug is configured — steers the AI to capture contact
info instead of inventing a URL that 404s.
"""

_DEFAULT_BASE_URL = "https://app.agentnexlify.com"


def booking_prompt_suffix(
    *,
    booking_enabled: bool,
    business_slug: str | None,
    frontend_url: str | None,
) -> str:
    """Return the BOOKING section to append to the widget system prompt.

    Empty string when booking is disabled. When a slug exists, the exact
    public booking URL is embedded and the AI is told to share it verbatim.
    When booking is enabled but no slug is set, the AI is told to collect
    contact details instead of fabricating a link.
    """
    if not booking_enabled:
        return ""

    slug = (business_slug or "").strip()
    if slug:
        base_url = (frontend_url or _DEFAULT_BASE_URL).rstrip("/")
        booking_url = f"{base_url}/api/v1/book/{slug}"
        return (
            "\n\nBOOKING: This business has online booking enabled. "
            "When the visitor shows any interest in a service, pricing, or scheduling — or once "
            "they have shared their name and contact info — actively offer to book them an "
            f"appointment and share this exact booking link: {booking_url} — then ask for their "
            "preferred day and time. Make booking the clear next step rather than waiting for "
            "them to ask. Share the link verbatim; never invent a different URL."
        )

    return (
        "\n\nBOOKING: This business has online booking enabled but no public booking "
        "page is configured yet, so there is no link to share. When the visitor shows "
        "interest in scheduling, collect their name, contact info, and preferred day/time "
        "so the business can confirm the appointment directly. Do not invent a booking URL."
    )
