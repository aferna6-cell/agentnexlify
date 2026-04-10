"""Default / fallback industry pack.

Used when a tenant's business_type is unknown or not in our 12 supported
verticals. Ships generic welcome + reminder + review sequences with
minimal intake form.
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


DEFAULT_PACK = IndustryPack(
    key="default",
    label="General Business",
    version=1,
    form_presets=[
        FormPreset(
            key="default_contact",
            name="Contact Us",
            description="Generic contact form for any business type.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": False},
                {"id": "message", "type": "textarea", "label": "How can we help?", "required": True},
            ],
            success_message="Thanks — we'll get back to you within 1 business day.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="appointment",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
    ],
    smart_list_templates=[
        make_overdue_invoices_list(min_days_overdue=3),
        make_unresponded_leads_list(hours_since_inquiry=24),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(),
        make_overdue_invoice_rule(),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="What are your hours?",
            body="Check our website or Google Business Profile for current hours.",
            tags=["hours", "faq"],
        ),
        KBSeedArticle(
            title="How can I contact you?",
            body=(
                "You can reach us by phone, email, or through the contact "
                "form on our website. We respond to all inquiries within "
                "1 business day."
            ),
            tags=["contact", "faq"],
        ),
        KBSeedArticle(
            title="Where are you located?",
            body="Our full address and directions are on our website under 'Contact' or 'Location'.",
            tags=["location", "faq"],
        ),
    ],
)
