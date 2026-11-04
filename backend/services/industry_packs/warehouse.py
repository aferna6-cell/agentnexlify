"""Warehouse and logistics industry pack.

Focus: storage quotes, freight booking, dock appointments, and shipment follow-up.
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
    IndustryAIPersona,
    IndustryPack,
    KBSeedArticle,
    SmartListTemplate,
)

_BUSINESS_LABEL = "{{business_name}}"


WAREHOUSE_PACK = IndustryPack(
    key="warehouse_logistics",
    label="Warehouse / Logistics",
    version=1,
    form_presets=[
        FormPreset(
            key="warehouse_quote_request",
            name="Freight & Storage Quote",
            description="Intake for a storage, fulfillment, or freight quote.",
            fields=[
                {"id": "company", "type": "text", "label": "Company", "required": True},
                {"id": "full_name", "type": "text", "label": "Contact name", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True},
                {"id": "phone", "type": "phone", "label": "Phone", "required": True},
                {
                    "id": "need",
                    "type": "select",
                    "label": "What do you need?",
                    "required": True,
                    "options": [
                        "Pallet storage",
                        "Fulfillment / pick and pack",
                        "Inbound receiving",
                        "Outbound freight",
                        "Cross-dock",
                    ],
                },
                {"id": "origin", "type": "text", "label": "Origin city", "required": False},
                {"id": "destination", "type": "text", "label": "Destination city", "required": False},
                {"id": "pallets", "type": "text", "label": "Pallet or carton count", "required": False},
                {"id": "needed_by", "type": "text", "label": "Needed by", "required": False},
            ],
            success_message="Thanks — a coordinator will reply with the next available dock time or a quote.",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="shipment",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=3,
        ),
    ],
    smart_list_templates=[
        SmartListTemplate(
            key="open_freight_quotes",
            name="Open freight quotes",
            description="Shippers who asked for a quote and have not booked.",
            entity="leads",
            filter={"status": {"in": ["new", "contacted", "qualified"]}},
        ),
        make_unresponded_leads_list(hours_since_inquiry=4),
    ],
    automation_rules=[
        *make_csat_gate_rules(happy_threshold=4),
        make_reactivation_weekly_rule(months_since_last_visit=3),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="What storage do you offer?",
            body=(
                "We store palletized freight, cartons, and short-term overflow. "
                "Tell us the pallet count, how long you need the space, and whether "
                "the goods are ambient or temperature-controlled, and we will quote storage plus handling."
            ),
            tags=["storage", "faq"],
        ),
        KBSeedArticle(
            title="How do dock appointments work?",
            body=(
                "Inbound and outbound loads need a dock appointment. Share the carrier, "
                "trailer type, pallet count, and requested window. We confirm a door "
                "time and the paperwork to bring: BOL, packing list, and PO numbers."
            ),
            tags=["dock", "receiving", "faq"],
        ),
        KBSeedArticle(
            title="How are freight rates quoted?",
            body=(
                "Rates depend on origin, destination, weight or pallet count, and service "
                "(LTL, FTL, or local cartage). We do not lock a rate in chat. Send the "
                "lane and timing and a coordinator will send a written quote."
            ),
            tags=["freight", "pricing", "faq"],
        ),
        KBSeedArticle(
            title="Can you pick, pack, and ship orders?",
            body=(
                "Yes. Fulfillment covers receiving your inventory, storing it, picking "
                "orders, and handing them to the carrier you choose. Share your order "
                "volume and carton sizes so we can confirm the handling fee."
            ),
            tags=["fulfillment", "faq"],
        ),
        KBSeedArticle(
            title="What if a shipment arrives damaged?",
            body=(
                "Note the damage on the delivery receipt before the driver leaves and "
                "send us photos plus the BOL or PRO number. We open a claim with the "
                "carrier and keep you updated. We do not decide claim payouts in chat."
            ),
            tags=["claims", "policy", "faq"],
        ),
    ],
    ai_persona=IndustryAIPersona(
        identity_addendum=(
            "You help shippers and receivers with storage, freight quotes, "
            "dock appointments, and shipment status for a warehouse and logistics company."
        ),
        tone_instructions=[
            "Ask for the lane, pallet or carton count, and the date the freight needs to move",
            "Never invent a tracking status, a door time, or a rate",
            "Collect the company name, contact, and a phone number before promising a callback",
        ],
        allowed_topics=[
            "pallet storage",
            "fulfillment",
            "dock appointments",
            "LTL and FTL freight",
            "receiving hours",
        ],
        disallowed_topics=[
            "guaranteed delivery times that were not provided",
            "customs brokerage legal advice",
            "invented claim settlements",
        ],
        escalation_triggers=[
            "damaged freight",
            "missing shipment",
            "OSHA incident",
            "billing dispute",
        ],
    ),
)
