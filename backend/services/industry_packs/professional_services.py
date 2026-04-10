"""Professional services (accounting, consulting, coaching) pack."""

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


PROFESSIONAL_SERVICES_PACK = IndustryPack(
    key="professional_services",
    label="Professional Services",
    version=1,
    form_presets=[
        FormPreset(
            key="pro_services_consultation",
            name="Book a Consultation",
            description="Collect project scope and contact info for new client consultations.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": True},
                {"id": "company", "type": "text", "label": "Company", "required": False},
                {"id": "service_needed", "type": "select", "label": "Service Needed", "required": True, "options": ["Tax prep", "Bookkeeping", "Business consulting", "Financial planning", "Other"]},
                {"id": "project_description", "type": "textarea", "label": "Briefly describe your needs", "required": True},
                {"id": "budget", "type": "select", "label": "Budget range", "required": False, "options": ["Under $500", "$500-$2,000", "$2,000-$10,000", "Over $10,000", "Unsure"]},
                {"id": "timeline", "type": "select", "label": "When do you need this done?", "required": False, "options": ["ASAP", "This month", "Next month", "Flexible"]},
            ],
            success_message="Thanks! We'll review and schedule your consultation within 1 business day.",
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
        make_overdue_invoices_list(min_days_overdue=7),
        make_unresponded_leads_list(hours_since_inquiry=8),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(days_overdue_trigger=7),
        make_overdue_invoice_rule(final_days=21),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="What services do you offer?",
            body=(
                "We offer tax preparation, bookkeeping, business consulting, "
                "and financial planning for individuals and small businesses. "
                "Check our services page for the full list."
            ),
            tags=["services", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer free consultations?",
            body=(
                "Yes — first consultation is free for new clients. Book online "
                "or call to schedule. We'll discuss your needs and outline "
                "how we can help."
            ),
            tags=["consultation", "faq"],
        ),
        KBSeedArticle(
            title="How do you charge for your services?",
            body=(
                "For tax prep and bookkeeping, we offer flat-fee packages. "
                "For consulting and advisory work, we bill hourly or on "
                "a project basis. Fees are discussed and agreed upfront."
            ),
            tags=["pricing", "faq"],
        ),
    ],
)
