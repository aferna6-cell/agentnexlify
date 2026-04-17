"""Base dataclasses + seeding helpers for industry packs.

An Industry Pack bundles the turnkey workflow content a tenant needs to go
from signup to value on day one:

- Form presets (new patient intake, insurance collection, quote request, etc.)
- Sequence templates (appt reminder, dunning ladder, reactivation)
- Smart lists (lapsed clients, unpaid invoices, high-value leads)
- Automation rules (post-appt review trigger, CSAT gate, overdue alert)
- KB seed articles (industry-specific FAQs the widget chat should answer)

Packs are pure data. Seeding them into a tenant is a separate operation
(`apply_pack_to_tenant`) that writes to the existing `forms`,
`automation_sequences`, `automation_steps`, `smart_lists`,
`automation_rules`, and `kb_articles` tables with a
`source='industry_pack:{pack.key}'` tag. No new migration required.

Idempotent: applying the same pack twice is a no-op because the seed
function checks for existing rows with the same `source` + `name` combo.
Upgrading a pack (new version) can update rows matching the tag while
leaving tenant customizations (identified by absence of the tag) alone.
"""

from dataclasses import dataclass, field
from typing import Any


# ----------------------------------------------------------------------
# Pack components — pure data
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class FormPreset:
    """A form preset shipped as part of an industry pack.

    If `preset_key` references a preset already defined in
    `backend/routers/forms.py:_FORM_PRESETS`, the seeder will look it up
    there rather than duplicating the field list. If `fields` is non-empty,
    the pack ships its own custom form definition.
    """

    key: str
    name: str
    description: str
    preset_key: str | None = None  # reference to forms.py _FORM_PRESETS
    fields: list[dict[str, Any]] = field(default_factory=list)
    success_message: str = "Thank you — we'll be in touch shortly."


@dataclass(frozen=True)
class SequenceStep:
    """A single step in a sequence template."""

    step_order: int
    delay_minutes: int
    subject_template: str
    body_template: str
    action_type: str = "email"  # email | sms


@dataclass(frozen=True)
class SequenceTemplate:
    """A multi-step sequence (appointment reminder, dunning ladder, etc.)."""

    key: str
    name: str
    trigger_event: str
    trigger_config: dict[str, Any] = field(default_factory=dict)
    steps: list[SequenceStep] = field(default_factory=list)


@dataclass(frozen=True)
class SmartListTemplate:
    """A smart list definition (saved filter over leads/appointments/invoices)."""

    key: str
    name: str
    description: str
    entity: str  # "leads" | "appointments" | "invoices"
    filter: dict[str, Any] = field(default_factory=dict)
    # Example filter: {"last_appointment_date": {"lt": "now-180d"}, "status": "active"}


@dataclass(frozen=True)
class AutomationRuleTemplate:
    """A declarative automation rule: on {event} [+ condition] do {action}.

    Maps to the existing `automation_rules` table used by
    `backend/services/automation_engine.py`.
    """

    key: str
    name: str
    trigger_event: str
    condition: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class KBSeedArticle:
    """A knowledge base seed article — industry-specific FAQ the widget
    chat should be able to answer on day one."""

    title: str
    body: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IndustryAIPersona:
    """Industry-specific AI persona for the widget chat system prompt.

    Injected into `_build_system_prompt` via `load_pack(business_type).ai_persona`.
    Keeps hardcoded compliance/tone blocks out of widget code — each industry
    pack owns its own persona.

    All fields default to empty so packs can opt in to only what they need.
    """

    # Appended after "You are a friendly AI assistant for {business}."
    # Example: "You specialize in answering questions about dental care and booking appointments."
    identity_addendum: str = ""

    # Bullet-point tone/style cues. Rendered as "- {line}" under TONE header.
    # Example: ["Warm and reassuring — patients are often anxious", "Never diagnose"]
    tone_instructions: list[str] = field(default_factory=list)

    # Topics the AI is encouraged to engage with. Used as hints, not hard limits.
    allowed_topics: list[str] = field(default_factory=list)

    # Topics the AI should explicitly avoid or deflect.
    disallowed_topics: list[str] = field(default_factory=list)

    # Free-form compliance text block (healthcare privacy, legal disclaimers, etc).
    # Rendered verbatim after tone block. Leave empty when no compliance text needed.
    compliance_block: str = ""

    # Visitor patterns that should trigger HANDOFF_REQUESTED marker.
    # Example: ["medical emergency", "complaint about staff", "refund request"]
    escalation_triggers: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# IndustryPack — the full bundle
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class IndustryPack:
    """A turnkey workflow bundle for one vertical.

    `key` matches the business_profile key in
    `backend/services/business_profiles.py` so a tenant's business_type
    deterministically picks a pack.

    `version` bumps when the pack content changes — lets the seeder
    update-in-place rows tagged `source='industry_pack:{key}'` without
    destroying tenant customizations.
    """

    key: str
    label: str
    version: int = 1
    form_presets: list[FormPreset] = field(default_factory=list)
    sequence_templates: list[SequenceTemplate] = field(default_factory=list)
    smart_list_templates: list[SmartListTemplate] = field(default_factory=list)
    automation_rules: list[AutomationRuleTemplate] = field(default_factory=list)
    kb_seed_articles: list[KBSeedArticle] = field(default_factory=list)
    ai_persona: IndustryAIPersona | None = None

    @property
    def source_tag(self) -> str:
        """The `source` column value written by the seeder for every row."""
        return f"industry_pack:{self.key}"

    def summary(self) -> dict[str, int]:
        """Return counts per component — useful for dry-run responses."""
        return {
            "form_presets": len(self.form_presets),
            "sequence_templates": len(self.sequence_templates),
            "smart_list_templates": len(self.smart_list_templates),
            "automation_rules": len(self.automation_rules),
            "kb_seed_articles": len(self.kb_seed_articles),
        }


# ----------------------------------------------------------------------
# Seed result (returned by apply_pack_to_tenant)
# ----------------------------------------------------------------------


@dataclass
class SeedResult:
    """Summary of what was seeded into a tenant.

    `*_inserted` counts rows created this call. `*_skipped` counts rows
    that already existed (idempotent re-apply) — matched by source_tag +
    name.
    """

    pack_key: str
    pack_version: int
    forms_inserted: int = 0
    forms_skipped: int = 0
    sequences_inserted: int = 0
    sequences_skipped: int = 0
    smart_lists_inserted: int = 0
    smart_lists_skipped: int = 0
    automation_rules_inserted: int = 0
    automation_rules_skipped: int = 0
    kb_articles_inserted: int = 0
    kb_articles_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def total_inserted(self) -> int:
        return (
            self.forms_inserted
            + self.sequences_inserted
            + self.smart_lists_inserted
            + self.automation_rules_inserted
            + self.kb_articles_inserted
        )
