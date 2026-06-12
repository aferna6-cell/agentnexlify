"""Seed a local-only demo tenant for the plumbing vertical prospect meeting.

Creates:
  - tenants row (plan=professional, business_type='plumbing')
  - widget_configs row (api_key, bot_name, knowledge_base, greeting)
  - business_hours row (Mon-Fri 7 AM - 6 PM, Sat 8 AM - 4 PM, Sun off)
  - 10 FAQ entries covering the most common plumbing questions (via inline
    data — same pattern as powerwash; industry_faqs.seed_industry_faqs is
    also called to layer on the canonical plumbing pack)
  - 12 leads in varied statuses: new, contacted, qualified, won, lost,
    with plumbing-real content (burst pipe, water heater, drain cleaning, etc.)
  - 3 appointments (upcoming, completed, cancelled)
  - 3 invoices (draft, sent, paid)
  - 1 Agent OS missed-call/voice-recovery thread:
      os_threads  (source='voice', title='Missed call from +15551234567')
      os_messages (inbound voicemail summary)
      os_agent_runs (agent_name='lead_nurture', deliverable_status='pending',
                     action_type='sms.send')

SAFETY: Aborts immediately if SUPABASE_URL points at the production database.

Usage (from project root, venv active):
    python scripts/demos/seed_plumbing_demo.py

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in environment or .env file.
Idempotent: re-running will SKIP rows that already exist (matched by
owner_email for the tenant; individual sub-rows checked by count or
question text).
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── project root on path ─────────────────────────────────────────────────────
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── PROD GUARD ────────────────────────────────────────────────────────────────
PROD_URL = "https://pxserpybmajixqrmzaly.supabase.co"

# ── Demo tenant constants ─────────────────────────────────────────────────────
DEMO_OWNER_EMAIL = "demo-plumbing@agentnexlify-demo.local"
DEMO_BUSINESS_NAME = "Reliable Plumbing Co. (DEMO)"
DEMO_PHONE = "555-321-7700"
DEMO_CITY = "Riverside"

GREETING_MESSAGE = (
    "Hi! I'm Pat, the virtual assistant for Reliable Plumbing Co. "
    "I can answer questions about our services, pricing, and availability — "
    "or help you get a free estimate. Got a leak, clogged drain, or water "
    "heater issue? Tell me what's going on and I'll help you right away."
)

BUSINESS_HOURS = {
    "monday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "tuesday":   {"enabled": True,  "start": "07:00", "end": "18:00"},
    "wednesday": {"enabled": True,  "start": "07:00", "end": "18:00"},
    "thursday":  {"enabled": True,  "start": "07:00", "end": "18:00"},
    "friday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "saturday":  {"enabled": True,  "start": "08:00", "end": "16:00"},
    "sunday":    {"enabled": False, "start": "09:00", "end": "17:00"},
}

FAQ_ENTRIES = [
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

# ── Lead data — 12 leads in varied statuses ───────────────────────────────────
# leads table uses client_id (NOT tenant_id), status (NOT lead_stage),
# areas_of_interest (NOT service_interest)

def _ts(days_ago: int, hour: int = 10) -> str:
    """UTC ISO timestamp N days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


