"""Real estate (agent / brokerage) industry pack.

Focus: buyer and seller nurture sequences, showing reminders,
long-cycle reactivation.
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


REAL_ESTATE_PACK = IndustryPack(
    key="real_estate",
    label="Real Estate Agent / Brokerage",
    version=1,
    form_presets=[
        FormPreset(
            key="real_estate_buyer_seller",
            name="Buyer / Seller Inquiry",
            description="Collect buyer or seller inquiry details.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Full Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": True},
                {"id": "intent", "type": "select", "label": "Are you buying or selling?", "required": True, "options": ["Buying", "Selling", "Both", "Just looking"]},
                {"id": "timeline", "type": "select", "label": "Your timeline", "required": False, "options": ["ASAP", "1-3 months", "3-6 months", "6-12 months", "Over 1 year"]},
                {"id": "area", "type": "text", "label": "Target area / current location", "required": False},
                {"id": "budget", "type": "select", "label": "Price range (buying) or target list (selling)", "required": False, "options": ["Under $300K", "$300K-$500K", "$500K-$750K", "$750K-$1M", "Over $1M"]},
                {"id": "prequalified", "type": "radio", "label": "Pre-qualified for financing?", "required": False, "options": ["Yes", "No", "Not applicable"]},
                {"id": "notes", "type": "textarea", "label": "Anything else we should know?", "required": False},
            ],
            success_message="Thanks! We'll reach out within 1 business day to schedule a conversation.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="showing",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="showing",
            business_label=_BUSINESS_LABEL,
        ),
        make_reactivation_sequence(
            entity_noun="home search",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=6,
        ),
    ],
    smart_list_templates=[
        make_unresponded_leads_list(hours_since_inquiry=2),  # fast SLA
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=6),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="How do I get pre-qualified for a mortgage?",
            body=(
                "We work with trusted local lenders who can pre-qualify you "
                "in about 15 minutes. Pre-qualification shows sellers you're "
                "serious and tells you your real budget. Message us and "
                "we'll connect you."
            ),
            tags=["prequal", "financing", "buyer", "faq"],
        ),
        KBSeedArticle(
            title="What are your commission rates?",
            body=(
                "Commissions are negotiable and vary by market. For sellers, "
                "we'll discuss rates as part of your listing consultation. "
                "For buyers, our services are usually paid by the seller — "
                "free to you."
            ),
            tags=["commission", "pricing", "faq"],
        ),
        KBSeedArticle(
            title="How long does it take to sell a home?",
            body=(
                "In our current market, the average time from list to "
                "accepted offer is 21-35 days. Pricing and condition are "
                "the biggest factors. We'll give you a realistic estimate "
                "during your listing consultation."
            ),
            tags=["selling", "timeline", "faq"],
        ),
        KBSeedArticle(
            title="Do you handle out-of-state buyers?",
            body=(
                "Yes — we're experienced with remote buyers. We do video "
                "tours, send detailed neighborhood info, and can represent "
                "you through the entire closing process even if you can't "
                "visit in person."
            ),
            tags=["remote_buyer", "faq"],
        ),
    ],
)
