"""Retail store industry pack.

Focus: order follow-up, loyalty, win-back after no recent purchase.
"""

from backend.services.industry_packs._shared import (
    make_csat_gate_rules,
    make_reactivation_sequence,
    make_reactivation_weekly_rule,
    make_unresponded_leads_list,
    make_welcome_sequence,
)
from backend.services.industry_packs.base import (
    FormPreset,
    IndustryPack,
    KBSeedArticle,
    SmartListTemplate,
)

_BUSINESS_LABEL = "{{business_name}}"


RETAIL_PACK = IndustryPack(
    key="retail",
    label="Retail",
    version=1,
    form_presets=[
        FormPreset(
            key="retail_customer_inquiry",
            name="Customer Inquiry",
            description="General customer inquiry for product or store questions.",
            fields=[
                {"id": "full_name", "type": "text", "label": "Name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": False},
                {"id": "inquiry_type", "type": "select", "label": "How can we help?", "required": True, "options": ["Product question", "Order status", "Return / exchange", "Store hours / location", "Other"]},
                {"id": "message", "type": "textarea", "label": "Your message", "required": True},
            ],
            success_message="Thanks — we'll get back to you within 1 business day.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="purchase",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=3,
        ),
    ],
    smart_list_templates=[
        SmartListTemplate(
            key="lapsed_customers",
            name="Lapsed Customers (3mo+)",
            description="Customers who haven't purchased in 3+ months.",
            entity="leads",
            filter={
                "last_purchase_date": {"lt": "now-90d"},
                "status": {"in": ["customer", "active"]},
            },
        ),
        make_unresponded_leads_list(hours_since_inquiry=24),
    ],
    automation_rules=[
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=3),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="What's your return policy?",
            body=(
                "Unworn items with tags can be returned within 30 days for a "
                "full refund. After 30 days, store credit only. Sale items "
                "are final sale unless defective."
            ),
            tags=["return", "policy", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer gift cards?",
            body="Yes, both physical and digital gift cards in any amount from $10 up. Never expire.",
            tags=["gift_card", "faq"],
        ),
        KBSeedArticle(
            title="Do you ship?",
            body=(
                "Yes, we ship anywhere in the US. Free shipping on orders over "
                "$75. Standard shipping 3-5 business days; expedited options "
                "available at checkout."
            ),
            tags=["shipping", "faq"],
        ),
        KBSeedArticle(
            title="What are your store hours?",
            body="Check our website or Google Business Profile for current hours. Holiday hours posted in advance.",
            tags=["hours", "faq"],
        ),
    ],
)