LEADS = [
    # --- hot / emergency ---
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
    # --- water heater ---
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
    # --- drain cleaning ---
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
    # --- bids / follow-ups ---
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
    # --- misc residential ---
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

# ── Appointments (3) ──────────────────────────────────────────────────────────
# appointments uses tenant_id (standard) and has a EXCLUDE constraint for
# confirmed/overlapping slots — so we stagger times.

def _appt_times(days_offset: int, start_hour: int) -> tuple[str, str]:
    """Return (start_time, end_time) ISO strings."""
    base = datetime.now(timezone.utc).replace(
        hour=start_hour, minute=0, second=0, microsecond=0
    )
    start = base + timedelta(days=days_offset)
    end = start + timedelta(hours=2)
    return start.isoformat(), end.isoformat()


def _build_appointments(lead_ids: list[str]) -> list[dict]:
    s1, e1 = _appt_times(3, 9)    # upcoming: 3 days out, 9 AM
    s2, e2 = _appt_times(-5, 11)  # completed: 5 days ago, 11 AM
    s3, e3 = _appt_times(7, 14)   # confirmed for later (different time slot)

    lead0 = lead_ids[0] if len(lead_ids) > 0 else None
    lead1 = lead_ids[2] if len(lead_ids) > 2 else None  # David Ong — water heater

    return [
        {
            "customer_name": "Sandra Kline",
            "customer_email": "sandra.kline@demo.local",
            "customer_phone": "555-101-0002",
            "start_time": s1,
            "end_time": e1,
            "status": "confirmed",
            "notes": "DEMO: Camera inspection + hydro-jet quote for sewer backup. Confirm 24h prior.",
            "lead_id": lead_ids[1] if len(lead_ids) > 1 else None,
        },
        {
            "customer_name": "David Ong",
            "customer_email": "david.ong@demo.local",
            "customer_phone": "555-101-0003",
            "start_time": s2,
            "end_time": e2,
            "status": "completed",
            "notes": "DEMO: Water heater replacement completed. 50-gal Bradford White installed.",
            "lead_id": lead1,
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


# ── Invoices (3) ─────────────────────────────────────────────────────────────
# invoices uses tenant_id (standard)

def _build_invoices(lead_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    due_future = (now + timedelta(days=14)).date().isoformat()
    due_sent = (now - timedelta(days=3)).date().isoformat()
    paid_at = (now - timedelta(days=20)).isoformat()

    lead_won_pipe = lead_ids[0] if len(lead_ids) > 0 else None   # Marcus Webb
    lead_won_wh = lead_ids[2] if len(lead_ids) > 2 else None     # David Ong
    lead_qual_sewer = lead_ids[1] if len(lead_ids) > 1 else None  # Sandra Kline

    return [
        {
            "invoice_number": "DEMO-PLB-001",
            "lead_id": lead_won_pipe,
            "items_json": json.dumps([
                {"description": "Emergency burst pipe repair — basement water main",
                 "quantity": 1, "unit_price": 420.00, "total": 420.00},
                {"description": "Labor (2.5 hrs @ $120/hr)", "quantity": 2.5,
                 "unit_price": 120.00, "total": 300.00},
                {"description": "Materials: copper coupling + fittings",
                 "quantity": 1, "unit_price": 45.00, "total": 45.00},
            ]),
            "subtotal": 765.00,
            "tax_rate": 0.00,
            "tax_amount": 0.00,
            "total": 765.00,
            "status": "paid",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=15)).date().isoformat(),
            "paid_at": paid_at,
            "payment_method": "credit_card",
            "notes": "DEMO: Emergency same-day burst pipe repair. Paid in full.",
        },
        {
            "invoice_number": "DEMO-PLB-002",
            "lead_id": lead_qual_sewer,
            "items_json": json.dumps([
                {"description": "Sewer camera inspection",
                 "quantity": 1, "unit_price": 250.00, "total": 250.00},
                {"description": "Hydro-jetting main sewer line (up to 75 ft)",
                 "quantity": 1, "unit_price": 550.00, "total": 550.00},
            ]),
            "subtotal": 800.00,
            "tax_rate": 0.00,
            "tax_amount": 0.00,
            "total": 800.00,
            "status": "sent",
            "due_date": due_sent,
            "sent_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "sent_via": "email",
            "notes": "DEMO: Sewer inspection + hydro-jet estimate. Awaiting approval.",
        },
        {
            "invoice_number": "DEMO-PLB-003",
            "lead_id": lead_won_wh,
            "items_json": json.dumps([
                {"description": "50-gallon Bradford White water heater (6-yr warranty)",
                 "quantity": 1, "unit_price": 890.00, "total": 890.00},
                {"description": "Installation labor + haul-away of old unit",
                 "quantity": 1, "unit_price": 280.00, "total": 280.00},
                {"description": "Expansion tank (code requirement)",
                 "quantity": 1, "unit_price": 95.00, "total": 95.00},
            ]),
            "subtotal": 1265.00,
            "tax_rate": 0.00,
            "tax_amount": 0.00,
            "total": 1265.00,
            "status": "draft",
            "due_date": due_future,
            "notes": "DEMO: Water heater replacement — draft pending final parts confirmation.",
        },
    ]


# ── Agent OS — missed-call voice recovery thread ──────────────────────────────
# os_threads, os_messages, os_agent_runs all use client_id (not tenant_id).
# Shape mirrors backend/services/voice_recovery.py::create_missed_call_followup.

MISSED_CALL_CALLER = "+15551234567"
MISSED_CALL_SUMMARY = (
    "Caller says they have a slow drain in their kitchen and a dripping faucet "
    "in the master bathroom. Looking for a quote, not an emergency."
)
MISSED_CALL_TRANSCRIPT_EXCERPT = (
    "Yeah, so uh, the kitchen sink has been draining really slowly for like "
    "a week now. And also our master bath faucet has been dripping non-stop. "
    "Just wondering if someone could come out and take a look. Thanks."
)


def _build_callback_sms(business_name: str, summary: str, caller: str) -> str:
    base = f"Hi, this is {business_name}. Sorry we missed your call!"
    detail = (summary or "").strip()[:280]
    if detail:
        return f"{base} {detail} Reply here or call us back anytime."
    return f"{base} How can we help? Reply here or call us back anytime."


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # --- imports deferred so project_root is on sys.path first ---
    try:
        from backend.config import settings
        from backend.models.database import get_supabase
        from backend.services.tenant_scope import tenant_scope_column, tenant_table
    except ImportError as exc:
        logger.error(
            "Import failed: %s — run from project root with venv active", exc
        )
        sys.exit(1)

    # --- PROD GUARD ---
    supabase_url = (settings.supabase_url or "").rstrip("/")
    if supabase_url == PROD_URL.rstrip("/"):
        logger.error(
            "ABORT: SUPABASE_URL points at the production database (%s). "
            "This script must only run against a LOCAL Supabase instance. "
            "Set SUPABASE_URL to your local Supabase URL "
            "(e.g. http://localhost:54321) and re-run.",
            supabase_url,
        )
        sys.exit(1)

    if not supabase_url or not settings.supabase_service_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    logger.info(
        "Targeting Supabase at: %s (NOT production — safe to proceed)", supabase_url
    )

    db = get_supabase()

    # ── 1. Tenant ─────────────────────────────────────────────────────────────
    tenant_id: str | None = None

    existing = (
        db.table("tenants")
        .select("id, business_name")
        .eq("owner_email", DEMO_OWNER_EMAIL)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant_id = existing.data[0]["id"]
        logger.info("Tenant already exists — id=%s  SKIP insert", tenant_id)
    else:
        result = (
            db.table("tenants")
            .insert({
                "business_name": DEMO_BUSINESS_NAME,
                "business_type": "plumbing",
                "owner_email": DEMO_OWNER_EMAIL,
                "phone": DEMO_PHONE,
                "city": DEMO_CITY,
                "plan": "professional",
                "plan_status": "active",
            })
            .execute()
        )
        if not result.data:
            logger.error("Failed to insert tenant: %s", result)
            sys.exit(1)
        tenant_id = result.data[0]["id"]
        logger.info("Tenant inserted — id=%s", tenant_id)

    # ── 2. Widget config ──────────────────────────────────────────────────────
    api_key: str | None = None

    existing_wc = (
        db.table("widget_configs")
        .select("id, api_key")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if existing_wc.data:
        api_key = existing_wc.data[0]["api_key"]
        logger.info(
            "widget_config already exists — api_key=%s  SKIP insert", api_key
        )
    else:
        wc_result = (
            db.table("widget_configs")
            .insert({
                "tenant_id": tenant_id,
                "bot_name": "Pat",
                "primary_color": "#1565C0",
                "greeting_message": GREETING_MESSAGE,
                "position": "bottom-right",
                "collect_name": True,
                "collect_email": True,
                "collect_phone": True,
                "show_watermark": False,
                "booking_enabled": True,
                "knowledge_base": (
                    "Reliable Plumbing Co. (DEMO) — Riverside area plumbing services. "
                    "Specialties: emergency pipe repair, drain cleaning, water heater "
                    "replacement (tank + tankless), sewer line services, leak detection, "
                    "faucet/fixture installation. Licensed, insured, free estimates. "
                    "Hours: Mon-Fri 7 AM–6 PM, Sat 8 AM–4 PM."
                ),
            })
            .execute()
        )
        if not wc_result.data:
            logger.error("Failed to insert widget_config: %s", wc_result)
            sys.exit(1)
        api_key = wc_result.data[0]["api_key"]
        logger.info("widget_config inserted — api_key=%s", api_key)

    # ── 3. Business hours ─────────────────────────────────────────────────────
    existing_bh = (
        db.table("business_hours")
        .select("id")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if existing_bh.data:
        logger.info("business_hours already exist — SKIP insert")
    else:
        bh_result = (
            db.table("business_hours")
            .insert({
                "tenant_id": tenant_id,
                "timezone": "America/Los_Angeles",
                "hours": json.dumps(BUSINESS_HOURS),
                "slot_duration_minutes": 90,
                "buffer_minutes": 30,
                "max_advance_days": 14,
            })
            .execute()
        )
        if not bh_result.data:
            logger.error("Failed to insert business_hours: %s", bh_result)
            sys.exit(1)
        logger.info("business_hours inserted")

    # ── 4. FAQ entries — inline plumbing pack ─────────────────────────────────
    existing_faqs = (
        db.table("faq_entries")
        .select("question")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    existing_questions = {
        row["question"].strip().lower() for row in (existing_faqs.data or [])
    }
    logger.info("Tenant has %d existing FAQ entries", len(existing_questions))

    inserted_faqs = 0
    skipped_faqs = 0
    for faq in FAQ_ENTRIES:
        if faq["question"].strip().lower() in existing_questions:
            skipped_faqs += 1
            continue
        faq_result = (
            db.table("faq_entries")
            .insert({
                "tenant_id": tenant_id,
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "is_active": True,
            })
            .execute()
        )
        if not faq_result.data:
            logger.warning("Failed to insert FAQ: %s", faq["question"])
        else:
            inserted_faqs += 1

    logger.info("FAQ entries: %d inserted, %d skipped", inserted_faqs, skipped_faqs)

    # ── 4b. Layer on canonical industry FAQ pack via service ──────────────────
    # industry_faqs.seed_industry_faqs uses its own db handle; skip on re-run
    # by checking whether the canonical "What services do you offer?" is present.
    INDUSTRY_SENTINEL = "what services do you offer?"
    if INDUSTRY_SENTINEL not in existing_questions:
        try:
            from backend.services.industry_faqs import seed_industry_faqs
            seed_industry_faqs(
                tenant_id=tenant_id,
                industry="plumbing",
                business_name=DEMO_BUSINESS_NAME,
                city=DEMO_CITY,
            )
            logger.info("industry_faqs.seed_industry_faqs completed")
        except Exception:
            logger.warning(
                "industry_faqs.seed_industry_faqs failed (non-fatal)", exc_info=True
            )
    else:
        logger.info("Industry FAQ sentinel already present — SKIP seed_industry_faqs")

    # ── 5. Leads — 12 plumbing leads in varied statuses ──────────────────────
    # leads uses client_id (NOT tenant_id), status (NOT lead_stage),
    # areas_of_interest (NOT service_interest).

    existing_leads_res = (
        db.table("leads")
        .select("id, email")
        .eq("client_id", tenant_id)
        .execute()
    )
    existing_lead_emails = {
        row["email"] for row in (existing_leads_res.data or []) if row.get("email")
    }
    existing_lead_ids = [row["id"] for row in (existing_leads_res.data or [])]

    inserted_leads = 0
    skipped_leads = 0
    new_lead_ids: list[str] = []

    for lead in LEADS:
        if lead["email"] in existing_lead_emails:
            skipped_leads += 1
            continue
        lead_row = {
            "client_id": tenant_id,   # leads use client_id, not tenant_id
            "name": lead["name"],
            "email": lead["email"],
            "phone": lead["phone"],
            "areas_of_interest": lead["areas_of_interest"],
            "status": lead["status"],
            "lead_score": lead["lead_score"],
            "source": lead["source"],
            "notes": lead["notes"],
            "created_at": lead["created_at"],
        }
        lr = db.table("leads").insert(lead_row).execute()
        if not lr.data:
            logger.warning("Failed to insert lead: %s", lead["email"])
        else:
            new_lead_ids.append(lr.data[0]["id"])
            inserted_leads += 1

    logger.info("Leads: %d inserted, %d skipped", inserted_leads, skipped_leads)

    # Merge newly inserted IDs with any pre-existing ones for FK references
    all_lead_ids = new_lead_ids + existing_lead_ids

    # ── 6. Appointments (3) ───────────────────────────────────────────────────
    # appointments uses tenant_id (standard)

    existing_appts = (
        db.table("appointments")
        .select("id")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if existing_appts.data:
        logger.info(
            "appointments already exist (%d rows) — SKIP insert",
            len(existing_appts.data),
        )
    else:
        appointments = _build_appointments(all_lead_ids)
        inserted_appts = 0
        for appt in appointments:
            appt_row = {"tenant_id": tenant_id, **appt}
            ar = db.table("appointments").insert(appt_row).execute()
            if not ar.data:
                logger.warning(
                    "Failed to insert appointment: %s", appt["customer_name"]
                )
            else:
                inserted_appts += 1
        logger.info("Appointments: %d inserted", inserted_appts)

    # ── 7. Invoices (3 — draft, sent, paid) ──────────────────────────────────
    # invoices uses tenant_id (standard); invoice_number is unique per tenant

    existing_inv = (
        db.table("invoices")
        .select("invoice_number")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    existing_invoice_numbers = {
        row["invoice_number"] for row in (existing_inv.data or [])
    }

    invoices = _build_invoices(all_lead_ids)
    inserted_invs = 0
    skipped_invs = 0
    for inv in invoices:
        if inv["invoice_number"] in existing_invoice_numbers:
            skipped_invs += 1
            continue
        inv_row = {"tenant_id": tenant_id, **inv}
        ivr = db.table("invoices").insert(inv_row).execute()
        if not ivr.data:
            logger.warning("Failed to insert invoice: %s", inv["invoice_number"])
        else:
            inserted_invs += 1

    logger.info("Invoices: %d inserted, %d skipped", inserted_invs, skipped_invs)

    # ── 8. Agent OS — missed-call voice recovery thread ──────────────────────
    # os_threads, os_messages, os_agent_runs all use client_id.
    # Mirrors the shape created by voice_recovery.create_missed_call_followup.

    # Check by thread title to stay idempotent
    existing_threads = (
        tenant_table(db, "os_threads", tenant_id)
        .select("id, title")
        .execute()
    )
    thread_titles = {row["title"] for row in (existing_threads.data or [])}
    thread_title = f"Missed call from {MISSED_CALL_CALLER}"

    if thread_title in thread_titles:
        logger.info("os_threads voice recovery row already exists — SKIP")
    else:
        # 8a. os_threads
        thread_id: str | None = None
        try:
            tr = (
                tenant_table(db, "os_threads", tenant_id)
                .insert({
                    "title": thread_title,
                    "source": "voice",
                    "status": "open",
                    "created_by": "system",
                })
                .execute()
            )
            thread_id = tr.data[0]["id"] if tr.data else None
        except Exception:
            logger.warning(
                "os_threads insert failed (non-fatal)", exc_info=True
            )

        # 8b. os_messages — inbound voicemail summary
        if thread_id:
            try:
                excerpt = MISSED_CALL_TRANSCRIPT_EXCERPT[:400]
                content = f"Voicemail from {MISSED_CALL_CALLER}."
                content += f"\n\nSummary: {MISSED_CALL_SUMMARY}"
                content += f'\n\nThey said: "{excerpt}"'
                tenant_table(db, "os_messages", tenant_id).insert({
                    "thread_id": thread_id,
                    "role": "user",
                    "content": content,
                    "inbound_kind": "voicemail",
                    "source_ref": "demo-call-001",
                }).execute()
                logger.info("os_messages voicemail row inserted")
            except Exception:
                logger.warning(
                    "os_messages insert failed (non-fatal)", exc_info=True
                )

        # 8c. os_agent_runs — pending sms.send deliverable
        # deliverable shape mirrors voice_recovery.create_missed_call_followup
        try:
            sms_body = _build_callback_sms(
                DEMO_BUSINESS_NAME, MISSED_CALL_SUMMARY, MISSED_CALL_CALLER
            )
            deliverable = {
                "title": f"Text back {MISSED_CALL_CALLER} about their voicemail",
                "body": f"{sms_body}\n\nRecipient: {MISSED_CALL_CALLER}",
                "channel": "sms",
                "metadata": {
                    "recipient": MISSED_CALL_CALLER,
                    "call_id": "demo-call-001",
                    "lead_id": all_lead_ids[0] if all_lead_ids else None,
                    "source": "missed_call_recovery",
                },
            }
            run_row = {
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
            }
            if thread_id:
                run_row["thread_id"] = thread_id

            rr = (
                tenant_table(db, "os_agent_runs", tenant_id)
                .insert(run_row)
                .execute()
            )
            run_id = rr.data[0]["id"] if rr.data else None
            logger.info("os_agent_runs voice recovery row inserted — id=%s", run_id)
        except Exception:
            logger.warning(
                "os_agent_runs insert failed (non-fatal)", exc_info=True
            )

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("DEMO SEED COMPLETE — Plumbing Vertical")
    logger.info("  tenant_id   : %s", tenant_id)
    logger.info("  api_key     : %s", api_key)
    logger.info("  plan        : professional")
    logger.info("  business    : %s", DEMO_BUSINESS_NAME)
    logger.info("  email       : %s", DEMO_OWNER_EMAIL)
    logger.info("  Supabase    : %s", supabase_url)
    logger.info("")
    logger.info("Embed snippet:")
    logger.info(
        '  <script src="http://localhost:8000/widget/agentnexlify-widget.js"'
        ' data-api-key="%s"'
        ' data-api-base="http://localhost:8000"'
        ' data-brand-color="#1565C0"></script>',
        api_key,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
