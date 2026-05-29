"""The business profile substrate.

This is the single highest-leverage dependency in the whole system (product
plan, Phase 1.1). Every agent reads the profile and fills real values into its
drafts. When a core field is genuinely missing, the agent surfaces that to the
orchestrator chat — never to the customer, and never as a ``[bracket]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The six core fields the product plan calls out explicitly. If one of these is
# present, an agent must use the real value and must never emit a placeholder
# for it.
CORE_FIELDS: tuple[str, ...] = (
    "business_name",
    "owner_name",
    "industry",
    "city",
    "phone",
    "website",
)


@dataclass
class KBEntry:
    """One owner-curated knowledge-base / FAQ entry."""

    question: str
    answer: str
    topics: tuple[str, ...] = ()


@dataclass
class BusinessProfile:
    """Structured business profile captured at signup.

    Any field may be ``None``/empty. The agents and the honest-trace machinery
    are responsible for behaving correctly when data is missing rather than
    pretending it loaded.
    """

    business_name: str | None = None
    owner_name: str | None = None
    industry: str | None = None
    city: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    services: list[str] = field(default_factory=list)
    hours: str | None = None
    timezone: str = "America/Los_Angeles"
    review_link_google: str | None = None
    review_link_yelp: str | None = None
    review_link_facebook: str | None = None
    payment_link: str | None = None
    knowledge_base: list[KBEntry] = field(default_factory=list)

    # ----- presence helpers -----
    def value(self, field_name: str) -> str | None:
        """Return the non-empty value of *field_name*, or ``None``."""

        raw = getattr(self, field_name, None)
        if raw is None:
            return None
        if isinstance(raw, str):
            stripped = raw.strip()
            return stripped or None
        if isinstance(raw, (list, tuple)):
            return ", ".join(str(x) for x in raw) if raw else None
        return str(raw)

    def has(self, field_name: str) -> bool:
        return self.value(field_name) is not None

    def has_any(self) -> bool:
        return any(self.has(f) for f in CORE_FIELDS)

    def present_core_fields(self) -> list[str]:
        return [f for f in CORE_FIELDS if self.has(f)]

    def missing_core_fields(self) -> list[str]:
        return [f for f in CORE_FIELDS if not self.has(f)]

    def loaded_summary(self) -> str | None:
        """Human-readable summary of what actually loaded, for the trace.

        Returns ``None`` when nothing loaded — callers must treat that as a
        no-load (honest-trace rule)."""

        present = self.present_core_fields()
        extras = [
            label
            for label, ok in (
                ("hours", bool(self.hours)),
                ("services", bool(self.services)),
                ("knowledge base", bool(self.knowledge_base)),
            )
            if ok
        ]
        parts = [f.replace("_", " ") for f in present] + extras
        return ", ".join(parts) if parts else None

    # ----- signoff helper used by many agents -----
    def signoff(self) -> str:
        """Best available signoff line, e.g. "Alex, Sunset Mobile Detailing"."""

        name = self.value("owner_name")
        biz = self.value("business_name")
        if name and biz:
            return f"{name}, {biz}"
        return name or biz or ""

    @property
    def domain(self) -> str | None:
        site = self.value("website")
        if not site:
            return None
        return site.replace("https://", "").replace("http://", "").rstrip("/")
