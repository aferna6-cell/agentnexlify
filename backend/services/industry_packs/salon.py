"""Salon / spa industry pack.

Differences: short reactivation window (4-6wk rebook cycle), appointments
are 'services', no dunning (most salons take payment at time of service),
review collection is the big lever.
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


SALON_PACK = IndustryPack(
    key="salon",
    label="Salon / Spa",
    version=1,
    form_presets=[
        FormPreset(
            key="salon_new_client",
            name="New Client Intake",
            description="Collect preferences, allergies, and contact info from new salon clients.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": True},
                {"id": "dob", "type": "date", "label": "Birthday (for gifts!)", "required": False},
                {"id": "referred_by", "type": "text", "label": "Referred by", "required": False},
                {"id": "allergies", "type": "textarea", "label": "Allergies / sensitivities", "required": False},
                {"id": "stylist_prefs", "type": "textarea", "label": "Stylist preferences", "required": False, "placeholder": "e.g. natural look, bold color"},
                {"id": "consent", "type": "checkbox", "label": "I consent to services and acknowledge the cancellation policy", "required": True},
            ],
            success_message="Welcome! We can't wait to see you at your appointment.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="appointment",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="service",
            business_label=_BUSINESS_LABEL,
        ),
        make_reactivation_sequence(
            entity_noun="appointment",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=2,  # fast rebook cycle
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=2),
        make_unresponded_leads_list(hours_since_inquiry=24),
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=2),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="How much does a haircut cost?",
            body=(
                "Haircut pricing depends on the stylist level and length. "
                "Stylist cuts start at $45, senior stylists at $65, and master "
                "stylists at $85. Blowouts are $35. Check our full menu for "
                "details on color, highlights, and treatments."
            ),
            tags=["pricing", "haircut", "faq"],
        ),
        KBSeedArticle(
            title="Do you take walk-ins?",
            body=(
                "We take walk-ins when a chair is open, but booking ahead "
                "guarantees your time. You can book online 24/7 or text us."
            ),
            tags=["booking", "walk_in", "faq"],
        ),
        KBSeedArticle(
            title="What's your cancellation policy?",
            body=(
                "We ask for 24 hours notice to cancel or reschedule. Late "
                "cancellations or no-shows may be charged 50% of the service "
                "price. Thanks for understanding — our stylists rely on "
                "booked appointments."
            ),
            tags=["cancel", "policy", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer first-time client discounts?",
            body=(
                "Yes! New clients get 15% off their first service. Ask about "
                "our refer-a-friend program too — both of you get $15 off."
            ),
            tags=["new_client", "discount", "faq"],
        ),
        KBSeedArticle(
            title="Are your products vegan / cruelty-free?",
            body=(
                "Many of our products are vegan and cruelty-free. Ask your "
                "stylist for recommendations — we carry several lines and "
                "can match your values."
            ),
            tags=["products", "vegan", "faq"],
        ),
    ],
)
