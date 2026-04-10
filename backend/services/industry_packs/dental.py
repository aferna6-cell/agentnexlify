"""Dental office industry pack — the reference implementation.

Covers all 6 classic dental-office problems:

    1. Patients not booking → booking form + widget already handle.
    2. No one answering at night → widget_chat + KB seed FAQs.
    3. Unpaid bills → dunning ladder sequence + trigger rule + escalation.
    4. Bad reviews → post-appt CSAT + happy/unhappy gate rules.
    5. Lapsed patients → 6mo+ smart list + reactivation sequence + weekly cron rule.
    6. Manual intake → new patient intake form preset (reuses forms.py _FORM_PRESETS).

A dental office seeded with this pack should be able to run its front desk
on autopilot for bookings, reminders, follow-ups, and billing.
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

_ENTITY_NOUN = "appointment"
_BUSINESS_LABEL = "{{business_name}}"


_FORM_PRESETS = [
    FormPreset(
        key="dental_new_patient_intake",
        name="New Patient Health History",
        description=(
            "Collect essential health information, insurance, and consent "
            "from new dental patients before their first visit."
        ),
        # Reuses the dental_intake preset already shipped in
        # backend/routers/forms.py:_FORM_PRESETS — no duplicated field list.
        preset_key="dental_intake",
    ),
]


_SEQUENCES = [
    make_welcome_sequence(business_label=_BUSINESS_LABEL),
    make_appointment_reminder_sequence(
        entity_noun=_ENTITY_NOUN,
        business_label=_BUSINESS_LABEL,
    ),
    make_post_appointment_review_sequence(
        entity_noun="visit",
        business_label=_BUSINESS_LABEL,
    ),
    make_dunning_ladder_sequence(business_label=_BUSINESS_LABEL),
    make_reactivation_sequence(
        entity_noun="cleaning",
        business_label=_BUSINESS_LABEL,
        months_since_last_visit=6,
    ),
]


_SMART_LISTS = [
    make_lapsed_clients_list(months_since_last_visit=6),
    make_overdue_invoices_list(min_days_overdue=3),
    make_unresponded_leads_list(hours_since_inquiry=24),
]


_AUTOMATION_RULES = [
    make_reminder_on_booking_rule(),
    make_post_appointment_review_trigger(),
    *make_csat_gate_rules(happy_threshold=4),
    make_dunning_trigger_rule(),
    make_overdue_invoice_rule(),
    make_reactivation_weekly_rule(months_since_last_visit=6),
]


# Top 15 dental FAQs — seeded into the tenant KB so widget_chat can answer
# them at 3am without a receptionist. Keep bodies short and scannable; the
# widget_chat prompt truncates at ~3500 chars.
_KB_ARTICLES = [
    KBSeedArticle(
        title="Do you accept Delta Dental?",
        body=(
            "Yes — we accept Delta Dental PPO and Premier plans. We also accept "
            "Cigna, MetLife, Aetna, Guardian, United Concordia, and most other "
            "major insurance carriers. If you don't see your insurance listed, "
            "call us and we'll check. We file claims on your behalf."
        ),
        tags=["insurance", "faq", "dental"],
    ),
    KBSeedArticle(
        title="How much does a cleaning cost?",
        body=(
            "A routine cleaning (prophylaxis) is typically covered at 100% by "
            "most dental insurance plans twice a year. Without insurance, the "
            "cash price is usually around $120-$180 depending on X-rays and "
            "exam. New patient exams with X-rays and cleaning usually range "
            "$200-$350 without insurance."
        ),
        tags=["pricing", "faq", "cleaning"],
    ),
    KBSeedArticle(
        title="How much does a crown cost?",
        body=(
            "Crown cost depends on the material (porcelain, ceramic, zirconia, "
            "gold) and your insurance coverage. Out-of-pocket, crowns typically "
            "range $800-$1,500 per tooth. Most dental insurance covers 50% of "
            "the crown cost after your deductible is met. We offer payment "
            "plans if needed."
        ),
        tags=["pricing", "faq", "crown"],
    ),
    KBSeedArticle(
        title="Do you offer payment plans?",
        body=(
            "Yes. We partner with CareCredit to offer 0% interest payment plans "
            "on treatment over $500. We also accept all major credit cards, "
            "HSA/FSA cards, and cash. For larger treatment plans, we can split "
            "payments into phases."
        ),
        tags=["payment", "financing", "faq"],
    ),
    KBSeedArticle(
        title="What are your office hours?",
        body=(
            "Our standard hours are Monday-Thursday 8am-5pm and Friday 8am-2pm. "
            "We offer early morning and evening appointments by request. "
            "Emergency appointments are available same-day — call the main line "
            "and we'll fit you in."
        ),
        tags=["hours", "faq"],
    ),
    KBSeedArticle(
        title="How do I become a new patient?",
        body=(
            "Easy — just book a new patient exam online or call us. We'll send "
            "you a digital intake form to fill out before your visit so we can "
            "get started right away. Please bring your insurance card and a "
            "list of any current medications. Your first visit usually takes "
            "60-90 minutes and includes X-rays, exam, and cleaning."
        ),
        tags=["new_patient", "intake", "faq"],
    ),
    KBSeedArticle(
        title="I have a dental emergency — what should I do?",
        body=(
            "For severe pain, knocked-out teeth, broken teeth, or bleeding that "
            "won't stop: call us immediately. We reserve same-day emergency "
            "slots. For a knocked-out tooth, rinse gently, place it back in "
            "the socket if possible, or store it in milk — and come in within "
            "1 hour for the best chance of saving it."
        ),
        tags=["emergency", "faq"],
    ),
    KBSeedArticle(
        title="Do you do teeth whitening?",
        body=(
            "Yes. We offer in-office professional whitening (about 1 hour, "
            "instant results, ~$400-$600) and take-home custom tray kits "
            "(~$250-$400, 2 weeks of nightly wear). In-office whitening lifts "
            "teeth 4-8 shades in a single visit."
        ),
        tags=["whitening", "cosmetic", "faq"],
    ),
    KBSeedArticle(
        title="Do you offer braces or Invisalign?",
        body=(
            "Yes. We offer Invisalign clear aligners for most cases. Traditional "
            "braces are available for complex orthodontic needs — we refer to "
            "our trusted orthodontist partner for those. Invisalign treatment "
            "typically costs $3,500-$6,500 depending on complexity. Free "
            "consultations are available."
        ),
        tags=["orthodontics", "invisalign", "faq"],
    ),
    KBSeedArticle(
        title="Do you accept walk-ins?",
        body=(
            "We see patients by appointment whenever possible so we can plan "
            "your visit properly. That said, we always try to fit in same-day "
            "emergencies. If you're in pain, call the main line and we'll do "
            "our best to see you today."
        ),
        tags=["walk_in", "scheduling", "faq"],
    ),
    KBSeedArticle(
        title="How often should I come in for a cleaning?",
        body=(
            "Most patients should come in every 6 months for a cleaning and "
            "exam. Some patients with gum disease or other risk factors benefit "
            "from 3-4 month cleanings. Your hygienist will recommend the right "
            "interval based on your dental health."
        ),
        tags=["cleaning", "recall", "faq"],
    ),
    KBSeedArticle(
        title="Do you treat children?",
        body=(
            "Yes — we see patients of all ages. The American Academy of Pediatric "
            "Dentistry recommends a child's first dental visit by age 1 or within "
            "6 months of the first tooth. We keep kids' visits short, friendly, "
            "and educational."
        ),
        tags=["pediatric", "family", "faq"],
    ),
    KBSeedArticle(
        title="Do you offer sedation dentistry?",
        body=(
            "Yes. We offer nitrous oxide (laughing gas) for mild anxiety, oral "
            "sedation pills for moderate anxiety, and IV sedation for severe "
            "anxiety or long procedures. All sedation options require an "
            "in-person consultation first."
        ),
        tags=["sedation", "anxiety", "faq"],
    ),
    KBSeedArticle(
        title="How do I cancel or reschedule my appointment?",
        body=(
            "Reply to your confirmation text or email, or call our main line. "
            "We appreciate 48 hours notice so we can offer your slot to another "
            "patient. Late cancellations (under 24h) may incur a $50 fee. "
            "Reschedules are free anytime."
        ),
        tags=["cancel", "reschedule", "policy", "faq"],
    ),
    KBSeedArticle(
        title="Where are you located and do you have parking?",
        body=(
            "You can find our full address, directions, and parking info on "
            "our website under 'Contact'. We have free patient parking directly "
            "in front of the building. We're wheelchair accessible."
        ),
        tags=["location", "parking", "faq"],
    ),
]


DENTAL_PACK = IndustryPack(
    key="dental",
    label="Dental Office",
    version=1,
    form_presets=_FORM_PRESETS,
    sequence_templates=_SEQUENCES,
    smart_list_templates=_SMART_LISTS,
    automation_rules=_AUTOMATION_RULES,
    kb_seed_articles=_KB_ARTICLES,
)
