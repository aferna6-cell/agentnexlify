"""Auto shop / mechanic industry pack.

Focus: service reminders (oil change every 3mo), estimate follow-ups,
dunning on unpaid invoices.
"""

from backend.services.industry_packs._shared import (
    make_appointment_reminder_sequence,
    make_csat_gate_rules,
    make_dunning_ladder_sequence,
    make_dunning_trigger_rule,
    make_lapsed_clients_list,
    make_overdue_invoice_rule,
    make_overdue_invoices_list,
    make_post_appointment_review_sequence,
    make_post_appointment_review_trigger,
    make_reactivation_sequence,
    make_reactivation_weekly_rule,
    make_reminder_on_booking_rule,
    make_unresponded_leads_list,
    make_welcome_sequence,
)
from backend.services.industry_packs.base import (
    FormPreset,
    IndustryAIPersona,
    IndustryPack,
    KBSeedArticle,
)

_BUSINESS_LABEL = "{{business_name}}"

_AI_PERSONA = IndustryAIPersona(
    identity_addendum=(
        "You help drivers describe vehicle issues, request quotes, and schedule "
        "service while collecting the details the shop needs."
    ),
    tone_instructions=[
        "Clear, practical, and reassuring",
        "Capture year, make, model, mileage, symptoms, urgency, and contact info",
        "Summarize the vehicle issue before asking the team to follow up",
    ],
    allowed_topics=[
        "repair estimates",
        "maintenance intervals",
        "diagnostics",
        "service appointments",
        "warranties",
        "loaner or shuttle options",
    ],
    disallowed_topics=[
        "guaranteed diagnosis without inspection",
        "unsafe driving advice",
        "promising exact repair prices before shop review",
    ],
    escalation_triggers=[
        "brake failure, engine smoke, fuel smell, unsafe-to-drive concern",
        "customer stranded or needs towing",
        "complaint about prior repair or invoice dispute",
    ],
)


AUTO_SHOP_PACK = IndustryPack(
    key="auto_shop",
    label="Auto Repair Shop",
    version=2,
    form_presets=[
        FormPreset(
            key="auto_repair_quote",
            name="Request a Repair Quote",
            description="Describe the issue and we'll quote the repair.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": True},
                {"id": "vehicle_year", "type": "number", "label": "Vehicle Year", "required": True},
                {"id": "vehicle_make", "type": "text", "label": "Make", "required": True},
                {"id": "vehicle_model", "type": "text", "label": "Model", "required": True},
                {"id": "mileage", "type": "number", "label": "Current Mileage", "required": False},
                {"id": "issue", "type": "textarea", "label": "What's the issue?", "required": True, "placeholder": "Describe symptoms, noises, warning lights, etc."},
                {"id": "urgency", "type": "select", "label": "How urgent?", "required": False, "options": ["Today", "This week", "Next week", "Flexible"]},
            ],
            success_message="Thanks! We'll review your request and send a quote within 24 hours.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="service visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="service",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="oil change",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=3,
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=3),
        make_overdue_invoices_list(min_days_overdue=3),
        make_unresponded_leads_list(hours_since_inquiry=8),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(),
        make_overdue_invoice_rule(),
        make_reactivation_weekly_rule(months_since_last_visit=3),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="How much does an oil change cost?",
            body=(
                "Basic conventional oil change: $40-$60. Synthetic blend: "
                "$55-$75. Full synthetic: $70-$100. Price includes new oil "
                "filter, oil top-off, multi-point inspection, and tire "
                "pressure check."
            ),
            tags=["pricing", "oil_change", "faq"],
        ),
        KBSeedArticle(
            title="Do you provide free estimates?",
            body=(
                "Yes. Diagnostic and written estimates are free. We'll never "
                "start work without your approval."
            ),
            tags=["estimate", "faq"],
        ),
        KBSeedArticle(
            title="Are your mechanics ASE certified?",
            body=(
                "Yes. All our technicians are ASE certified, and we carry "
                "AAA Approved Auto Repair accreditation. We stand behind our "
                "work with a 12-month / 12,000-mile warranty."
            ),
            tags=["certification", "warranty", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer loaner cars?",
            body=(
                "We offer shuttle service within the metro area for free and "
                "loaner cars for extended repairs (availability depends on "
                "the day). Just ask when you book."
            ),
            tags=["loaner", "shuttle", "faq"],
        ),
        KBSeedArticle(
            title="How often should I get an oil change?",
            body=(
                "Modern cars with synthetic oil: every 5,000-7,500 miles or "
                "6 months, whichever comes first. Conventional oil: every "
                "3,000 miles or 3 months. Check your owner's manual for your "
                "specific vehicle."
            ),
            tags=["maintenance", "oil_change", "faq"],
        ),
    ],
    ai_persona=_AI_PERSONA,
)
