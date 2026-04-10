"""Restaurant industry pack.

Focus: reservations, catering inquiries, loyalty.
"""

from backend.services.industry_packs._shared import (
    make_appointment_reminder_sequence,
    make_csat_gate_rules,
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


RESTAURANT_PACK = IndustryPack(
    key="restaurant",
    label="Restaurant",
    version=1,
    form_presets=[
        FormPreset(
            key="restaurant_catering_inquiry",
            name="Catering & Event Inquiry",
            description="Collect event details for catering and private dining.",
            preset_key="catering_inquiry",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="reservation",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_reactivation_sequence(
            entity_noun="visit",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=3,
        ),
    ],
    smart_list_templates=[
        make_unresponded_leads_list(hours_since_inquiry=24),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=3),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="What are your hours?",
            body="Check our website or Google Business Profile for daily hours. We post holiday hours in advance.",
            tags=["hours", "faq"],
        ),
        KBSeedArticle(
            title="Do you take reservations?",
            body=(
                "Yes. You can book a table online 24/7. For parties of 8 or "
                "more, please call so we can accommodate you properly."
            ),
            tags=["reservations", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer catering?",
            body=(
                "Yes, we cater events from 10 to 500 people. Submit a catering "
                "inquiry with your date and guest count and we'll send a "
                "custom proposal within 24 hours."
            ),
            tags=["catering", "events", "faq"],
        ),
        KBSeedArticle(
            title="Do you have vegetarian / vegan / gluten-free options?",
            body=(
                "Yes, we have vegetarian, vegan, and gluten-free options on "
                "our menu, clearly marked. Let your server know about any "
                "allergies and we'll accommodate."
            ),
            tags=["dietary", "menu", "faq"],
        ),
        KBSeedArticle(
            title="Do you have a private dining room?",
            body=(
                "Yes. We have a private dining room that seats up to 40 "
                "guests. Perfect for birthdays, rehearsal dinners, and "
                "corporate events. Contact us for availability and pricing."
            ),
            tags=["private_dining", "events", "faq"],
        ),
    ],
)
