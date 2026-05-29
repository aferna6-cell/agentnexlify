"""Bracketed-placeholder detection (rule 2).

No agent may emit ``[Shop Name]`` / ``[Your Name]`` / ``[Phone]`` style
placeholders for fields that exist in the business profile. The QA report
traced production bugs to exactly this. Our posture is stricter and simpler to
enforce: **customer-facing drafts contain no bracketed placeholder tokens at
all.** If a needed value is genuinely missing from the profile, the agent
surfaces the gap to the orchestrator chat instead of leaving a bracket in the
draft.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_os.profile import BusinessProfile

# Matches a bracketed token like "[Shop Name]" or "[methods]". We require the
# inside to look like a placeholder (letters/spaces/slashes) and short, so we
# don't trip on things like "[1]" footnote markers in owner reports.
_PLACEHOLDER_RE = re.compile(r"\[([A-Za-z][A-Za-z /_'-]{1,40})\]")

# Known placeholder spellings mapped to the profile field they should have used.
PLACEHOLDER_TO_FIELD: dict[str, str] = {
    "shop name": "business_name",
    "business name": "business_name",
    "company name": "business_name",
    "your name": "owner_name",
    "owner name": "owner_name",
    "name": "owner_name",
    "phone": "phone",
    "phone number": "phone",
    "website": "website",
    "city": "city",
    "industry": "industry",
    "email": "email",
}


@dataclass(frozen=True)
class PlaceholderFinding:
    token: str  # the raw matched text, e.g. "[Shop Name]"
    label: str  # normalized inside, e.g. "shop name"
    maps_to_field: str | None  # profile field this should have used, if known


def find_placeholders(text: str) -> list[PlaceholderFinding]:
    """Return all bracketed placeholders in *text*."""

    findings: list[PlaceholderFinding] = []
    for match in _PLACEHOLDER_RE.finditer(text):
        label = match.group(1).strip().lower()
        findings.append(
            PlaceholderFinding(
                token=match.group(0),
                label=label,
                maps_to_field=PLACEHOLDER_TO_FIELD.get(label),
            )
        )
    return findings


def placeholders_for_present_fields(
    text: str, profile: BusinessProfile
) -> list[PlaceholderFinding]:
    """Placeholders that should have used a value the profile actually has.

    This is the precise wording of rule 2. The registry uses the stricter
    "no placeholders at all in customer-facing drafts" check, but this function
    lets the orchestrator explain *why* a draft was rejected.
    """

    return [
        f
        for f in find_placeholders(text)
        if f.maps_to_field and profile.has(f.maps_to_field)
    ]
