"""Demo tenant seeding service for the public live-demo sandbox.

Exposes two public functions:

    ensure_demo_tenant(db) -> str | None
        Find the tenant with is_demo=True; if none exists, seed the full
        plumbing demo and return the tenant_id. Idempotent. Never raises.

    reset_demo_tenant(db, tenant_id) -> dict
        Delete volatile rows for the demo tenant and re-seed them so the
        sandbox looks fresh. Hard-asserts is_demo=True before deleting
        anything. Returns a counts summary dict.

PRODUCTION-URL guard: intentionally absent from this service.
The service is designed to run in production for the live-demo sandbox.
It may only operate on the tenant whose is_demo flag is True.

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
# Demo tenant constants (mirrors seed_plumbing_demo.py)
# ---------------------------------------------------------------------------

_DEMO_OWNER_EMAIL = "demo-plumbing@agentnexlify-demo.local"
_DEMO_BUSINESS_NAME = "Reliable Plumbing Co. (DEMO)"
_DEMO_PHONE = "555-321-7700"
_DEMO_CITY = "Riverside"

_GREETING_MESSAGE = (
    "Hi! I'm Pat, the virtual assistant for Reliable Plumbing Co. "
    "I can answer questions about our services, pricing, and availability — "
    "or help you get a free estimate. Got a leak, clogged drain, or water "
    "heater issue? Tell me what's going on and I'll help you right away."
)

_BUSINESS_HOURS = {
    "monday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "tuesday":   {"enabled": True,  "start": "07:00", "end": "18:00"},
    "wednesday": {"enabled": True,  "start": "07:00", "end": "18:00"},
    "thursday":  {"enabled": True,  "start": "07:00", "end": "18:00"},
    "friday":    {"enabled": True,  "start": "07:00", "end": "18:00"},
    "saturday":  {"enabled": True,  "start": "08:00", "end": "16:00"},
    "sunday":    {"enabled": False, "start": "09:00", "end": "17:00"},
}

_FAQ_ENTRIES = [
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

_MISSED_CALL_CALLER = "+15551234567"
_MISSED_CALL_SUMMARY = (
    "Caller says they have a slow drain in their kitchen and a dripping faucet "
    "in the master bathroom. Looking for a quote, not an emergency."
)
_MISSED_CALL_TRANSCRIPT = (
    "Yeah, so uh, the kitchen sink has been draining really slowly for like "
    "a week now. And also our master bath faucet has been dripping non-stop. "
    "Just wondering if someone could come out and take a look. Thanks."
)

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


def _leads_data() -> list[dict]:
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


def _build_appointments(lead_ids: list[str]) -> list[dict]:
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


def _build_invoices(lead_ids: list[str]) -> list[dict]:
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
# Public API
# ---------------------------------------------------------------------------

def ensure_demo_tenant(db: Any) -> str | None:
    """Find the is_demo tenant; create it if absent. Always returns tenant_id.

    Idempotent — safe to call multiple times. Never raises; logs errors and
    returns None on unrecoverable failure.
    """
    # 1. Check for existing demo tenant
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
            logger.info("ensure_demo_tenant: found existing demo tenant id=%s", tenant_id)
            return tenant_id
    except Exception:
        logger.exception("ensure_demo_tenant: failed to query for existing demo tenant")
        return None

    # 2. Create the demo tenant
    logger.info("ensure_demo_tenant: no demo tenant found — seeding plumbing demo")
    return _seed_demo_tenant(db)


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
            .select("id, is_demo")
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

    deleted: dict[str, int] = {}

    # 3. Delete volatile rows in dependency order
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

    # 4. Re-seed volatile data
    seeded = _seed_volatile(db, tenant_id)

    summary = {"deleted": deleted, "seeded": seeded}
    logger.info("reset_demo_tenant: complete for tenant_id=%s summary=%s", tenant_id, summary)
    return summary


# ---------------------------------------------------------------------------
# Internal seeding logic
# ---------------------------------------------------------------------------

def _seed_demo_tenant(db: Any) -> str | None:
    """Create the full plumbing demo tenant and all sub-rows. Returns tenant_id or None."""
    tenant_id: str | None = None

    # 1. Tenant row
    try:
        result = (
            db.table("tenants")
            .insert({
                "business_name": _DEMO_BUSINESS_NAME,
                "business_type": "plumbing",
                "owner_email": _DEMO_OWNER_EMAIL,
                "phone": _DEMO_PHONE,
                "city": _DEMO_CITY,
                "plan": "professional",
                "plan_status": "active",
                "is_demo": True,
            })
            .execute()
        )
        if not result.data:
            logger.error("_seed_demo_tenant: tenant insert returned no data")
            return None
        tenant_id = result.data[0]["id"]
        logger.info("_seed_demo_tenant: tenant inserted id=%s", tenant_id)
    except Exception:
        logger.exception("_seed_demo_tenant: tenant insert failed")
        return None

    # 2. Widget config
    try:
        db.table("widget_configs").insert({
            "tenant_id": tenant_id,
            "bot_name": "Pat",
            "primary_color": "#1565C0",
            "greeting_message": _GREETING_MESSAGE,
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
        }).execute()
        logger.info("_seed_demo_tenant: widget_config inserted")
    except Exception:
        logger.exception("_seed_demo_tenant: widget_config insert failed (non-fatal)")

    # 3. Business hours
    try:
        db.table("business_hours").insert({
            "tenant_id": tenant_id,
            "timezone": "America/Los_Angeles",
            "hours": json.dumps(_BUSINESS_HOURS),
            "slot_duration_minutes": 90,
            "buffer_minutes": 30,
            "max_advance_days": 14,
        }).execute()
        logger.info("_seed_demo_tenant: business_hours inserted")
    except Exception:
        logger.exception("_seed_demo_tenant: business_hours insert failed (non-fatal)")

    # 4. FAQ entries
    inserted_faqs = 0
    for faq in _FAQ_ENTRIES:
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
                "_seed_demo_tenant: FAQ insert failed for '%s'", faq["question"],
                exc_info=True,
            )
    logger.info("_seed_demo_tenant: %d FAQ entries inserted", inserted_faqs)

    # 4b. Industry FAQ pack (optional)
    try:
        from backend.services.industry_faqs import seed_industry_faqs
        seed_industry_faqs(
            tenant_id=tenant_id,
            industry="plumbing",
            business_name=_DEMO_BUSINESS_NAME,
            city=_DEMO_CITY,
        )
        logger.info("_seed_demo_tenant: industry_faqs seeded")
    except Exception:
        logger.warning("_seed_demo_tenant: industry_faqs failed (non-fatal)", exc_info=True)

    # 5-8. Volatile rows
    _seed_volatile(db, tenant_id)

    return tenant_id


def _seed_volatile(db: Any, tenant_id: str) -> dict:
    """Seed the volatile demo rows: leads, appointments, invoices, Agent OS thread.

    Returns counts of rows inserted per entity type.
    """
    seeded: dict[str, int] = {
        "leads": 0,
        "appointments": 0,
        "invoices": 0,
        "os_thread": 0,
    }

    # 5. Leads — use client_id
    lead_ids: list[str] = []
    for lead in _leads_data():
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
    for appt in _build_appointments(lead_ids):
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
    for inv in _build_invoices(lead_ids):
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
    thread_id: str | None = None
    try:
        tr = (
            tenant_table(db, "os_threads", tenant_id)
            .insert({
                "title": f"Missed call from {_MISSED_CALL_CALLER}",
                "source": "voice",
                "status": "open",
                "created_by": "system",
            })
            .execute()
        )
        thread_id = tr.data[0]["id"] if tr.data else None
        if thread_id:
            seeded["os_thread"] += 1
            logger.info("_seed_volatile: os_threads inserted id=%s", thread_id)
    except Exception:
        logger.exception("_seed_volatile: os_threads insert failed (non-fatal)")

    if thread_id:
        try:
            content = f"Voicemail from {_MISSED_CALL_CALLER}."
            content += f"\n\nSummary: {_MISSED_CALL_SUMMARY}"
            content += f'\n\nThey said: "{_MISSED_CALL_TRANSCRIPT[:400]}"'
            tenant_table(db, "os_messages", tenant_id).insert({
                "thread_id": thread_id,
                "role": "user",
                "content": content,
                "inbound_kind": "voicemail",
                "source_ref": "demo-call-001",
            }).execute()
            logger.info("_seed_volatile: os_messages inserted")
        except Exception:
            logger.exception("_seed_volatile: os_messages insert failed (non-fatal)")

        try:
            sms_body = _build_callback_sms(_DEMO_BUSINESS_NAME, _MISSED_CALL_SUMMARY)
            deliverable = {
                "title": f"Text back {_MISSED_CALL_CALLER} about their voicemail",
                "body": f"{sms_body}\n\nRecipient: {_MISSED_CALL_CALLER}",
                "channel": "sms",
                "metadata": {
                    "recipient": _MISSED_CALL_CALLER,
                    "call_id": "demo-call-001",
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
            logger.info("_seed_volatile: os_agent_runs inserted")
        except Exception:
            logger.exception("_seed_volatile: os_agent_runs insert failed (non-fatal)")

    logger.info(
        "_seed_volatile: seeded for tenant_id=%s: %s", tenant_id, seeded
    )
    return seeded
