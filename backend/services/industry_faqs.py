"""Industry FAQ seeding — runs once during tenant provisioning."""

import logging

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.business_profiles import resolve_business_profile_key

logger = logging.getLogger(__name__)


def _get_db():
    return _get_service_supabase()


INDUSTRY_FAQS: dict[str, list[dict]] = {
    "hvac": [
        {
            "question": "What HVAC services do you offer?",
            "answer": "We help with AC repair, heating service, tune-ups, indoor air quality, thermostat upgrades, system replacements, and emergency HVAC support.",
            "category": "Services",
        },
        {
            "question": "Do you offer emergency HVAC service?",
            "answer": "Yes, we handle urgent heating and cooling issues. Contact us with your issue and we'll respond as quickly as possible.",
            "category": "Services",
        },
        {
            "question": "Do you service both heating and air conditioning systems?",
            "answer": "Yes, we work on both heating and cooling equipment, including furnaces, heat pumps, central AC systems, and more.",
            "category": "Services",
        },
        {
            "question": "Do you provide estimates for new systems?",
            "answer": "Yes, we can provide an estimate for repairs, replacements, or a new HVAC system based on your needs and property.",
            "category": "Pricing",
        },
        {
            "question": "What areas do you serve?",
            "answer": "We serve the local area. Contact us to confirm we can service your location.",
            "category": "About",
        },
        {
            "question": "How often should I have my system serviced?",
            "answer": "We recommend a tune-up twice a year — cooling in spring, heating in fall. Regular maintenance keeps energy bills down, prevents mid-season breakdowns, and protects your manufacturer warranty.",
            "category": "Services",
        },
        {
            "question": "Do you offer maintenance plans?",
            "answer": "Yes, we offer maintenance plans that include seasonal tune-ups, priority scheduling, and discounts on repairs. Ask us for plan details and pricing.",
            "category": "Pricing",
        },
        {
            "question": "How long does a new system installation take?",
            "answer": "Most residential installations are completed in one day. Larger or more complex jobs can take longer — we'll give you a clear timeline with your estimate.",
            "category": "Services",
        },
    ],
    "plumbing": [
        {
            "question": "What services do you offer?",
            "answer": "We offer a full range of plumbing services including drain cleaning, water heater installation and repair, leak detection, pipe repair, sewer line services, faucet and fixture installation, and emergency plumbing.",
            "category": "Services",
        },
        {
            "question": "Do you offer emergency service?",
            "answer": "Yes, we offer emergency plumbing services. Contact us and we'll get back to you as quickly as possible.",
            "category": "Services",
        },
        {
            "question": "Are you licensed and insured?",
            "answer": "Yes, we are fully licensed and insured. We carry all required licenses and liability insurance for your protection.",
            "category": "About",
        },
        {
            "question": "What areas do you serve?",
            "answer": "We serve the local area. Contact us to confirm we can service your location.",
            "category": "About",
        },
        {
            "question": "Do you give free estimates?",
            "answer": "Yes, we provide free estimates for most plumbing jobs. Contact us to schedule an estimate.",
            "category": "Pricing",
        },
        {
            "question": "How much does a typical repair cost?",
            "answer": "It depends on the job, and we'd rather see it before quoting a number. Send us a photo and a short description and we'll give you an honest range — no surprise charges once work starts.",
            "category": "Pricing",
        },
        {
            "question": "Do you repair or replace water heaters?",
            "answer": "Yes, we repair and replace both tank and tankless water heaters. If yours is leaking, not heating, or over 10 years old, tell us the brand and roughly how old it is and we'll advise repair vs. replace.",
            "category": "Services",
        },
        {
            "question": "What should I do while I wait for the plumber?",
            "answer": "For active leaks, shut off the nearest fixture valve or your home's main water shut-off and avoid using the affected fixture. If you smell gas near a water heater, leave the house and call your gas utility first.",
            "category": "Services",
        },
    ],
    "home_services": [
        {
            "question": "What services do you offer?",
            "answer": "We help with repairs, replacements, installations, inspections, and estimate requests for your home or property. If you're not sure what category your project fits into, send us a quick message and we'll point you in the right direction.",
            "category": "Services",
        },
        {
            "question": "Do you provide free estimates?",
            "answer": "Yes, we offer free estimates for most projects. For larger jobs, we may schedule an in-person visit so we can give you the most accurate quote possible.",
            "category": "Pricing",
        },
        {
            "question": "Are you licensed and insured?",
            "answer": "Yes, we are licensed and insured. If you need license or insurance details for a permit, HOA, or property manager, we can provide them on request.",
            "category": "About",
        },
        {
            "question": "How soon can you get here?",
            "answer": "It depends on the job and our current schedule, but we always try to handle urgent repairs as quickly as possible. If it's an emergency, tell us what is happening and we'll do our best to prioritize it.",
            "category": "Services",
        },
        {
            "question": "What should I send before the estimate?",
            "answer": "Photos of the issue or project area, your address, a short description of the work, and your ideal timeline are the most helpful details. The more we know up front, the faster we can quote it.",
            "category": "Pricing",
        },
        {
            "question": "Do you stand behind your work?",
            "answer": "Yes. We want every customer to feel confident in the work we do, and we can explain warranty coverage for labor and parts before the job starts.",
            "category": "Policy",
        },
        {
            "question": "What payment methods do you accept?",
            "answer": "We accept all major payment methods. For larger projects we can discuss payment schedules tied to project milestones — ask when you get your estimate.",
            "category": "Pricing",
        },
        {
            "question": "Do I need to be home during the work?",
            "answer": "For most exterior work, no — we just need access to the work area. For interior work, we'll coordinate a time that works for you, and we always confirm before arriving.",
            "category": "Services",
        },
    ],
    "dental": [
        {
            "question": "What services do you offer?",
            "answer": "We offer comprehensive dental care including cleanings, exams, fillings, crowns, root canals, teeth whitening, Invisalign, dental implants, and emergency dental care.",
            "category": "Services",
        },
        {
            "question": "Do you accept dental insurance?",
            "answer": "Yes, we accept most major dental insurance plans. Contact us with your insurance information and we'll verify your coverage.",
            "category": "Insurance",
        },
        {
            "question": "Do you see new patients?",
            "answer": "Yes! We are always welcoming new patients. You can book an appointment through our chat or call us directly.",
            "category": "About",
        },
        {
            "question": "Do you offer emergency dental care?",
            "answer": "Yes, we offer same-day emergency appointments for dental emergencies like toothaches, broken teeth, or dental trauma.",
            "category": "Services",
        },
        {
            "question": "What is your cancellation policy?",
            "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations or no-shows may be subject to a fee.",
            "category": "Policy",
        },
        {
            "question": "Do you offer payment plans?",
            "answer": "Yes, we offer flexible payment plans for major procedures. We also accept CareCredit and other dental financing options.",
            "category": "Insurance",
        },
        {
            "question": "What should I bring to my first visit?",
            "answer": "Please bring your photo ID, insurance card, a list of current medications, and any dental records or X-rays from your previous dentist.",
            "category": "About",
        },
        {
            "question": "Do you offer cosmetic dentistry?",
            "answer": "Yes! We offer teeth whitening, veneers, bonding, Invisalign, and other cosmetic procedures to help you achieve your perfect smile.",
            "category": "Services",
        },
    ],
    "restaurant": [
        {
            "question": "What are your hours?",
            "answer": "Please check our business hours for the most up-to-date schedule. You can also ask us here!",
            "category": "Hours",
        },
        {
            "question": "Do you offer delivery?",
            "answer": "Please ask us about our current delivery options and delivery area.",
            "category": "Orders",
        },
        {
            "question": "Can I make a reservation?",
            "answer": "Yes! You can book a table through our chat widget or call us directly.",
            "category": "Reservations",
        },
        {
            "question": "Do you cater events?",
            "answer": "Yes, we offer catering services for events of all sizes. Contact us for a custom quote.",
            "category": "Catering",
        },
        {
            "question": "Do you accommodate dietary restrictions?",
            "answer": "Yes! We can accommodate vegetarian, vegan, gluten-free, and allergy-specific requests. Please let us know when ordering or making a reservation.",
            "category": "Dietary",
        },
        {
            "question": "Do you have a private dining room?",
            "answer": "Please ask us about our private dining and event space options. We'd love to host your special occasion.",
            "category": "Events",
        },
    ],
    "realestate": [
        {
            "question": "What areas do you cover?",
            "answer": "We serve the local real estate market. Contact us to discuss your specific area of interest.",
            "category": "Areas",
        },
        {
            "question": "Are you a buyer's or seller's agent?",
            "answer": "We work with both buyers and sellers. Whether you're looking to buy your dream home or sell your property, we can help.",
            "category": "Services",
        },
        {
            "question": "How do I schedule a showing?",
            "answer": "You can schedule a showing by chatting with us here, calling, or booking an appointment through our scheduling system.",
            "category": "Showings",
        },
        {
            "question": "Do I need to be pre-approved?",
            "answer": "Getting pre-approved for a mortgage before house hunting is highly recommended. It shows sellers you're a serious buyer and helps you understand your budget.",
            "category": "Buying",
        },
        {
            "question": "How long does it take to buy a house?",
            "answer": "The typical home buying process takes 30-60 days from accepted offer to closing. Finding the right home can take a few weeks to several months depending on the market.",
            "category": "Buying",
        },
        {
            "question": "What are your commission rates?",
            "answer": "Our commission structure is competitive and transparent. Contact us for details — we're happy to explain how our fees work.",
            "category": "Pricing",
        },
        {
            "question": "How do you market my property?",
            "answer": "We use professional photography, virtual tours, MLS listing, social media marketing, and targeted advertising to maximize your property's exposure.",
            "category": "Selling",
        },
        {
            "question": "What's my home worth?",
            "answer": "We offer free comparative market analyses (CMA) to help you understand your home's current value. Contact us to schedule yours.",
            "category": "Selling",
        },
    ],
    "legal": [
        {
            "question": "What areas of law do you practice?",
            "answer": "Contact us to learn about our practice areas and how we can help with your legal matter.",
            "category": "Services",
        },
        {
            "question": "Do you offer free consultations?",
            "answer": "Yes, we offer free initial consultations. Book an appointment to discuss your case.",
            "category": "Consultations",
        },
        {
            "question": "Are consultations confidential?",
            "answer": "We take your privacy seriously. Please note that this chat is for general inquiries and does not create an attorney-client relationship. Confidential matters should be discussed during a scheduled consultation with our attorney.",
            "category": "Privacy",
        },
        {
            "question": "What should I bring to my consultation?",
            "answer": "Please bring any relevant documents, contracts, court papers, or correspondence related to your matter. A timeline of events is also helpful.",
            "category": "Consultations",
        },
        {
            "question": "How are your fees structured?",
            "answer": "We offer various fee arrangements including hourly rates, flat fees, and contingency fees depending on the type of case. We'll discuss fees during your initial consultation.",
            "category": "Pricing",
        },
        {
            "question": "How long will my case take?",
            "answer": "Every case is different. During your consultation, we can give you a realistic timeline based on the specifics of your situation.",
            "category": "Process",
        },
    ],
    "salon": [
        {
            "question": "What services do you offer?",
            "answer": "We offer haircuts, coloring, styling, blowouts, treatments, and more. Contact us for our full service menu.",
            "category": "Services",
        },
        {
            "question": "How do I book an appointment?",
            "answer": "You can book an appointment right here in our chat, call us, or use our online booking system.",
            "category": "Booking",
        },
        {
            "question": "Do you accept walk-ins?",
            "answer": "We welcome walk-ins based on availability, but we recommend booking an appointment to guarantee your preferred time.",
            "category": "Booking",
        },
        {
            "question": "What is your cancellation policy?",
            "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations may be subject to a fee.",
            "category": "Policy",
        },
        {
            "question": "How much do haircuts cost?",
            "answer": "Our pricing varies by service and stylist. Contact us or check our service menu for current prices.",
            "category": "Pricing",
        },
        {
            "question": "Do you do bridal/event styling?",
            "answer": "Yes! We offer bridal hair, updos, and makeup services for weddings and special events. Book a consultation to discuss your look.",
            "category": "Services",
        },
    ],
    "auto_shop": [
        {
            "question": "What services do you offer?",
            "answer": "We offer oil changes, brake service, tire rotation, engine diagnostics, transmission repair, AC service, and more.",
            "category": "Services",
        },
        {
            "question": "Do you give free estimates?",
            "answer": "Yes, we provide free estimates for most repair work. Bring your vehicle in or describe the issue and we'll give you a quote.",
            "category": "Pricing",
        },
        {
            "question": "Do you work on all makes and models?",
            "answer": "Yes, our certified technicians work on all makes and models of cars, trucks, and SUVs.",
            "category": "Services",
        },
        {
            "question": "How long will my repair take?",
            "answer": "Repair times vary. Simple services like oil changes take 30-60 minutes. We'll give you an estimated completion time when you drop off your vehicle.",
            "category": "Process",
        },
        {
            "question": "Do you offer a warranty on repairs?",
            "answer": "Yes, our repairs come with a warranty on parts and labor. Ask us for specific warranty details.",
            "category": "Warranty",
        },
    ],
    "medical": [
        {
            "question": "Are you accepting new patients?",
            "answer": "Yes, we are currently accepting new patients. Book an appointment to get started.",
            "category": "About",
        },
        {
            "question": "What insurance do you accept?",
            "answer": "We accept most major insurance plans. Contact us with your insurance information to verify coverage.",
            "category": "Insurance",
        },
        {
            "question": "Do you offer telehealth appointments?",
            "answer": "Please ask us about our current telehealth options for virtual visits.",
            "category": "Services",
        },
        {
            "question": "What should I bring to my first visit?",
            "answer": "Please bring your photo ID, insurance card, list of current medications, and any relevant medical records.",
            "category": "About",
        },
        {
            "question": "What is your cancellation policy?",
            "answer": "We ask for at least 24 hours notice for cancellations. Late cancellations may be subject to a fee.",
            "category": "Policy",
        },
    ],
    "financial_services": [
        {
            "question": "How do I receive the trading alerts?",
            "answer": "Alerts are delivered the moment they trigger so you can act quickly. Ask us about delivery options (SMS, email) and we'll get you set up.",
            "category": "Service",
        },
        {
            "question": "Do you offer a free trial?",
            "answer": "Yes — try the full alert service free before committing. Ask us here and we'll get your trial started today.",
            "category": "Trial",
        },
        {
            "question": "Is this financial advice?",
            "answer": "No. Our alerts are for educational and informational purposes only and are not personalized financial advice. Trading involves risk, and past performance does not guarantee future results.",
            "category": "Disclaimer",
        },
        {
            "question": "What is your track record?",
            "answer": "We publish our documented alert history so you can review real results. Ask us and we'll point you to the latest performance log.",
            "category": "Performance",
        },
        {
            "question": "How do I cancel my subscription?",
            "answer": "You can cancel anytime — no lock-in. Message us here or use your account page and we'll take care of it right away.",
            "category": "Billing",
        },
    ],
    "fitness": [
        {
            "question": "What memberships do you offer?",
            "answer": "We offer a variety of membership options. Contact us to learn about our plans and pricing.",
            "category": "Memberships",
        },
        {
            "question": "Do you offer personal training?",
            "answer": "Yes! We have certified personal trainers available. Book a consultation to get started.",
            "category": "Services",
        },
        {
            "question": "Do you offer a free trial?",
            "answer": "Yes, we offer a free trial so you can experience our facility before committing. Ask us to get started!",
            "category": "Trial",
        },
        {
            "question": "What are your hours?",
            "answer": "Please check our business hours or ask us here. We're open early mornings through late evenings.",
            "category": "Hours",
        },
        {
            "question": "Do you offer group classes?",
            "answer": "Yes! We offer a variety of group fitness classes including yoga, spin, HIIT, and more. Ask about our class schedule.",
            "category": "Services",
        },
    ],
}


