"""Gym / fitness industry pack.

Focus: trial conversion, membership renewal, no-show follow-up.
"""

from backend.services.industry_packs._shared import (
    make_appointment_reminder_sequence,
    make_csat_gate_rules,
    make_lapsed_clients_list,
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


FITNESS_PACK = IndustryPack(
    key="fitness",
    label="Gym / Fitness Studio",
    version=1,
    form_presets=[
        FormPreset(
            key="fitness_waiver_intake",
            name="Fitness Liability Waiver",
            description="Waiver and health screening for new members.",
            preset_key="fitness_waiver",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="training session",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="session",
            business_label=_BUSINESS_LABEL,
        ),
        make_reactivation_sequence(
            entity_noun="workout",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=1,  # fast churn
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=1),
        make_unresponded_leads_list(hours_since_inquiry=24),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=1),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="Do you offer a free trial?",
            body=(
                "Yes — we offer a 7-day free trial for new members. Book your "
                "first session online and come meet the team. No credit card "
                "required upfront."
            ),
            tags=["trial", "new_member", "faq"],
        ),
        KBSeedArticle(
            title="What does membership cost?",
            body=(
                "Membership starts at $49/month for unlimited access. We also "
                "offer personal training packages and class-pack options. "
                "Student and military discounts available."
            ),
            tags=["pricing", "membership", "faq"],
        ),
        KBSeedArticle(
            title="What are your class schedules?",
            body=(
                "Check our class schedule online or in the member app for "
                "real-time availability. We run group classes throughout the "
                "day, with morning, lunch, and evening options."
            ),
            tags=["classes", "schedule", "faq"],
        ),
        KBSeedArticle(
            title="Can I freeze my membership?",
            body=(
                "Yes. Members can freeze their membership for up to 3 months "
                "per year (travel, injury, etc.). Just send us a message."
            ),
            tags=["freeze", "membership", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer personal training?",
            body=(
                "Yes. We offer 1:1 personal training and small-group "
                "training. Book a free 30-minute intro session online to "
                "meet a trainer and design your plan."
            ),
            tags=["personal_training", "faq"],
        ),
    ],
)
