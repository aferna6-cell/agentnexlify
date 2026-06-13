"""Per-vertical qualification rubrics for the AI lead qualifier.

The shared `lead_qualifier` Managed Agent (config/managed_agents.yaml) scores
every lead on the same intent/fit axes, but what counts as a *good* lead differs
by trade: an HVAC "no heat today" is a hot call, while the same urgency words in
a law-firm intake might be a fee-shopper. These rubrics inject vertical context
into the qualification prompt so the model weights the right signals.

Keyed by the same canonical industry-pack keys as
`backend/services/business_profiles.py`. Resolution goes through
`resolve_business_profile_key` so free-text `business_type` values
("plumbing", "cafe", "barber") map to the right rubric. Unknown types fall
back to the generic `default` rubric.
"""

from backend.services.business_profiles import resolve_business_profile_key

# One short paragraph per canonical vertical. Each names the strongest
# buying signals (push intent up), the fit cues (push fit up), and the
# spam/disqualify tells for that trade. Kept terse — this is appended to a
# latency-sensitive prompt.
_RUBRICS: dict[str, str] = {
    "default": (
        "Weight a clear, specific request, a real contact method, and a "
        "near-term timeline as high intent. Treat vague one-liners, free-tool "
        "seekers, and obvious bot/spam submissions as low intent or "
        "disqualify_spam."
    ),
    "hvac": (
        "High intent: no-heat / no-cool / water-leak emergencies, named "
        "equipment problems, install or replacement quotes, and same-week "
        "service windows. High fit: homeowner or property manager inside the "
        "service area. Low intent: parts-only price shoppers and warranty "
        "questions for systems installed elsewhere. Disqualify generic "
        "marketing or SEO solicitations."
    ),
    "home_services": (
        "High intent: a defined job (repair, install, remodel), a property "
        "address or photos, a budget range, and a start-date expectation. High "
        "fit: jobs that match the trades the business actually offers. Low "
        "intent: 'just curious what it costs' with no timeline. Disqualify "
        "subcontractor pitches and supplier cold outreach."
    ),
    "real_estate": (
        "High intent: buyers with financing in motion (pre-approval, cash), "
        "sellers naming a target list date, and specific showing requests. "
        "High fit: price band and area match the agent's market. Low intent: "
        "early browsers 'just looking,' rate-only questions. Disqualify "
        "wholesaler blasts and recruiting messages."
    ),
    "dental": (
        "High intent: new-patient bookings, emergencies (pain, broken tooth), "
        "and treatment the practice offers (implants, ortho, cleanings). High "
        "fit: in insurance network or willing to self-pay, in driving range. "
        "Low intent: insurance-coverage trivia with no booking intent. "
        "Disqualify supplier and staffing solicitations."
    ),
    "medical": (
        "High intent: appointment requests, new-patient onboarding, and "
        "specific care needs the clinic provides. High fit: accepted insurance "
        "or self-pay, within service area. Low intent: general health "
        "questions with no booking. Disqualify spam and vendor outreach. Never "
        "infer or record diagnoses — score on intent to book, not symptoms."
    ),
    "salon": (
        "High intent: booking a specific service, asking same-week "
        "availability, and pricing for a service the salon offers. High fit: "
        "local clients and repeat-visit potential. Low intent: one-off "
        "discount hunters. Disqualify product-line and booth-rental pitches."
    ),
    "restaurant": (
        "High intent: reservations with a date and party size, catering and "
        "private-event inquiries with head counts, and large-order requests. "
        "High fit: events that fit the venue's capacity and cuisine. Low "
        "intent: menu trivia with no booking. Disqualify delivery-app and "
        "supplier solicitations."
    ),
    "legal": (
        "High intent: a described legal matter in the firm's practice area, a "
        "deadline or court date, and willingness to schedule a consultation. "
        "High fit: matter type and jurisdiction the firm handles. Low intent: "
        "free-advice seekers and fee-only shoppers. Disqualify lead-broker and "
        "marketing outreach. Flag potential conflicts in reasoning, do not "
        "give legal advice."
    ),
    "professional_services": (
        "High intent: a scoped engagement, a budget signal, and a start "
        "timeline. High fit: the service line and company size the firm "
        "serves. Low intent: 'pick your brain' requests with no budget. "
        "Disqualify agency and outsourcing cold pitches."
    ),
    "auto_shop": (
        "High intent: a named vehicle problem, a drivability or safety issue, "
        "a repair or maintenance quote, and a near-term drop-off. High fit: "
        "vehicle make/age the shop services, local owner. Low intent: "
        "part-price-only questions. Disqualify parts-vendor and warranty "
        "telemarketing."
    ),
    "fitness": (
        "High intent: trial or membership sign-ups, intro-session bookings, "
        "and questions about specific programs (PT, classes). High fit: local "
        "prospects with a stated goal. Low intent: free-pass-only hunters. "
        "Disqualify supplement and franchise-sales outreach."
    ),
    "retail": (
        "High intent: product availability and reservation requests, bulk or "
        "wholesale orders, and order or return follow-ups from real customers. "
        "High fit: in-stock categories and serviceable location. Low intent: "
        "generic browsing with no question. Disqualify supplier and "
        "drop-ship pitches."
    ),
}


def get_qualification_rubric(business_type: str | None) -> str:
    """Return the vertical qualification rubric for a tenant's business type.

    Resolves free-text ``business_type`` to a canonical industry-pack key the
    same way the widget defaults and dashboard presets do, then returns the
    matching rubric. Always returns a non-empty string (falls back to the
    generic ``default`` rubric for unknown types).
    """
    key = resolve_business_profile_key(business_type)
    return _RUBRICS.get(key, _RUBRICS["default"])
