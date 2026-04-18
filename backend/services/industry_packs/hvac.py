"""HVAC industry pack.

Differences from dental/medical: appointments are 'service visits' or 'jobs',
'lapsed' = 'needs seasonal tune-up' (6mo), intake is an estimate request
form (reuses contractor_estimate preset).
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
        "You help homeowners with HVAC repair, maintenance, replacement, and "
        "estimate requests while routing urgent comfort issues quickly."
    ),
    tone_instructions=[
        "Calm and helpful when the visitor has no heat or no cooling",
        "Capture system type, issue, urgency, ZIP code, and contact info",
        "Suggest booking a diagnostic or estimate when the visitor shows intent",
    ],
    allowed_topics=[
        "AC repair",
        "heating service",
        "maintenance plans",
        "replacement estimates",
        "financing",
        "service area",
        "emergency dispatch",
    ],
    disallowed_topics=[
        "guaranteed diagnosis from symptoms alone",
        "unsafe electrical, gas, or refrigerant repair instructions",
        "exact pricing without a diagnostic or estimate",
    ],
    escalation_triggers=[
        "gas smell, burning smell, electrical hazard, carbon monoxide concern",
        "no heat or no cooling during unsafe temperatures",
        "angry customer or warranty complaint",
    ],
)


HVAC_PACK = IndustryPack(
    key="hvac",
    label="HVAC Contractor",
    version=2,
    form_presets=[
        FormPreset(
            key="hvac_estimate_request",
            name="Request a Free HVAC Estimate",
            description="Collect repair, install, or maintenance estimate requests.",
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
            entity_noun="service visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="seasonal tune-up",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=6,
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=6),
        make_overdue_invoices_list(min_days_overdue=3),
        make_unresponded_leads_list(hours_since_inquiry=4),  # faster SLA
    ],
    automation_rules=[
        make_reminder_on_booking_rule(),
        make_post_appointment_review_trigger(),
        *make_csat_gate_rules(happy_threshold=4),
        make_dunning_trigger_rule(),
        make_overdue_invoice_rule(),
        make_reactivation_weekly_rule(months_since_last_visit=6),
    ],
    kb_seed_articles=[
        KBSeedArticle(
            title="How much does AC repair cost?",
            body=(
                "Most AC repairs run $150-$650 depending on the issue. "
                "Common fixes: capacitor replacement ($150-$300), refrigerant "
                "recharge ($200-$500), blower motor ($300-$600). We charge a "
                "diagnostic fee that's waived if you book the repair with us."
            ),
            tags=["pricing", "repair", "ac", "faq"],
        ),
        KBSeedArticle(
            title="How much does a new AC unit cost?",
            body=(
                "A new central AC install typically runs $4,500-$9,500 "
                "installed, depending on the tonnage, SEER rating, and "
                "brand. We offer free in-home estimates and financing from "
                "0% APR up to 60 months on qualified credit."
            ),
            tags=["pricing", "install", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer emergency service?",
            body=(
                "Yes — we offer 24/7 emergency service for no-heat and "
                "no-cool calls. Emergency dispatch fee is $150 after hours, "
                "waived if you book the repair."
            ),
            tags=["emergency", "hours", "faq"],
        ),
        KBSeedArticle(
            title="How often should I have my system serviced?",
            body=(
                "Twice a year — spring for the AC and fall for the furnace. "
                "Regular maintenance catches small problems before they "
                "become expensive failures and keeps your warranty valid. "
                "Our maintenance plan covers both visits for $199/year."
            ),
            tags=["maintenance", "tune_up", "faq"],
        ),
        KBSeedArticle(
            title="What areas do you serve?",
            body=(
                "We serve the metro area and surrounding counties. If you're "
                "outside our standard zone, we can still help for an additional "
                "travel fee — call or message us with your ZIP code and we'll "
                "confirm."
            ),
            tags=["service_area", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer financing?",
            body=(
                "Yes. We offer 0% APR financing for 12-60 months on qualified "
                "credit for installs over $2,500, and longer-term plans with "
                "low APR for bigger projects. Apply in about 2 minutes."
            ),
            tags=["financing", "faq"],
        ),
    ],
    ai_persona=_AI_PERSONA,
)