def seed_industry_faqs(
    tenant_id: str, industry: str, business_name: str, city: str
) -> None:
    """Insert starter FAQ entries for a new tenant based on their industry."""
    raw_industry = (industry or "").strip().lower()
    normalized = resolve_business_profile_key(industry)
    faq_key = {
        "home_services": "home_services",
        "contractor": "home_services",
        "contractors": "home_services",
        "general_contractor": "home_services",
        "plumbing": "plumbing",
        "hvac": "hvac",
        "real_estate": "realestate",
        # not in _BUSINESS_PROFILES, so resolve_business_profile_key would
        # collapse it to "default" — map it straight to its FAQ pack
        "financial_services": "financial_services",
        "trading": "financial_services",
        "trading_alerts": "financial_services",
    }.get(raw_industry, normalized)
    faqs = INDUSTRY_FAQS.get(faq_key, [])
    if not faqs:
        return
    db = _get_db()
    rows = []
    for faq in faqs:
        answer = faq["answer"]
        if city:
            answer = answer.replace("the local area", f"the {city} area")
            answer = answer.replace(
                "the local real estate market", f"the {city} real estate market"
            )
        rows.append(
            {
                "tenant_id": tenant_id,
                "question": faq["question"],
                "answer": answer,
                "category": faq.get("category", "General"),
            }
        )
    try:
        db.table("faq_entries").insert(rows).execute()
        logger.info(
            "Seeded %d industry FAQs for tenant %s (industry=%s)",
            len(rows),
            tenant_id,
            industry,
        )
    except Exception:
        logger.warning(
            "Failed to seed industry FAQs for tenant %s", tenant_id, exc_info=True
        )


_seed_industry_faqs = seed_industry_faqs
