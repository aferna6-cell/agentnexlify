"""Demo tenant seeding service for the public live-demo sandbox.

Exposes these public functions:

    ensure_demo_tenants(db) -> dict[str, str]
        Ensure all three demo verticals exist.  Creates any missing ones.
        Returns {vertical: tenant_id, ...}.  Idempotent.  Never raises.

    get_demo_tenant(db, vertical) -> str | None
        Return the tenant_id for the given vertical, or None if not found.
        vertical must be one of "plumbing", "salon", "financial_services".

    ensure_demo_tenant(db) -> str | None
        Back-compat wrapper — returns the plumbing demo tenant_id.
        All legacy callers (demo_reset_job, seed script, tests) continue to
        work unchanged.  The wrapper never raises.

    reset_demo_tenant(db, tenant_id) -> dict
        Delete volatile rows for a demo tenant and re-seed them.
        Hard-asserts is_demo=True before deleting anything.

PRODUCTION-URL guard: intentionally absent from this service.
The service is designed to run in production for the live-demo sandbox.
It may only operate on tenants whose is_demo flag is True.

NOTE: the script at scripts/demos/seed_plumbing_demo.py retains its own
production-URL guard for local manual seeding — that asymmetry is
intentional. The service has no such guard because the whole point is
running in prod for the live demo; safety comes from the is_demo flag check.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.tenant_scope import tenant_scope_column, tenant_table

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# AI token caps — same for all verticals (conservative for public sandbox)
_AI_TOKEN_ALERT = 150_000
_AI_TOKEN_HARD = 400_000

# Fake 555 phone numbers (safe for demo)
_MISSED_CALL_CALLER_PLUMBING = "+15551234567"
_MISSED_CALL_CALLER_SALON = "+15559876543"
_MISSED_CALL_CALLER_FINANCIAL = "+15554561234"

# ---------------------------------------------------------------------------
# Plumbing vertical constants (unchanged from original)
# ---------------------------------------------------------------------------

_PLUMBING_OWNER_EMAIL = "demo-plumbing@agentnexlify-demo.local"
_PLUMBING_BUSINESS_NAME = "Reliable Plumbing Co. (DEMO)"
_PLUMBING_PHONE = "555-321-7700"
_PLUMBING_CITY = "Riverside"

_PLUMBING_GREETING = (
    "Hi! I'm Pat, the virtual assistant for Reliable Plumbing Co. "
    "I can answer questions about our services, pricing, and availability — "
    "or help you get a free estimate. Got a leak, clogged drain, or water "
    "heater issue? Tell me what's going on and I'll help you right away."
)

_PLUMBING_HOURS = {
    "monday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "tuesday":   {"enabled": True,  "start": "07:00", "end": "18:00"},
    "wednesday": {"enabled": True,  "start": "07:00", "end": "18:00"},
    "thursday":  {"enabled": True,  "start": "07:00", "end": "18:00"},
    "friday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "saturday":  {"enabled": True,  "start": "08:00", "end": "16:00"},
    "sunday":    {"enabled": False, "start": "09:00", "end": "17:00"},
}

_PLUMBING_FAQ_ENTRIES = [
    {
        "question": "Do you handle plumbing emergencies?",
        "answer": (
            "Yes — burst pipes, major leaks, and sewer backups are our top priority. "
            "Contact us immediately and we will dispatch a plumber as fast as possible. "
            "While you wait, locate your main water shut-off valve and turn it off to "
            "limit damage."
        ),
        "category": "Emergency",
    },
    {
        "question": "How much does it cost to fix a leaking pipe?",
        "answer": (
            "Repair cost depends on where the leak is, how accessible the pipe is, and "
            "the extent of the damage. Minor compression or fitting repairs start around "
            "$150–$300. Pipe section replacements in walls or under slabs vary widely. "
            "We provide a free estimate before any work begins — no surprise charges."
        ),
        "category": "Pricing",
    },
    {
        "question": "Should I repair or replace my water heater?",
        "answer": (
            "If your water heater is under 8 years old and the issue is a faulty element, "
            "thermostat, or pressure valve, repair usually makes sense. If it is over "
            "10 years old, leaking from the tank, or leaving rust-colored water, "
            "replacement is almost always more cost-effective. Tell us the brand, model, "
            "and age and we can advise you quickly."
        ),
        "category": "Water Heater",
    },
    {
        "question": "How do I know if I have a hidden leak?",
        "answer": (
            "Warning signs include an unexpected spike in your water bill, the sound of "
            "running water with all fixtures off, wet spots on walls or ceilings, mold "
            "or musty odors, and low water pressure throughout the house. We use "
            "non-invasive leak detection equipment to locate leaks without unnecessary "
            "demolition."
        ),
        "category": "Leak Detection",
    },
    {
        "question": "What causes slow or clogged drains?",
        "answer": (
            "Hair, soap scum, and grease are the most common culprits in bathroom and "
            "kitchen drains. Older homes can have root intrusion, scale buildup, or "
            "partial pipe collapse deeper in the line. We offer hydro-jetting for "
            "severe blockages and camera inspection to find the exact cause."
        ),
        "category": "Drain Cleaning",
    },
    {
        "question": "How long does a drain cleaning service take?",
        "answer": (
            "A standard snake or auger service for a single drain typically takes "
            "30–60 minutes. Hydro-jetting a main sewer line takes 1–2 hours. "
            "Camera inspections add about 30 minutes. We will give you a time window "
            "when we schedule your appointment."
        ),
        "category": "Drain Cleaning",
    },
    {
        "question": "Do you install tankless water heaters?",
        "answer": (
            "Yes. We install, service, and flush both tank and tankless water heaters "
            "from all major brands. Tankless units require a gas line or electrical "
            "upgrade in many homes — we assess that during the estimate so there are "
            "no surprises on installation day."
        ),
        "category": "Water Heater",
    },
    {
        "question": "Are you licensed and insured?",
        "answer": (
            "Yes — we hold a current state plumbing contractor license and carry "
            "general liability and workers compensation insurance. We are happy to "
            "provide a certificate of insurance for landlords, property managers, "
            "or permit applications."
        ),
        "category": "Trust",
    },
    {
        "question": "What areas do you serve?",
        "answer": (
            "We serve Riverside and surrounding communities within approximately "
            "30 miles, including the greater metro area. Contact us for jobs farther "
            "out — we may still be able to help depending on the scope."
        ),
        "category": "Service Area",
    },
    {
        "question": "How do I get a free estimate?",
        "answer": (
            "Just tell us your name, what the issue is, and the best way to reach you "
            "right here in chat. We typically respond the same business day. A photo "
            "of the problem area helps us give you a more accurate quote upfront."
        ),
        "category": "Booking",
    },
]

_PLUMBING_MISSED_CALL_SUMMARY = (
    "Caller says they have a slow drain in their kitchen and a dripping faucet "
    "in the master bathroom. Looking for a quote, not an emergency."
)
_PLUMBING_MISSED_CALL_TRANSCRIPT = (
    "Yeah, so uh, the kitchen sink has been draining really slowly for like "
    "a week now. And also our master bath faucet has been dripping non-stop. "
    "Just wondering if someone could come out and take a look. Thanks."
)

# ---------------------------------------------------------------------------
# Salon vertical constants
# ---------------------------------------------------------------------------

_SALON_OWNER_EMAIL = "demo-salon@agentnexlify-demo.local"
_SALON_BUSINESS_NAME = "Luxe & Co. Salon (DEMO)"
_SALON_PHONE = "555-234-8800"
_SALON_CITY = "Lakewood"

_SALON_GREETING = (
    "Hi! I'm Mia, the virtual assistant for Luxe & Co. Salon. "
    "I can help you book a haircut, color treatment, or any of our services — "
    "and answer questions about our stylists, pricing, and availability. "
    "What can I help you with today?"
)

_SALON_HOURS = {
    "monday":    {"enabled": False, "start": "09:00", "end": "17:00"},
    "tuesday":   {"enabled": True,  "start": "09:00", "end": "19:00"},
    "wednesday": {"enabled": True,  "start": "09:00", "end": "19:00"},
    "thursday":  {"enabled": True,  "start": "09:00", "end": "20:00"},
    "friday":    {"enabled": True,  "start": "09:00", "end": "20:00"},
    "saturday":  {"enabled": True,  "start": "08:00", "end": "18:00"},
    "sunday":    {"enabled": True,  "start": "10:00", "end": "16:00"},
}

_SALON_FAQ_ENTRIES = [
    {
        "question": "How do I book an appointment?",
        "answer": (
            "You can book right here in chat! Tell us your preferred service, stylist "
            "(if you have a preference), and a few date/time options. We'll confirm "
            "your slot and send a reminder the day before."
        ),
        "category": "Booking",
    },
    {
        "question": "Do you offer bridal or event styling?",
        "answer": (
            "Yes — bridal hair, updos, and event styling are among our most popular "
            "services. We recommend booking a trial run 4–6 weeks before your event. "
            "Ask us about bridal party packages for groups of four or more."
        ),
        "category": "Services",
    },
    {
        "question": "What is a balayage and how long does it take?",
        "answer": (
            "Balayage is a freehand color technique that creates soft, natural-looking "
            "highlights with grow-out that blends seamlessly. A full balayage typically "
            "takes 2.5–4 hours depending on your hair length and density. We require a "
            "consultation for color corrections or if you have significant prior color."
        ),
        "category": "Color",
    },
    {
        "question": "What is your cancellation policy?",
        "answer": (
            "We ask for at least 24 hours notice for cancellations or reschedules. "
            "Appointments over 90 minutes (color, balayage, extensions) require a deposit "
            "that is applied to your service — deposits are refundable with 24-hour notice."
        ),
        "category": "Policy",
    },
    {
        "question": "How much do color corrections cost?",
        "answer": (
            "Color corrections are priced by consultation only — the work required varies "
            "widely based on your current color, desired result, and hair condition. "
            "Please book a complimentary consultation so your stylist can give you an "
            "accurate quote and a realistic timeline."
        ),
        "category": "Pricing",
    },
]

_SALON_MISSED_CALL_SUMMARY = (
    "Caller wants to book a balayage consult. Mentioned they have dark brown hair "
    "and want to go lighter for summer. First-time client."
)
_SALON_MISSED_CALL_TRANSCRIPT = (
    "Hi, I was calling about getting a balayage done. I've got dark brown hair "
    "down to my shoulders and I want to go a bit lighter for summer. "
    "It would be my first time here. Just wanted to know if I could book a "
    "consultation or something. Thanks so much!"
)

# ---------------------------------------------------------------------------
# Financial Services vertical constants
# ---------------------------------------------------------------------------

_FINANCIAL_OWNER_EMAIL = "demo-financial_services@agentnexlify-demo.local"
_FINANCIAL_BUSINESS_NAME = "Summit Trading Alerts (DEMO)"
_FINANCIAL_PHONE = "555-789-4400"
_FINANCIAL_CITY = "Chicago"

_FINANCIAL_GREETING = (
    "Hi! I'm Alex, the virtual assistant for Summit Trading Alerts. "
    "I can help you learn about our alert service, start a free trial, or "
    "answer questions about how our signals work. What brings you in today?"
)

_FINANCIAL_HOURS = {
    "monday":    {"enabled": True,  "start": "08:00", "end": "20:00"},
    "tuesday":   {"enabled": True,  "start": "08:00", "end": "20:00"},
    "wednesday": {"enabled": True,  "start": "08:00", "end": "20:00"},
    "thursday":  {"enabled": True,  "start": "08:00", "end": "20:00"},
    "friday":    {"enabled": True,  "start": "08:00", "end": "18:00"},
    "saturday":  {"enabled": False, "start": "09:00", "end": "15:00"},
    "sunday":    {"enabled": False, "start": "09:00", "end": "15:00"},
}

_FINANCIAL_FAQ_ENTRIES = [
    {
        "question": "How do I receive the trading alerts?",
        "answer": (
            "Alerts are pushed the moment they trigger via SMS and email so you can act "
            "quickly. After signing up you choose your delivery preferences in your "
            "account settings. Most members receive both channels for redundancy."
        ),
        "category": "Service",
    },
    {
        "question": "Do you offer a free trial?",
        "answer": (
            "Yes — you can try the full alert service free for 14 days with no credit "
            "card required. Ask us here and we'll get your trial activated today."
        ),
        "category": "Trial",
    },
    {
        "question": "Is this financial advice?",
        "answer": (
            "No. Summit Trading Alerts provides market alerts and educational commentary "
            "only — not personalized financial advice. Trading involves risk and past "
            "performance does not guarantee future results. Always consult a licensed "
            "financial advisor for decisions specific to your situation."
        ),
        "category": "Disclaimer",
    },
    {
        "question": "What markets do your alerts cover?",
        "answer": (
            "Our alerts cover US equities and options. We focus on high-liquidity, "
            "large-cap setups with defined risk parameters. Our documented alert history "
            "is available in the member portal — ask us to point you there."
        ),
        "category": "Service",
    },
    {
        "question": "How do I cancel my subscription?",
        "answer": (
            "You can cancel anytime with no lock-in. Message us here, use your account "
            "page, or email support and we will process it same day. No runaround."
        ),
        "category": "Billing",
    },
]

_FINANCIAL_MISSED_CALL_SUMMARY = (
    "Caller is a cancelled subscriber wanting to know about a special win-back offer. "
    "They cancelled 3 months ago and are interested in rejoining if the price is right."
)
_FINANCIAL_MISSED_CALL_TRANSCRIPT = (
    "Hey, I was a member about three months ago and I cancelled because I got busy. "
    "I saw you sent out an email about some kind of win-back deal and I wanted to "
    "find out more before it expires. Give me a call back or I can reply here. Thanks."
)

# ---------------------------------------------------------------------------
# Per-vertical definition registry
# ---------------------------------------------------------------------------

_DEMO_VERTICALS: dict[str, dict] = {
    "plumbing": {
        "owner_email": _PLUMBING_OWNER_EMAIL,
        "business_name": _PLUMBING_BUSINESS_NAME,
        "business_type": "plumbing",
        "phone": _PLUMBING_PHONE,
        "city": _PLUMBING_CITY,
        "greeting_message": _PLUMBING_GREETING,
        "bot_name": "Pat",
        "primary_color": "#1565C0",
        "hours": _PLUMBING_HOURS,
        "faq_entries": _PLUMBING_FAQ_ENTRIES,
        "industry_faq_key": "plumbing",
        "knowledge_base": (
            "Reliable Plumbing Co. (DEMO) — Riverside area plumbing services. "
            "Specialties: emergency pipe repair, drain cleaning, water heater "
            "replacement (tank + tankless), sewer line services, leak detection, "
            "faucet/fixture installation. Licensed, insured, free estimates. "
            "Hours: Mon-Fri 7 AM–6 PM, Sat 8 AM–4 PM."
        ),
        "missed_call_caller": _MISSED_CALL_CALLER_PLUMBING,
        "missed_call_summary": _PLUMBING_MISSED_CALL_SUMMARY,
        "missed_call_transcript": _PLUMBING_MISSED_CALL_TRANSCRIPT,
        "leads_builder": "_plumbing_leads_data",
        "appointments_builder": "_plumbing_appointments",
        "invoices_builder": "_plumbing_invoices",
    },
    "salon": {
        "owner_email": _SALON_OWNER_EMAIL,
        "business_name": _SALON_BUSINESS_NAME,
        "business_type": "salon",
        "phone": _SALON_PHONE,
        "city": _SALON_CITY,
        "greeting_message": _SALON_GREETING,
        "bot_name": "Mia",
        "primary_color": "#880E4F",
        "hours": _SALON_HOURS,
        "faq_entries": _SALON_FAQ_ENTRIES,
        "industry_faq_key": "salon",
        "knowledge_base": (
            "Luxe & Co. Salon (DEMO) — Lakewood full-service hair salon. "
            "Specialties: balayage, color corrections, bridal/event styling, "
            "cuts, blowouts, and keratin treatments. By appointment preferred. "
            "Hours: Tue-Fri 9 AM–8 PM, Sat 8 AM–6 PM, Sun 10 AM–4 PM."
        ),
        "missed_call_caller": _MISSED_CALL_CALLER_SALON,
        "missed_call_summary": _SALON_MISSED_CALL_SUMMARY,
        "missed_call_transcript": _SALON_MISSED_CALL_TRANSCRIPT,
        "leads_builder": "_salon_leads_data",
        "appointments_builder": "_salon_appointments",
        "invoices_builder": "_salon_invoices",
    },
    "financial_services": {
        "owner_email": _FINANCIAL_OWNER_EMAIL,
        "business_name": _FINANCIAL_BUSINESS_NAME,
        "business_type": "financial_services",
        "phone": _FINANCIAL_PHONE,
        "city": _FINANCIAL_CITY,
        "greeting_message": _FINANCIAL_GREETING,
        "bot_name": "Alex",
        "primary_color": "#1B5E20",
        "hours": _FINANCIAL_HOURS,
        "faq_entries": _FINANCIAL_FAQ_ENTRIES,
        "industry_faq_key": "financial_services",
        "knowledge_base": (
            "Summit Trading Alerts (DEMO) — Chicago-based subscription trading alert "
            "service. Provides real-time market alerts for US equities and options. "
            "Educational content only — not personalized financial advice. "
            "14-day free trial. Cancel anytime."
        ),
        "missed_call_caller": _MISSED_CALL_CALLER_FINANCIAL,
        "missed_call_summary": _FINANCIAL_MISSED_CALL_SUMMARY,
        "missed_call_transcript": _FINANCIAL_MISSED_CALL_TRANSCRIPT,
        "leads_builder": "_financial_leads_data",
        "appointments_builder": "_financial_appointments",
        "invoices_builder": "_financial_invoices",
    },
}

# ---------------------------------------------------------------------------
# Table -> tenant column mapping (sourced from tenant_scope.py)
# ---------------------------------------------------------------------------
# Verified from backend/services/tenant_scope.py _TENANT_COLUMN_OVERRIDES:
#   leads               -> client_id
#   conversations       -> client_id
#   os_threads          -> client_id
#   os_messages         -> client_id
#   os_agent_runs       -> client_id
#   appointments        -> tenant_id  (default)
#   invoices            -> tenant_id  (default)
#   chat_messages       -> tenant_id  (default)
#   action_items        -> tenant_id  (default)
#   activity_log        -> tenant_id  (default)

# Volatile tables deleted during reset (order matters for FK safety):
# os_agent_runs before os_messages/os_threads, chat_messages before conversations
_VOLATILE_TABLES = [
    # os_* — use client_id
    "os_agent_runs",
    "os_messages",
    "os_threads",
    # leads/conversations — use client_id
    "leads",
    "conversations",
    # tenant_id tables
    "appointments",
    "invoices",
    "chat_messages",
    "action_items",
    "activity_log",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ts(days_ago: int, hour: int = 10) -> str:
    """UTC ISO timestamp N days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def _appt_times(days_offset: int, start_hour: int) -> tuple[str, str]:
    base = datetime.now(timezone.utc).replace(
        hour=start_hour, minute=0, second=0, microsecond=0
    )
    start = base + timedelta(days=days_offset)
    end = start + timedelta(hours=2)
    return start.isoformat(), end.isoformat()


