"""Legal / law firm industry pack.

Reuses legal_intake form preset. Sequences focus on consultation booking,
retainer dunning, and matter follow-up.
"""

from backend.services.industry_packs._shared import (
    make_appointment_reminder_sequence,
    make_csat_gate_rules,
    make_dunning_ladder_sequence,
    make_dunning_trigger_rule,
    make_overdue_invoice_rule,
    make_overdue_invoices_list,
    make_post_appointment_review_sequence,
    make_post_appointment_review_trigger,
    make_reminder_on_booking_rule,
    make_unresponded_leads_list,
    make_welcome_sequence,
)
from backend.services.industry_packs.base import (
    FormPreset,
    IndustryPack,
    KBSeedArticle,
)

_BUSINESS_LABEL = "{{business_name}}"


LEGAL_PACK = IndustryPack(
    key="legal",
    label="Law Firm",
    version=1,
    form_presets=[
        FormPreset(
            key="legal_new_matter_intake",
            name="New Client Intake",
            description="Collect case details and contact info for potential new matters.",
            preset_key="legal_intake",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="consultation",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="consultation",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
    ],
    smart_list_templates=[
        make_overdue_invoices_list(min_days_overdue=7),  # slower for legal
        make_unresponded_leads_list(hours_since_inquiry=4),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(days_overdue_trigger=7),
        make_overdue_invoice_rule(final_days=30),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="Do you offer free consultations?",
            body=(
                "Yes. Initial consultations are free and confidential for most "
                "matter types. Book online or call — we'll take 30 minutes to "
                "understand your situation and outline your options."
            ),
            tags=["consultation", "faq"],
        ),
        KBSeedArticle(
            title="What are your fees?",
            body=(
                "Fees depend on the matter type. We offer flat-fee packages "
                "for many common matters (estate planning, simple contracts, "
                "LLC formation), contingency for personal injury, and hourly "
                "for litigation. Full transparency on your engagement letter."
            ),
            tags=["fees", "pricing", "faq"],
        ),
        KBSeedArticle(
            title="Is my information confidential?",
            body=(
                "Yes. All communication with our firm is protected by "
                "attorney-client privilege from your first contact, whether "
                "or not you ultimately retain us."
            ),
            tags=["confidentiality", "trust", "faq"],
        ),
        KBSeedArticle(
            title="What areas of law do you practice?",
            body=(
                "Our practice areas are listed on our website. If your matter "
                "falls outside our practice areas, we'll refer you to a "
                "trusted colleague who handles that area."
            ),
            tags=["practice_areas", "faq"],
        ),
    ],
)
