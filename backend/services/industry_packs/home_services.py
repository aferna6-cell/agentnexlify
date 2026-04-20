"""Contractors / Home Services industry pack.

General contractor, plumbing, roofing, electrical, landscaping, and
similar home-service trades share the same core workflow: capture the
estimate request, qualify the job, book the visit, and keep callbacks
moving until the work is scheduled.
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

_BUYER_POSITIONING = {
    "headline": "Turn estimate requests, callbacks, and repairs into booked jobs",
    "subheadline": (
        "Capture the right job details up front, respond quickly to urgent "
        "requests, and keep every estimate moving until it's scheduled."
    ),
    "value_props": [
        "Lead capture tuned for repairs, estimates, and service calls",
        "A widget greeting that asks the right follow-up question fast",
        "Reminder and review automations that fit contractor workflows",
    ],
}

_ONBOARDING_90_SECOND_FIELDS = [
    "Business name",
    "Primary trade or service type",
    "Service area / ZIP codes",
    "Main phone number",
    "Website URL",
    "Top 3 services",
    "Emergency service yes/no",
    "Business hours",
    "Preferred widget greeting",
]

_LEAD_FIELDS = [
    "Name",
    "Phone",
    "Email",
    "Service needed",
    "Property address",
    "Job type",
    "Timeline / urgency",
    "Budget range",
    "Photos or video link",
]

_DEMO_CONVERSATION_TRANSCRIPT = [
    ("Visitor", "Hi, I need an estimate for a bathroom remodel."),
    ("AI", "Absolutely. Is this for a repair, replacement, or full remodel?"),
    ("Visitor", "Full remodel. It's a 1970s house and we want new tile, vanity, and lighting."),
    ("AI", "Got it. What's the property address and when would you like someone to come take a look?"),
    ("Visitor", "123 Maple St. We're flexible, but this month would be great."),
    ("AI", "Perfect. I can book a site visit and note that you'd like a remodel estimate this month. Do you want phone, text, or email updates?"),
    ("Visitor", "Text is best."),
    ("AI", "Done. You're on the calendar and our team will follow up with the estimate details."),
]

_AI_PERSONA = IndustryAIPersona(
    identity_addendum=(
        "You qualify homeowners for repairs, estimates, and project calls, "
        "capture the job details the office needs, and help urgent requests "
        "get routed quickly."
    ),
    tone_instructions=[
        "Direct, practical, and calm",
        "Ask one clear follow-up at a time",
        "Prioritize urgency, service area, property type, timeline, budget, and contact info",
    ],
    allowed_topics=[
        "repairs",
        "estimates",
        "service requests",
        "emergency availability",
        "service area",
        "project photos",
        "project scope",
        "warranties",
        "licensing and insurance",
    ],
    disallowed_topics=[
        "guaranteed pricing without inspection",
        "unsafe DIY repair instructions",
        "promising exact arrival times without confirmed availability",
    ],
    escalation_triggers=[
        "active water leak, flooding, gas smell, electrical hazard, no heat or no cooling during extreme weather",
        "visitor is upset about an active job",
        "visitor asks for a manager or human dispatcher",
    ],
)

HOME_SERVICES_PACK = IndustryPack(
    key="home_services",
    label="Contractors / Home Services",
    version=3,
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
        make_unresponded_leads_list(hours_since_inquiry=2),
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
                "out the estimate form or call us - we can often quote basic "
                "jobs over the phone or schedule an in-person visit for "
                "larger projects."
            ),
            tags=["estimate", "pricing", "faq"],
        ),
        KBSeedArticle(
            title="Are you licensed and insured?",
            body=(
                "Yes - we're fully licensed, bonded, and insured. Our license "
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
                "the product). We stand behind our work - if something's not "
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
                "hazards. Call our main line and select emergency - we'll "
                "dispatch the next available tech."
            ),
            tags=["emergency", "faq"],
        ),
        KBSeedArticle(
            title="What should I send before the estimate?",
            body=(
                "A few photos, your address, a short description of the work, "
                "and your timeline help us quote faster and send the right "
                "person to the job."
            ),
            tags=["estimate", "photos", "faq"],
        ),
        KBSeedArticle(
            title="Do you require a deposit?",
            body=(
                "For larger projects, yes. We can explain the deposit amount, "
                "payment schedule, and what is due before work starts when we "
                "send your estimate."
            ),
            tags=["deposit", "payment", "faq"],
        ),
    ],
    ai_persona=_AI_PERSONA,
)

CONTRACTOR_VERTICAL_PACK = {
    "buyer_positioning": _BUYER_POSITIONING,
    "widget_greeting": (
        "Hi! Thanks for reaching out to {business_name}. Are you looking for a repair, "
        "an estimate, or help with an existing job?"
    ),
    "onboarding_90_second_fields": _ONBOARDING_90_SECOND_FIELDS,
    "lead_fields": _LEAD_FIELDS,
    "automation_presets": [
        "Welcome series for new leads",
        "Appointment reminder before site visits",
        "Post-job review request",
        "Invoice follow-up for overdue bills",
        "12-month reactivation for past customers",
    ],
    "faq_seed_set": [article.title for article in HOME_SERVICES_PACK.kb_seed_articles],
    "demo_conversation_transcript": _DEMO_CONVERSATION_TRANSCRIPT,
}