def _build_callback_sms(business_name: str, summary: str) -> str:
    base = f"Hi, this is {business_name}. Sorry we missed your call!"
    detail = (summary or "").strip()[:280]
    if detail:
        return f"{base} {detail} Reply here or call us back anytime."
    return f"{base} How can we help? Reply here or call us back anytime."


# ---------------------------------------------------------------------------
# Plumbing volatile data builders (unchanged from original)
# ---------------------------------------------------------------------------

def _plumbing_leads_data() -> list[dict]:
    return [
        {
            "name": "Marcus Webb",
            "email": "marcus.webb@demo.local",
            "phone": "555-101-0001",
            "areas_of_interest": "Burst pipe in basement — emergency",
            "status": "won",
            "lead_score": 95,
            "source": "widget",
            "notes": "DEMO: Pipe burst near water main. Dispatched same day. Job closed.",
            "created_at": _ts(18),
        },
        {
            "name": "Sandra Kline",
            "email": "sandra.kline@demo.local",
            "phone": "555-101-0002",
            "areas_of_interest": "Sewage backup, first-floor bathroom",
            "status": "qualified",
            "lead_score": 88,
            "source": "widget",
            "notes": "DEMO: Confirmed sewer line issue. Estimate sent. Awaiting sign-off.",
            "created_at": _ts(10),
        },
        {
            "name": "David Ong",
            "email": "david.ong@demo.local",
            "phone": "555-101-0003",
            "areas_of_interest": "Water heater replacement — 14-year-old unit leaking",
            "status": "won",
            "lead_score": 90,
            "source": "widget",
            "notes": "DEMO: Installed 50-gal Bradford White. Paid via invoice. Closed.",
            "created_at": _ts(22),
        },
        {
            "name": "Priya Nair",
            "email": "priya.nair@demo.local",
            "phone": "555-101-0004",
            "areas_of_interest": "Tankless water heater quote",
            "status": "qualified",
            "lead_score": 75,
            "source": "widget",
            "notes": "DEMO: Navien proposal sent. Needs electrical assessment first.",
            "created_at": _ts(7),
        },
        {
            "name": "Kevin Torres",
            "email": "kevin.torres@demo.local",
            "phone": "555-101-0005",
            "areas_of_interest": "Kitchen drain slow, garbage disposal backing up",
            "status": "contacted",
            "lead_score": 60,
            "source": "widget",
            "notes": "DEMO: Called customer 2x, left voicemail. Awaiting callback.",
            "created_at": _ts(5),
        },
        {
            "name": "Lila Hutchins",
            "email": "lila.hutchins@demo.local",
            "phone": "555-101-0006",
            "areas_of_interest": "Main sewer line — tree root blockage suspected",
            "status": "won",
            "lead_score": 85,
            "source": "widget",
            "notes": "DEMO: Hydro-jet + camera inspection completed. Roots cleared.",
            "created_at": _ts(30),
        },
        {
            "name": "George Patel",
            "email": "george.patel@demo.local",
            "phone": "555-101-0007",
            "areas_of_interest": "Full bathroom remodel rough-in plumbing",
            "status": "qualified",
            "lead_score": 72,
            "source": "widget",
            "notes": "DEMO: Large job. Estimate sent $2,400. Following up next week.",
            "created_at": _ts(14),
        },
        {
            "name": "Cindy Morales",
            "email": "cindy.morales@demo.local",
            "phone": "555-101-0008",
            "areas_of_interest": "Bid follow-up — kitchen sink reroute",
            "status": "lost",
            "lead_score": 40,
            "source": "widget",
            "notes": "DEMO: Went with another contractor — price sensitivity.",
            "created_at": _ts(25),
        },
        {
            "name": "Aaron Fields",
            "email": "aaron.fields@demo.local",
            "phone": "555-101-0009",
            "areas_of_interest": "Low water pressure throughout house",
            "status": "new",
            "lead_score": 50,
            "source": "widget",
            "notes": "DEMO: Captured via widget. Needs pressure test.",
            "created_at": _ts(2),
        },
        {
            "name": "Beth Carmichael",
            "email": "beth.carmichael@demo.local",
            "phone": "555-101-0010",
            "areas_of_interest": "Faucet replacement — master bath dripping",
            "status": "contacted",
            "lead_score": 45,
            "source": "widget",
            "notes": "DEMO: Emailed estimate for Moen faucet swap.",
            "created_at": _ts(3),
        },
        {
            "name": "Jorge Reyes",
            "email": "jorge.reyes@demo.local",
            "phone": "555-101-0011",
            "areas_of_interest": "Outdoor hose bib — frozen and cracked",
            "status": "new",
            "lead_score": 55,
            "source": "widget",
            "notes": "DEMO: Seasonal repair. Needs scheduling.",
            "created_at": _ts(1),
        },
        {
            "name": "Fiona Strand",
            "email": "fiona.strand@demo.local",
            "phone": "555-101-0012",
            "areas_of_interest": "Commercial unit — multiple toilets running",
            "status": "qualified",
            "lead_score": 80,
            "source": "widget",
            "notes": "DEMO: 8-unit rental complex. Owner wants flat-rate quote.",
            "created_at": _ts(8),
        },
    ]


