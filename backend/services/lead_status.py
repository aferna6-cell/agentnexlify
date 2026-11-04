"""Map pipeline stage labels onto the leads.status check constraint.

``leads_status_check`` allows only:
new, contacted, appointment_booked, closed, lost.

The dashboard pipeline uses display names ("New Lead", "Won", "Booked").
Those names belong in ``pipeline_stage``. ``status`` stays canonical.
"""

import re

ALLOWED_LEAD_STATUSES = (
    "new",
    "contacted",
    "appointment_booked",
    "closed",
    "lost",
)
_ALLOWED = set(ALLOWED_LEAD_STATUSES)


class UnknownLeadStatus(ValueError):
    """Raised when a status string is not canonical and not a known stage alias."""

    def __init__(self, raw: str):
        self.raw = raw
        super().__init__(raw)


def is_check_violation(exc: BaseException) -> bool:
    """True for Postgres check_violation (SQLSTATE 23514)."""
    code = getattr(exc, "code", None)
    if str(code) == "23514":
        return True
    args = getattr(exc, "args", ())
    if args and isinstance(args[0], dict) and str(args[0].get("code")) == "23514":
        return True
    blob = str(exc).lower()
    return "23514" in blob or "check constraint" in blob


def canonical_lead_status(raw: str | None) -> str:
    """Return a leads.status value, or raise UnknownLeadStatus.

    Empty input defaults to ``new``. Already-allowed values pass through.
    Known stage labels map as:
    New Lead → new, Contacted → contacted, booked/appointment →
    appointment_booked, won → closed, lost → lost.
    """
    text = (raw or "").strip()
    if not text:
        return "new"

    spaced = " ".join(text.lower().replace("-", " ").replace("_", " ").split())
    underscored = spaced.replace(" ", "_")
    if underscored in _ALLOWED:
        return underscored

    if spaced == "new lead" or spaced.startswith("new lead"):
        return "new"
    if "contacted" in spaced:
        return "contacted"
    if "booked" in spaced or "appointment" in spaced:
        return "appointment_booked"
    if re.search(r"\bwon\b", spaced):
        return "closed"
    if re.search(r"\blost\b", spaced):
        return "lost"
    raise UnknownLeadStatus(text)


def stage_label_for_lead(lead: dict, stages: list[dict]) -> str | None:
    """Column name this lead belongs in on the pipeline board.

    ``pipeline_stage`` wins when it names a real stage. Otherwise a canonical
    ``status`` lands on the stage whose label maps to that status.
    """
    names = {(s.get("name") or "").lower(): s.get("name") for s in stages if s.get("name")}
    explicit = (lead.get("pipeline_stage") or "").strip()
    if explicit and explicit.lower() in names:
        return names[explicit.lower()]

    status = (lead.get("status") or "").strip()
    if status.lower() in names:
        return names[status.lower()]

    try:
        canonical = canonical_lead_status(status)
    except UnknownLeadStatus:
        return None

    matches: list[str] = []
    for stage in stages:
        name = stage.get("name") or ""
        if not name:
            continue
        try:
            if canonical_lead_status(name) == canonical:
                matches.append(name)
        except UnknownLeadStatus:
            continue
    if not matches:
        return None

    preferred = {
        "new": ("new lead",),
        "contacted": ("contacted",),
        "appointment_booked": ("booked", "appointment booked", "appointment"),
        "closed": ("closed", "won"),
        "lost": ("lost",),
    }.get(canonical, ())
    lowered = {name.lower(): name for name in matches}
    for want in preferred:
        if want in lowered:
            return lowered[want]
    return matches[0]
