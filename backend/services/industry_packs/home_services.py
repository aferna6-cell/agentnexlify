"""Home services industry pack (plumbing, electrical, roofing, etc.).

Generalizes the HVAC pack for all trades using the shared contractor
estimate form.
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
    IndustryPack,
    KBSeedArticle,
)

_BUSINESS_LABEL = "{{business_name}}"


HOME_SERVICES_PACK = IndustryPack(
    key="home_services",
    label="Home Services (Plumbing, Electrical, Roofing, etc.)",
    version=1,
    form_presets=[
        FormPreset(
            key="home_services_estimate",
            name="Request a Free Estimate",
            description="Collect project details from homeowners.",
            preset_key="contractor_estimate",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="service visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="job",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="service",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=12,
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=12),
        make_overdue_invoices_list(min_days_overdue=3),
        make_unresponded_leads_list(hours_since_inquiry=4),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(),
        make_overdue_invoice_rule(),
        make_reactivation_weekly_rule(months_since_last_visit=12),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="Do you offer free estimates?",
            body=(
                "Yes, estimates are free and come with no obligation. Fill "
                "out the estimate form or call us — we can often quote basic "
                "jobs over the phone or schedule an in-person visit for "
                "larger projects."
            ),
            tags=["estimate", "pricing", "faq"],
        ),
        KBSeedArticle(
            title="Are you licensed and insured?",
            body=(
                "Yes — we're fully licensed, bonded, and insured. Our license "
                "number and insurance certificate are available on request. "
                "Never hire a contractor without verifying these."
            ),
            tags=["license", "insurance", "trust", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer a warranty on your work?",
            body=(
                "Yes. All labor is warranted for 1 year, and parts carry the "
                "manufacturer's warranty (typically 1-10 years depending on "
                "the product). We stand behind our work — if something's not "
                "right, let us know."
            ),
            tags=["warranty", "faq"],
        ),
        KBSeedArticle(
            title="What's your service area?",
            body=(
                "We serve the metro area and surrounding counties. Message "
                "us your ZIP code and we'll confirm we can help."
            ),
            tags=["service_area", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer emergency service?",
            body=(
                "Yes, for urgent issues like leaks, no-heat, or electrical "
                "hazards. Call our main line and select emergency — we'll "
                "dispatch the next available tech."
            ),
            tags=["emergency", "faq"],
        ),
    ],
)
