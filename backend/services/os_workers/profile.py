"""Business profile helpers shared across all LLM-backed Agent OS workers.

Wires the signup-captured business profile (business name, owner, industry,
city, phone, website) into every worker prompt so drafts stop emitting
``[Shop Name]``, ``[Your Name]``, ``[Phone]``, ``[Website]`` placeholders when
real data exists.

Single concern: format ``WorkerTools.tenant_profile()`` output into prompt
fragments and reasoning-trace steps. No I/O, no Claude calls, pure formatting.
"""

from typing import Any

PLACEHOLDER_INSTRUCTION = (
    "Use the Business Profile data above wherever a draft would otherwise "
    "contain placeholders like [Shop Name], [Your Name], [Phone], or "
    "[Website]. Only emit bracketed placeholders for data that genuinely is "
    "not in the profile."
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def profile_has_data(profile: dict | None) -> bool:
    """True iff the profile carries a business name (the minimum signal).

    A profile with only a ``client_id`` and no business name is treated as
    empty — that's the "no business profile yet" path.
    """
    if not profile:
        return False
    return bool(_clean(profile.get("business_name")))


def format_business_profile_block(profile: dict | None) -> str:
    """Return the 6-field Business Profile block, or ``""`` when empty.

    Fields render as ``"not provided"`` when missing so workers can still cite
    presence/absence consistently in drafts.
    """
    if not profile_has_data(profile):
        return ""

    business_name = _clean(profile.get("business_name"))
    owner_name = _clean(profile.get("owner_name"))
    industry = _clean(profile.get("business_type"))
    city = _clean(profile.get("city")) or _clean(profile.get("business_city"))
    phone = _clean(profile.get("business_phone")) or _clean(
        profile.get("notification_phone")
    )
    website = _clean(profile.get("website_url"))

    def _or_missing(value: str) -> str:
        return value if value else "not provided"

    lines = [
        "Business Profile:",
        f"- Business name: {_or_missing(business_name)}",
        f"- Owner name: {_or_missing(owner_name)}",
        f"- Industry: {_or_missing(industry)}",
        f"- City: {_or_missing(city)}",
        f"- Phone: {_or_missing(phone)}",
        f"- Website: {_or_missing(website)}",
    ]
    return "\n".join(lines)


def profile_trace_step(profile: dict | None) -> tuple[str, str]:
    """Reasoning-trace label + detail for profile load result.

    Returns ``("Loaded business profile", "<name>, <industry>, <city>")`` when
    populated, or ``("No business profile yet", "Using fallback")`` when not.
    Workers should NOT emit a "loading profile" step before this — only emit
    one trace step based on the outcome.
    """
    if not profile_has_data(profile):
        return ("No business profile yet", "Using fallback")

    business_name = _clean(profile.get("business_name"))
    industry = _clean(profile.get("business_type")) or "industry not set"
    city = (
        _clean(profile.get("city"))
        or _clean(profile.get("business_city"))
        or "city not set"
    )
    detail = f"{business_name}, {industry}, {city}"
    return ("Loaded business profile", detail)
