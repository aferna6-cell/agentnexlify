"""Pure helpers for send_birthday_greetings — filter + email composition."""

__all__ = ["filter_birthday_leads", "build_birthday_greeting_email"]


def filter_birthday_leads(leads: list, today_mmdd: str) -> list:
    """Return only leads whose date_of_birth MM-DD matches today_mmdd (MM-DD)."""
    return [
        lead
        for lead in leads
        if (lead.get("date_of_birth") or "")[5:10] == today_mmdd
    ]


def build_birthday_greeting_email(
    customer_name: str, business_name: str
) -> tuple[str, str]:
    """Return (subject, body_html) for a birthday greeting email."""
    subject = f"Happy Birthday from {business_name}!"
    body = (
        f"<h2>Happy Birthday, {customer_name}!</h2>"
        f"<p>Everyone at <strong>{business_name}</strong> wishes you a wonderful birthday!</p>"
        f"<p>As a special thank you for being a valued client, we'd love to see you soon. "
        f"Reply to this email or contact us to schedule your next visit.</p>"
        f"<p>Best wishes,<br>The {business_name} Team</p>"
    )
    return subject, body