def _plumbing_appointments(lead_ids: list[str]) -> list[dict]:
    s1, e1 = _appt_times(3, 9)
    s2, e2 = _appt_times(-5, 11)
    s3, e3 = _appt_times(7, 14)
    return [
        {
            "customer_name": "Sandra Kline",
            "customer_email": "sandra.kline@demo.local",
            "customer_phone": "555-101-0002",
            "start_time": s1,
            "end_time": e1,
            "status": "confirmed",
            "notes": "DEMO: Camera inspection + hydro-jet quote for sewer backup.",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
        },
        {
            "customer_name": "David Ong",
            "customer_email": "david.ong@demo.local",
            "customer_phone": "555-101-0003",
            "start_time": s2,
            "end_time": e2,
            "status": "completed",
            "notes": "DEMO: Water heater replacement completed. 50-gal Bradford White.",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
        },
        {
            "customer_name": "George Patel",
            "customer_email": "george.patel@demo.local",
            "customer_phone": "555-101-0007",
            "start_time": s3,
            "end_time": e3,
            "status": "confirmed",
            "notes": "DEMO: Bathroom rough-in walk-through. Bring permit checklist.",
            "lead_id": lead_ids[6] if len(lead_ids) > 6 else None,
        },
    ]


def _plumbing_invoices(lead_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    due_future = (now + timedelta(days=14)).date().isoformat()
    due_sent = (now - timedelta(days=3)).date().isoformat()
    paid_at = (now - timedelta(days=20)).isoformat()
    return [
        {
            "invoice_number": "DEMO-PLB-001",
            "lead_id": lead_ids[0] if lead_ids else None,
            "items_json": json.dumps([
                {"description": "Emergency burst pipe repair — basement water main",
                 "quantity": 1, "unit_price": 420.00, "total": 420.00},
                {"description": "Labor (2.5 hrs @ $120/hr)", "quantity": 2.5,
                 "unit_price": 120.00, "total": 300.00},
                {"description": "Materials: copper coupling + fittings",
                 "quantity": 1, "unit_price": 45.00, "total": 45.00},
            ]),
            "subtotal": 765.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 765.00,
            "status": "paid",
            "due_date": (now - timedelta(days=15)).date().isoformat(),
            "paid_at": paid_at,
            "payment_method": "credit_card",
            "notes": "DEMO: Emergency same-day burst pipe repair. Paid in full.",
        },
        {
            "invoice_number": "DEMO-PLB-002",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
            "items_json": json.dumps([
                {"description": "Sewer camera inspection",
                 "quantity": 1, "unit_price": 250.00, "total": 250.00},
                {"description": "Hydro-jetting main sewer line (up to 75 ft)",
                 "quantity": 1, "unit_price": 550.00, "total": 550.00},
            ]),
            "subtotal": 800.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 800.00,
            "status": "sent",
            "due_date": due_sent,
            "sent_at": (now - timedelta(days=3)).isoformat(),
            "sent_via": "email",
            "notes": "DEMO: Sewer inspection + hydro-jet estimate. Awaiting approval.",
        },
        {
            "invoice_number": "DEMO-PLB-003",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
            "items_json": json.dumps([
                {"description": "50-gallon Bradford White water heater (6-yr warranty)",
                 "quantity": 1, "unit_price": 890.00, "total": 890.00},
                {"description": "Installation labor + haul-away of old unit",
                 "quantity": 1, "unit_price": 280.00, "total": 280.00},
                {"description": "Expansion tank (code requirement)",
                 "quantity": 1, "unit_price": 95.00, "total": 95.00},
            ]),
            "subtotal": 1265.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 1265.00,
            "status": "draft",
            "due_date": due_future,
            "notes": "DEMO: Water heater replacement — draft pending final parts confirmation.",
        },
    ]


# ---------------------------------------------------------------------------
# Salon volatile data builders
# ---------------------------------------------------------------------------

def _salon_leads_data() -> list[dict]:
    return [
        {
            "name": "Olivia Chen",
            "email": "olivia.chen@demo.local",
            "phone": "555-202-0001",
            "areas_of_interest": "Balayage — want to go lighter for summer",
            "status": "won",
            "lead_score": 92,
            "source": "widget",
            "notes": "DEMO: Booked balayage with Kayla. Job completed. Loved result.",
            "created_at": _ts(20),
        },
        {
            "name": "Priya Sharma",
            "email": "priya.sharma@demo.local",
            "phone": "555-202-0002",
            "areas_of_interest": "Bridal hair trial for August wedding",
            "status": "qualified",
            "lead_score": 90,
            "source": "widget",
            "notes": "DEMO: Trial run booked for July 5. Bridal party of 4.",
            "created_at": _ts(8),
        },
        {
            "name": "Madison Torres",
            "email": "madison.torres@demo.local",
            "phone": "555-202-0003",
            "areas_of_interest": "Color correction — box dye removal",
            "status": "qualified",
            "lead_score": 80,
            "source": "widget",
            "notes": "DEMO: Consultation scheduled. Needs 2-session correction plan.",
            "created_at": _ts(5),
        },
        {
            "name": "Rachel Kim",
            "email": "rachel.kim@demo.local",
            "phone": "555-202-0004",
            "areas_of_interest": "Keratin treatment — frizzy hair",
            "status": "contacted",
            "lead_score": 65,
            "source": "widget",
            "notes": "DEMO: Emailed pricing. Awaiting callback.",
            "created_at": _ts(3),
        },
        {
            "name": "Elena Vasquez",
            "email": "elena.vasquez@demo.local",
            "phone": "555-202-0005",
            "areas_of_interest": "Haircut + highlights — maintenance trim",
            "status": "won",
            "lead_score": 70,
            "source": "widget",
            "notes": "DEMO: Regular client. Cut + partial highlights completed.",
            "created_at": _ts(14),
        },
        {
            "name": "Jessica Park",
            "email": "jessica.park@demo.local",
            "phone": "555-202-0006",
            "areas_of_interest": "Extensions consultation",
            "status": "new",
            "lead_score": 55,
            "source": "widget",
            "notes": "DEMO: Widget inquiry. Needs to book consult.",
            "created_at": _ts(1),
        },
        {
            "name": "Tamara Wells",
            "email": "tamara.wells@demo.local",
            "phone": "555-202-0007",
            "areas_of_interest": "Blowout + event styling — gala this weekend",
            "status": "won",
            "lead_score": 78,
            "source": "widget",
            "notes": "DEMO: Same-week booking. Event styling completed Friday.",
            "created_at": _ts(10),
        },
        {
            "name": "Chloe Martin",
            "email": "chloe.martin@demo.local",
            "phone": "555-202-0008",
            "areas_of_interest": "First haircut — pixie cut",
            "status": "new",
            "lead_score": 50,
            "source": "widget",
            "notes": "DEMO: New client. Consult needed before drastic cut.",
            "created_at": _ts(2),
        },
    ]


def _salon_appointments(lead_ids: list[str]) -> list[dict]:
    s1, e1 = _appt_times(2, 11)
    s2, e2 = _appt_times(-3, 13)
    s3, e3 = _appt_times(5, 10)
    return [
        {
            "customer_name": "Priya Sharma",
            "customer_email": "priya.sharma@demo.local",
            "customer_phone": "555-202-0002",
            "start_time": s1,
            "end_time": e1,
            "status": "confirmed",
            "notes": "DEMO: Bridal hair trial. 3.5 hr booking. Deposit collected.",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
        },
        {
            "customer_name": "Olivia Chen",
            "customer_email": "olivia.chen@demo.local",
            "customer_phone": "555-202-0001",
            "start_time": s2,
            "end_time": e2,
            "status": "completed",
            "notes": "DEMO: Full balayage session completed. Client thrilled.",
            "lead_id": lead_ids[0] if lead_ids else None,
        },
        {
            "customer_name": "Madison Torres",
            "customer_email": "madison.torres@demo.local",
            "customer_phone": "555-202-0003",
            "start_time": s3,
            "end_time": e3,
            "status": "confirmed",
            "notes": "DEMO: Color correction consultation — session 1 of 2.",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
        },
    ]


def _salon_invoices(lead_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    due_future = (now + timedelta(days=7)).date().isoformat()
    paid_at = (now - timedelta(days=14)).isoformat()
    return [
        {
            "invoice_number": "DEMO-SAL-001",
            "lead_id": lead_ids[0] if lead_ids else None,
            "items_json": json.dumps([
                {"description": "Balayage — full (shoulder-length)",
                 "quantity": 1, "unit_price": 220.00, "total": 220.00},
                {"description": "Gloss treatment",
                 "quantity": 1, "unit_price": 55.00, "total": 55.00},
                {"description": "Blowout + style",
                 "quantity": 1, "unit_price": 65.00, "total": 65.00},
            ]),
            "subtotal": 340.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 340.00,
            "status": "paid",
            "due_date": (now - timedelta(days=12)).date().isoformat(),
            "paid_at": paid_at,
            "payment_method": "credit_card",
            "notes": "DEMO: Balayage + gloss + blowout. Paid in full.",
        },
        {
            "invoice_number": "DEMO-SAL-002",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
            "items_json": json.dumps([
                {"description": "Bridal hair trial — updo",
                 "quantity": 1, "unit_price": 150.00, "total": 150.00},
                {"description": "Bridal day — hair (bride)",
                 "quantity": 1, "unit_price": 250.00, "total": 250.00},
                {"description": "Bridal party styling (3 attendants @ $120)",
                 "quantity": 3, "unit_price": 120.00, "total": 360.00},
            ]),
            "subtotal": 760.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 760.00,
            "status": "sent",
            "due_date": due_future,
            "sent_at": (now - timedelta(days=1)).isoformat(),
            "sent_via": "email",
            "notes": "DEMO: Bridal package invoice. 50% deposit already collected.",
        },
        {
            "invoice_number": "DEMO-SAL-003",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
            "items_json": json.dumps([
                {"description": "Color correction — session 1 (box dye removal)",
                 "quantity": 1, "unit_price": 180.00, "total": 180.00},
            ]),
            "subtotal": 180.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 180.00,
            "status": "draft",
            "due_date": (now + timedelta(days=14)).date().isoformat(),
            "notes": "DEMO: Color correction session 1 — draft pending session completion.",
        },
    ]


# ---------------------------------------------------------------------------
# Financial services volatile data builders
# ---------------------------------------------------------------------------

def _financial_leads_data() -> list[dict]:
    return [
        {
            "name": "Derek Hughes",
            "email": "derek.hughes@demo.local",
            "phone": "555-303-0001",
            "areas_of_interest": "Free trial sign-up — found us on Twitter",
            "status": "won",
            "lead_score": 85,
            "source": "widget",
            "notes": "DEMO: Trial converted to paid monthly. Active subscriber.",
            "created_at": _ts(25),
        },
        {
            "name": "Natalie Brooks",
            "email": "natalie.brooks@demo.local",
            "phone": "555-303-0002",
            "areas_of_interest": "Win-back — cancelled subscriber, 3 months ago",
            "status": "qualified",
            "lead_score": 78,
            "source": "widget",
            "notes": "DEMO: Called about win-back offer. Price-sensitive. Sent comparison.",
            "created_at": _ts(4),
        },
        {
            "name": "Marcus Powell",
            "email": "marcus.powell@demo.local",
            "phone": "555-303-0003",
            "areas_of_interest": "Trial — questions about alert delivery",
            "status": "qualified",
            "lead_score": 72,
            "source": "widget",
            "notes": "DEMO: Active trial day 8. Replied to check-in. Interested.",
            "created_at": _ts(8),
        },
        {
            "name": "Sandra Lee",
            "email": "sandra.lee@demo.local",
            "phone": "555-303-0004",
            "areas_of_interest": "Track record question — win rate",
            "status": "contacted",
            "lead_score": 60,
            "source": "widget",
            "notes": "DEMO: Sent performance log link. Awaiting reply.",
            "created_at": _ts(3),
        },
        {
            "name": "Ryan Foster",
            "email": "ryan.foster@demo.local",
            "phone": "555-303-0005",
            "areas_of_interest": "Subscription pricing — annual vs monthly",
            "status": "new",
            "lead_score": 55,
            "source": "widget",
            "notes": "DEMO: Widget inquiry. Needs pricing breakdown.",
            "created_at": _ts(1),
        },
        {
            "name": "Angela Torres",
            "email": "angela.torres@demo.local",
            "phone": "555-303-0006",
            "areas_of_interest": "Trial — cancelled day 5, no specific reason",
            "status": "lost",
            "lead_score": 30,
            "source": "widget",
            "notes": "DEMO: Early cancellation. No stated reason. Flagged for 30-day follow-up.",
            "created_at": _ts(15),
        },
        {
            "name": "Tom Nakamura",
            "email": "tom.nakamura@demo.local",
            "phone": "555-303-0007",
            "areas_of_interest": "Options alerts only — no equity positions",
            "status": "qualified",
            "lead_score": 70,
            "source": "widget",
            "notes": "DEMO: Options-focused trader. Confirmed our alerts cover options.",
            "created_at": _ts(6),
        },
        {
            "name": "Christine Webb",
            "email": "christine.webb@demo.local",
            "phone": "555-303-0008",
            "areas_of_interest": "Refund request — billing confusion",
            "status": "won",
            "lead_score": 40,
            "source": "widget",
            "notes": "DEMO: Refunded and re-enrolled. Resolved graciously — no chargeback.",
            "created_at": _ts(30),
        },
    ]


def _financial_appointments(lead_ids: list[str]) -> list[dict]:
    # Financial services: calls/demos rather than in-person appointments
    s1, e1 = _appt_times(2, 14)
    s2, e2 = _appt_times(-2, 10)
    s3, e3 = _appt_times(4, 16)
    return [
        {
            "customer_name": "Natalie Brooks",
            "customer_email": "natalie.brooks@demo.local",
            "customer_phone": "555-303-0002",
            "start_time": s1,
            "end_time": s1,  # 30-min call
            "status": "confirmed",
            "notes": "DEMO: Win-back call. Review performance log and special rate offer.",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
        },
        {
            "customer_name": "Marcus Powell",
            "customer_email": "marcus.powell@demo.local",
            "customer_phone": "555-303-0003",
            "start_time": s2,
            "end_time": s2,
            "status": "completed",
            "notes": "DEMO: Trial check-in call completed. Follow-up email sent.",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
        },
        {
            "customer_name": "Tom Nakamura",
            "customer_email": "tom.nakamura@demo.local",
            "customer_phone": "555-303-0007",
            "start_time": s3,
            "end_time": s3,
            "status": "confirmed",
            "notes": "DEMO: Onboarding call — options alert setup walkthrough.",
            "lead_id": lead_ids[6] if len(lead_ids) > 6 else None,
        },
    ]


def _financial_invoices(lead_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    due_future = (now + timedelta(days=30)).date().isoformat()
    paid_at1 = (now - timedelta(days=22)).isoformat()
    paid_at2 = (now - timedelta(days=7)).isoformat()
    return [
        {
            "invoice_number": "DEMO-FIN-001",
            "lead_id": lead_ids[0] if lead_ids else None,
            "items_json": json.dumps([
                {"description": "Monthly subscription — Summit Trading Alerts",
                 "quantity": 1, "unit_price": 97.00, "total": 97.00},
            ]),
            "subtotal": 97.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 97.00,
            "status": "paid",
            "due_date": (now - timedelta(days=20)).date().isoformat(),
            "paid_at": paid_at1,
            "payment_method": "credit_card",
            "notes": "DEMO: Monthly subscription — trial conversion.",
        },
        {
            "invoice_number": "DEMO-FIN-002",
            "lead_id": lead_ids[2] if len(lead_ids) > 2 else None,
            "items_json": json.dumps([
                {"description": "Monthly subscription — Summit Trading Alerts (trial month)",
                 "quantity": 1, "unit_price": 0.00, "total": 0.00},
            ]),
            "subtotal": 0.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 0.00,
            "status": "paid",
            "due_date": (now - timedelta(days=5)).date().isoformat(),
            "paid_at": paid_at2,
            "payment_method": "trial",
            "notes": "DEMO: 14-day free trial subscription receipt.",
        },
        {
            "invoice_number": "DEMO-FIN-003",
            "lead_id": lead_ids[6] if len(lead_ids) > 6 else None,
            "items_json": json.dumps([
                {"description": "Monthly subscription — Summit Trading Alerts",
                 "quantity": 1, "unit_price": 97.00, "total": 97.00},
            ]),
            "subtotal": 97.00, "tax_rate": 0.00, "tax_amount": 0.00, "total": 97.00,
            "status": "draft",
            "due_date": due_future,
            "notes": "DEMO: Pending — new subscriber awaiting first billing cycle.",
        },
    ]


# Map builder names to functions
_LEADS_BUILDERS = {
    "_plumbing_leads_data": _plumbing_leads_data,
    "_salon_leads_data": _salon_leads_data,
    "_financial_leads_data": _financial_leads_data,
}
_APPT_BUILDERS = {
    "_plumbing_appointments": _plumbing_appointments,
    "_salon_appointments": _salon_appointments,
    "_financial_appointments": _financial_appointments,
}
_INV_BUILDERS = {
    "_plumbing_invoices": _plumbing_invoices,
    "_salon_invoices": _salon_invoices,
    "_financial_invoices": _financial_invoices,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_demo_tenants(db: Any) -> dict[str, str]:
    """Ensure all three demo verticals exist. Creates any missing ones.

    Returns {vertical: tenant_id, ...} for successfully ensured tenants.
    Idempotent — safe to call multiple times.  Never raises.
    """
    result: dict[str, str] = {}

    # Fetch all existing demo tenants in one query
    try:
        existing = (
            db.table("tenants")
            .select("id, owner_email, business_type")
            .eq("is_demo", True)
            .execute()
        )
        existing_by_email: dict[str, str] = {}
        if existing.data:
            for row in existing.data:
                existing_by_email[row["owner_email"]] = row["id"]
    except Exception:
        logger.exception("ensure_demo_tenants: failed to query existing demo tenants")
        return result

    for vertical, cfg in _DEMO_VERTICALS.items():
        email = cfg["owner_email"]
        if email in existing_by_email:
            tid = existing_by_email[email]
            logger.info(
                "ensure_demo_tenants: vertical=%s already exists tenant_id=%s",
                vertical, tid,
            )
            result[vertical] = tid
        else:
            logger.info(
                "ensure_demo_tenants: vertical=%s not found — seeding", vertical
            )
            tid = _seed_demo_tenant(db, vertical)
            if tid:
                result[vertical] = tid
            else:
                logger.error(
                    "ensure_demo_tenants: seed failed for vertical=%s", vertical
                )

    return result


def get_demo_tenant(db: Any, vertical: str) -> str | None:
    """Return tenant_id for the given demo vertical, or None if not found.

    vertical must be one of "plumbing", "salon", "financial_services".
    Never raises.
    """
    cfg = _DEMO_VERTICALS.get(vertical)
    if not cfg:
        logger.warning("get_demo_tenant: unknown vertical=%s", vertical)
        return None
    try:
        result = (
            db.table("tenants")
            .select("id")
            .eq("owner_email", cfg["owner_email"])
            .eq("is_demo", True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception:
        logger.exception(
            "get_demo_tenant: query failed for vertical=%s", vertical
        )
        return None


def ensure_demo_tenant(db: Any) -> str | None:
    """Back-compat wrapper — returns the plumbing demo tenant_id.

    Callers: demo_reset_job.py, scripts/demos/seed_plumbing_demo.py, tests.
    Behaviour: find the first is_demo tenant (plumbing) or create it.
    Never raises.
    """
    # Fast path: check for existing plumbing tenant by owner_email
    try:
        existing = (
            db.table("tenants")
            .select("id, business_name")
            .eq("is_demo", True)
            .limit(1)
            .execute()
        )
        if existing.data:
            tenant_id = existing.data[0]["id"]
            logger.info(
                "ensure_demo_tenant: found existing demo tenant id=%s", tenant_id
            )
            return tenant_id
    except Exception:
        logger.exception(
            "ensure_demo_tenant: failed to query for existing demo tenant"
        )
        return None

    logger.info("ensure_demo_tenant: no demo tenant found — seeding plumbing demo")
    return _seed_demo_tenant(db, "plumbing")


def reset_demo_tenant(db: Any, tenant_id: str) -> dict:
    """Delete volatile rows for the demo tenant and re-seed them.

    Hard-asserts is_demo=True on the provided tenant_id before deleting
    anything. Returns counts summary:
        {"deleted": {table: count, ...}, "seeded": {...}}
    """
    # Hard assertion: never delete production data
    try:
        check = (
            db.table("tenants")
            .select("id, is_demo, owner_email, business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not check.data:
            logger.error(
                "reset_demo_tenant: tenant_id=%s not found — aborting", tenant_id
            )
            return {"error": "tenant not found"}
        row = check.data[0]
        if not row.get("is_demo"):
            logger.error(
                "reset_demo_tenant: tenant_id=%s is_demo=False — REFUSING to delete. "
                "Only demo tenants may be reset.",
                tenant_id,
            )
            return {"error": "not a demo tenant"}
    except Exception:
        logger.exception(
            "reset_demo_tenant: is_demo check failed for tenant_id=%s — aborting",
            tenant_id,
        )
        return {"error": "is_demo check failed"}

    # Determine vertical from owner_email for re-seeding
    owner_email = row.get("owner_email", "")
    vertical = _vertical_from_email(owner_email)

    deleted: dict[str, int] = {}

    # Delete volatile rows in dependency order
    for table in _VOLATILE_TABLES:
        col = tenant_scope_column(table)
        try:
            result = (
                db.table(table)
                .delete()
                .eq(col, tenant_id)
                .execute()
            )
            count = len(result.data) if result.data else 0
            deleted[table] = count
            logger.info(
                "reset_demo_tenant: deleted %d rows from %s (%s=%s)",
                count, table, col, tenant_id,
            )
        except Exception:
            logger.exception(
                "reset_demo_tenant: failed to delete from %s for tenant_id=%s",
                table, tenant_id,
            )
            deleted[table] = -1  # -1 signals failure for that table

    # Re-seed volatile data
    seeded = _seed_volatile(db, tenant_id, vertical)

    summary = {"deleted": deleted, "seeded": seeded}
    logger.info(
        "reset_demo_tenant: complete for tenant_id=%s summary=%s", tenant_id, summary
    )
    return summary


# ---------------------------------------------------------------------------
# Internal seeding logic
# ---------------------------------------------------------------------------

def _vertical_from_email(owner_email: str) -> str:
    """Map owner_email back to vertical name. Defaults to 'plumbing'."""
    for vertical, cfg in _DEMO_VERTICALS.items():
        if cfg["owner_email"] == owner_email:
            return vertical
    return "plumbing"


def _seed_demo_tenant(db: Any, vertical: str) -> str | None:
    """Create the full demo tenant for `vertical` and all sub-rows.

    Returns tenant_id or None on failure.
    """
    cfg = _DEMO_VERTICALS[vertical]
    tenant_id: str | None = None

    # 1. Tenant row
    try:
        result = (
            db.table("tenants")
            .insert({
                "business_name": cfg["business_name"],
                "business_type": cfg["business_type"],
                "owner_email": cfg["owner_email"],
                "phone": cfg["phone"],
                "city": cfg["city"],
                "plan": "professional",
                "plan_status": "active",
                "is_demo": True,
                "ai_monthly_token_alert_threshold": _AI_TOKEN_ALERT,
                "ai_monthly_token_hard_limit": _AI_TOKEN_HARD,
            })
            .execute()
        )
        if not result.data:
            logger.error(
                "_seed_demo_tenant: tenant insert returned no data for vertical=%s",
                vertical,
            )
            return None
        tenant_id = result.data[0]["id"]
        logger.info(
            "_seed_demo_tenant: tenant inserted vertical=%s id=%s", vertical, tenant_id
        )
    except Exception:
        logger.exception(
            "_seed_demo_tenant: tenant insert failed for vertical=%s", vertical
        )
        return None

    # 2. Widget config
    try:
        db.table("widget_configs").insert({
            "tenant_id": tenant_id,
            "bot_name": cfg["bot_name"],
            "primary_color": cfg["primary_color"],
            "greeting_message": cfg["greeting_message"],
            "position": "bottom-right",
            "collect_name": True,
            "collect_email": True,
            "collect_phone": True,
            "show_watermark": False,
            "booking_enabled": True,
            "knowledge_base": cfg["knowledge_base"],
        }).execute()
        logger.info(
            "_seed_demo_tenant: widget_config inserted for vertical=%s", vertical
        )
    except Exception:
        logger.exception(
            "_seed_demo_tenant: widget_config insert failed for vertical=%s (non-fatal)",
            vertical,
        )

    # 3. Business hours
    try:
        db.table("business_hours").insert({
            "tenant_id": tenant_id,
            "timezone": "America/Chicago" if vertical == "financial_services" else "America/Los_Angeles",
            "hours": json.dumps(cfg["hours"]),
            "slot_duration_minutes": 30 if vertical == "financial_services" else 60,
            "buffer_minutes": 15,
            "max_advance_days": 14,
        }).execute()
        logger.info(
            "_seed_demo_tenant: business_hours inserted for vertical=%s", vertical
        )
    except Exception:
        logger.exception(
            "_seed_demo_tenant: business_hours insert failed for vertical=%s (non-fatal)",
            vertical,
        )

    # 4. FAQ entries
    inserted_faqs = 0
    for faq in cfg["faq_entries"]:
        try:
            db.table("faq_entries").insert({
                "tenant_id": tenant_id,
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "is_active": True,
            }).execute()
            inserted_faqs += 1
        except Exception:
            logger.warning(
                "_seed_demo_tenant: FAQ insert failed for '%s' (vertical=%s)",
                faq["question"], vertical,
                exc_info=True,
            )
    logger.info(
        "_seed_demo_tenant: %d FAQ entries inserted for vertical=%s",
        inserted_faqs, vertical,
    )

    # 4b. Industry FAQ pack (optional)
    try:
        from backend.services.industry_faqs import seed_industry_faqs
        seed_industry_faqs(
            tenant_id=tenant_id,
            industry=cfg["industry_faq_key"],
            business_name=cfg["business_name"],
            city=cfg["city"],
        )
        logger.info(
            "_seed_demo_tenant: industry_faqs seeded for vertical=%s", vertical
        )
    except Exception:
        logger.warning(
            "_seed_demo_tenant: industry_faqs failed for vertical=%s (non-fatal)",
            vertical, exc_info=True,
        )

    # 5–8. Volatile rows
    _seed_volatile(db, tenant_id, vertical)

    return tenant_id


def _seed_volatile(db: Any, tenant_id: str, vertical: str = "plumbing") -> dict:
    """Seed the volatile demo rows: leads, appointments, invoices, Agent OS thread.

    Returns counts of rows inserted per entity type.
    """
    cfg = _DEMO_VERTICALS.get(vertical, _DEMO_VERTICALS["plumbing"])

    seeded: dict[str, int] = {
        "leads": 0,
        "appointments": 0,
        "invoices": 0,
        "os_thread": 0,
    }

    # 5. Leads — use client_id
    lead_ids: list[str] = []
    leads_fn = _LEADS_BUILDERS[cfg["leads_builder"]]
    for lead in leads_fn():
        try:
            lr = db.table("leads").insert({
                "client_id": tenant_id,
                "name": lead["name"],
                "email": lead["email"],
                "phone": lead["phone"],
                "areas_of_interest": lead["areas_of_interest"],
                "status": lead["status"],
                "lead_score": lead["lead_score"],
                "source": lead["source"],
                "notes": lead["notes"],
                "created_at": lead["created_at"],
            }).execute()
            if lr.data:
                lead_ids.append(lr.data[0]["id"])
                seeded["leads"] += 1
            else:
                logger.warning(
                    "_seed_volatile: lead insert returned no data for %s", lead["email"]
                )
        except Exception:
            logger.exception(
                "_seed_volatile: lead insert failed for %s", lead.get("email")
            )

    # 6. Appointments — use tenant_id
    appt_fn = _APPT_BUILDERS[cfg["appointments_builder"]]
    for appt in appt_fn(lead_ids):
        try:
            ar = db.table("appointments").insert({
                "tenant_id": tenant_id,
                **appt,
            }).execute()
            if ar.data:
                seeded["appointments"] += 1
            else:
                logger.warning(
                    "_seed_volatile: appointment insert returned no data for %s",
                    appt.get("customer_name"),
                )
        except Exception:
            logger.exception(
                "_seed_volatile: appointment insert failed for %s",
                appt.get("customer_name"),
            )

    # 7. Invoices — use tenant_id
    inv_fn = _INV_BUILDERS[cfg["invoices_builder"]]
    for inv in inv_fn(lead_ids):
        try:
            ivr = db.table("invoices").insert({
                "tenant_id": tenant_id,
                **inv,
            }).execute()
            if ivr.data:
                seeded["invoices"] += 1
            else:
                logger.warning(
                    "_seed_volatile: invoice insert returned no data for %s",
                    inv.get("invoice_number"),
                )
        except Exception:
            logger.exception(
                "_seed_volatile: invoice insert failed for %s",
                inv.get("invoice_number"),
            )

    # 8. Agent OS missed-call thread — os_* uses client_id
    missed_caller = cfg["missed_call_caller"]
    missed_summary = cfg["missed_call_summary"]
    missed_transcript = cfg["missed_call_transcript"]
    business_name = cfg["business_name"]

    thread_id: str | None = None
    try:
        tr = (
            tenant_table(db, "os_threads", tenant_id)
            .insert({
                "title": f"Missed call from {missed_caller}",
                "source": "voice",
                "status": "open",
                "created_by": "system",
            })
            .execute()
        )
        thread_id = tr.data[0]["id"] if tr.data else None
        if thread_id:
            seeded["os_thread"] += 1
            logger.info(
                "_seed_volatile: os_threads inserted id=%s vertical=%s",
                thread_id, vertical,
            )
    except Exception:
        logger.exception(
            "_seed_volatile: os_threads insert failed for vertical=%s (non-fatal)",
            vertical,
        )

    if thread_id:
        try:
            content = f"Voicemail from {missed_caller}."
            content += f"\n\nSummary: {missed_summary}"
            content += f'\n\nThey said: "{missed_transcript[:400]}"'
            tenant_table(db, "os_messages", tenant_id).insert({
                "thread_id": thread_id,
                "role": "user",
                "content": content,
                "inbound_kind": "voicemail",
                "source_ref": f"demo-call-{vertical}-001",
            }).execute()
            logger.info(
                "_seed_volatile: os_messages inserted for vertical=%s", vertical
            )
        except Exception:
            logger.exception(
                "_seed_volatile: os_messages insert failed for vertical=%s (non-fatal)",
                vertical,
            )

        try:
            sms_body = _build_callback_sms(business_name, missed_summary)
            deliverable = {
                "title": f"Text back {missed_caller} about their voicemail",
                "body": f"{sms_body}\n\nRecipient: {missed_caller}",
                "channel": "sms",
                "metadata": {
                    "recipient": missed_caller,
                    "call_id": f"demo-call-{vertical}-001",
                    "lead_id": lead_ids[0] if lead_ids else None,
                    "source": "missed_call_recovery",
                },
            }
            tenant_table(db, "os_agent_runs", tenant_id).insert({
                "thread_id": thread_id,
                "agent_name": "lead_nurture",
                "status": "succeeded",
                "action_type": "sms.send",
                "deliverable": deliverable,
                "deliverable_status": "pending",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "thought_process": [
                    {
                        "step": "missed_call_recovery",
                        "detail": "Drafted callback text from voicemail transcription",
                    }
                ],
            }).execute()
            logger.info(
                "_seed_volatile: os_agent_runs inserted for vertical=%s", vertical
            )
        except Exception:
            logger.exception(
                "_seed_volatile: os_agent_runs insert failed for vertical=%s (non-fatal)",
                vertical,
            )

    # 9. Welcome thread
    try:
        import asyncio
        from backend.services.welcome_thread import create_welcome_thread

        coro = create_welcome_thread(
            db,
            tenant_id=tenant_id,
            business_name=business_name,
            business_type=cfg["business_type"],
            website_url=None,
        )
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            welcome_id = future.result(timeout=10)
        except RuntimeError:
            welcome_id = asyncio.run(coro)

        if welcome_id:
            seeded["welcome_thread"] = 1
            logger.info(
                "_seed_volatile: welcome_thread inserted id=%s vertical=%s",
                welcome_id, vertical,
            )
        else:
            seeded["welcome_thread"] = 0
    except Exception:
        logger.warning(
            "_seed_volatile: welcome_thread creation failed for vertical=%s (non-fatal)",
            vertical, exc_info=True,
        )
        seeded.setdefault("welcome_thread", 0)

    logger.info(
        "_seed_volatile: seeded for tenant_id=%s vertical=%s: %s",
        tenant_id, vertical, seeded,
    )
    return seeded
