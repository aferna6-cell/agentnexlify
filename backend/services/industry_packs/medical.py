"""Medical practice industry pack.

Similar structure to the dental pack — same 6 problems, medically-generic
copy. Reuses the `medical_intake` form preset already in forms.py.
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
        "You help patients schedule visits, answer questions about services, "
        "insurance, and clinic logistics."
    ),
    tone_instructions=[
        "Professional and calm — patients may be worried",
        "Acknowledge concerns without minimizing",
        "Never diagnose, interpret symptoms, or recommend treatment",
    ],
    allowed_topics=["appointments", "clinic services", "insurance", "office hours", "new patient paperwork"],
    disallowed_topics=["diagnoses", "symptom interpretation", "medication dosage", "treatment plans"],
    compliance_block=(
        "HEALTHCARE PRIVACY:\n"
        "- If someone shares medical or health information, acknowledge it professionally\n"
        "- Do NOT store, repeat, or reference specific medical conditions in detail\n"
        "- If asked about privacy, say: 'Your information is kept confidential and handled in accordance with privacy regulations.'\n"
        "- Recommend patients complete a health history form before their visit\n"
        "- Never provide medical advice, diagnoses, or treatment recommendations\n"
        "- For any symptom question, respond: 'I can't evaluate symptoms — please call the clinic or seek medical care if urgent.'"
    ),
    escalation_triggers=[
        "medical emergency — direct to 911",
        "severe symptoms described",
        "billing dispute or insurance denial",
    ],
)


MEDICAL_PACK = IndustryPack(
    key="medical",
    label="Medical Practice",
    version=1,
    form_presets=[
        FormPreset(
            key="medical_new_patient_registration",
            name="New Patient Registration",
            description="Patient registration and medical history for new visits.",
            preset_key="medical_intake",
        ),
    ],
    sequence_templates=[
        make_welcome_sequence(business_label=_BUSINESS_LABEL),
        make_appointment_reminder_sequence(
            entity_noun="appointment",
            business_label=_BUSINESS_LABEL,
        ),
        make_post_appointment_review_sequence(
            entity_noun="visit",
            business_label=_BUSINESS_LABEL,
        ),
        make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
        make_reactivation_sequence(
            entity_noun="annual physical",
            business_label=_BUSINESS_LABEL,
            months_since_last_visit=12,
        ),
    ],
    smart_list_templates=[
        make_lapsed_clients_list(months_since_last_visit=12),
        make_overdue_invoices_list(min_days_overdue=3),
        make_unresponded_leads_list(hours_since_inquiry=24),
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
            title="What insurance do you accept?",
            body=(
                "We accept most major insurance carriers including Blue Cross, "
                "Aetna, Cigna, United, Humana, Kaiser, and Medicare. Call with "
                "your plan details and we'll verify coverage before your visit."
            ),
            tags=["insurance", "faq"],
        ),
        KBSeedArticle(
            title="How do I become a new patient?",
            body=(
                "Book a new patient visit online or by phone. You'll receive a "
                "registration form to complete before your appointment. Bring "
                "your insurance card, photo ID, and a list of current medications."
            ),
            tags=["new_patient", "faq"],
        ),
        KBSeedArticle(
            title="Do you offer telehealth visits?",
            body=(
                "Yes. Many visit types can be done via secure video call. "
                "Select 'Telehealth' when booking, or ask when you call. "
                "Most insurance plans cover telehealth the same as in-person."
            ),
            tags=["telehealth", "faq"],
        ),
        KBSeedArticle(
            title="What are your office hours?",
            body=(
                "Monday-Friday 8am-5pm. Same-day sick visits are usually "
                "available — call early in the day for best availability."
            ),
            tags=["hours", "faq"],
        ),
        KBSeedArticle(
            title="How do I get a prescription refill?",
            body=(
                "Call your pharmacy and ask them to send us a refill request, "
                "or use our patient portal. Please request refills at least "
                "48 hours before you run out."
            ),
            tags=["prescription", "refill", "faq"],
        ),
        KBSeedArticle(
            title="What should I bring to my first visit?",
            body=(
                "Photo ID, insurance card, list of current medications and "
                "doses, list of allergies, and any recent lab or imaging "
                "reports from other providers."
            ),
            tags=["new_patient", "intake", "faq"],
        ),
    ],
    ai_persona=_AI_PERSONA,
)
