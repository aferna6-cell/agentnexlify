"""Seed a local-only demo tenant for the power washing prospect meeting.

Creates:
  - tenants row (plan=professional, business_type='other')
  - widget_configs row (api_key, bot_name, knowledge_base, greeting)
  - business_hours row (Mon-Sat 7 AM - 6 PM)
  - 10 faq_entries covering the most common power washing questions

SAFETY: Aborts immediately if SUPABASE_URL points at the production database.

Usage (from project root):
    python scripts/demos/seed_powerwash_demo.py

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in environment or .env file.
Idempotent: re-running will SKIP rows that already exist (matched by owner_email).
"""

import json
import sys
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
DEMO_OWNER_EMAIL = "demo-powerwash@agentnexlify-demo.local"
DEMO_BUSINESS_NAME = "Clean Slate Power Washing (DEMO)"
DEMO_PHONE = "555-867-5309"
DEMO_CITY = "Springfield"

KB_PATH = project_root / "widget" / "knowledge-bases" / "powerwash-demo_kb.md"

KNOWLEDGE_BASE_TEXT = KB_PATH.read_text(encoding="utf-8") if KB_PATH.exists() else (
    "Power washing demo KB — file not found. "
    "Expected at widget/knowledge-bases/powerwash-demo_kb.md"
)

GREETING_MESSAGE = (
    "Hi! I'm Wade, the virtual assistant for Clean Slate Power Washing. "
    "I can answer questions about our services, pricing, and availability — "
    "or help you request a free estimate. What can I help you with today?"
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
        "question": "How much does power washing cost?",
        "answer": (
            "Pricing depends on the size of the area, the type of surface, and the level "
            "of buildup. A typical house wash ranges from $250 to $500 and a standard "
            "two-car driveway is usually $100 to $200. These are sample ranges — we "
            "provide a free estimate tailored to your specific job. What would you like "
            "to have cleaned?"
        ),
        "category": "Pricing",
    },
    {
        "question": "What surfaces do you clean?",
        "answer": (
            "We clean most exterior surfaces: vinyl, brick, stucco, and wood siding; "
            "concrete, paver, and asphalt driveways; wood and composite decks; patios; "
            "roofs (shingle, tile, and metal); fences; gutters; and commercial buildings. "
            "We use the right method for each surface automatically."
        ),
        "category": "Services",
    },
    {
        "question": "Do you use chemicals? Is it safe for my plants and pets?",
        "answer": (
            "Yes, we use biodegradable, SDS-compliant detergents that are safe for "
            "plants, pets, and children. For house and roof washing we use a soft wash "
            "method with a low-concentration sodium hypochlorite-based solution. We "
            "pre-wet and rinse all surrounding landscaping before and after the job."
        ),
        "category": "Services",
    },
    {
        "question": "How long does it take to power wash my house or driveway?",
        "answer": (
            "Most residential jobs take 1 to 3 hours. A house wash is typically 1 to 2 "
            "hours; a driveway takes about 30 to 60 minutes. Larger jobs or heavy "
            "staining take longer. We give you a time estimate when we provide your quote."
        ),
        "category": "Services",
    },
    {
        "question": "Do I need to be home during the service?",
        "answer": (
            "No — as long as we have access to the areas being cleaned and an outdoor "
            "water spigot. We coordinate access details beforehand and send before-and-"
            "after photos when the job is complete. Many customers simply leave access "
            "and check back when we are done."
        ),
        "category": "Scheduling",
    },
    {
        "question": "What area do you serve?",
        "answer": (
            "We serve Springfield and surrounding areas within approximately 25 miles. "
            "Contact us for jobs outside this area — we may still be able to help "
            "depending on the job size."
        ),
        "category": "Service Area",
    },
    {
        "question": "How do I get a free estimate?",
        "answer": (
            "Request one right here in chat — just tell us your name, what you need "
            "cleaned, and the best way to reach you. We typically respond with a quote "
            "the same business day. No commitment required."
        ),
        "category": "Booking",
    },
    {
        "question": "Do you offer recurring or maintenance service?",
        "answer": (
            "Yes. We offer monthly, quarterly, and annual maintenance plans at discounted "
            "rates. Most residential customers do a full house wash and driveway cleaning "
            "once or twice a year. Ask us about maintenance pricing when you get your "
            "estimate."
        ),
        "category": "Services",
    },
    {
        "question": "Are you insured and licensed?",
        "answer": (
            "Yes — we are fully insured with general liability coverage and carry workers "
            "compensation for all crew members. We are licensed and in good standing. "
            "We are happy to provide a certificate of insurance on request, which is "
            "standard for commercial and property management clients."
        ),
        "category": "Trust",
    },
    {
        "question": "What is the difference between pressure washing and soft washing?",
        "answer": (
            "Pressure washing uses high-pressure water — best for hard surfaces like "
            "concrete, brick, and pavers. Soft washing uses low-pressure water combined "
            "with professional cleaning solutions — the right choice for roofs, siding, "
            "and any surface where high pressure could cause damage. We choose the "
            "correct method for each surface automatically."
        ),
        "category": "Services",
    },
]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # --- imports (deferred so project_root is on sys.path first) ---
    try:
        from backend.config import settings
        from backend.models.database import get_supabase
    except ImportError as exc:
        logger.error("Import failed: %s — run from project root with venv active", exc)
        sys.exit(1)

    # --- PROD GUARD ---
    supabase_url = (settings.supabase_url or "").rstrip("/")
    if supabase_url == PROD_URL.rstrip("/"):
        logger.error(
            "ABORT: SUPABASE_URL points at the production database (%s). "
            "This script must only run against a LOCAL Supabase instance. "
            "Set SUPABASE_URL to your local Supabase URL (e.g. http://localhost:54321) "
            "and re-run.",
            supabase_url,
        )
        sys.exit(1)

    if not supabase_url or not settings.supabase_service_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    logger.info("Targeting Supabase at: %s (NOT production — safe to proceed)", supabase_url)

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
                "business_type": "other",
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
    existing_wc = (
        db.table("widget_configs")
        .select("id, api_key")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if existing_wc.data:
        api_key = existing_wc.data[0]["api_key"]
        logger.info("widget_config already exists — api_key=%s  SKIP insert", api_key)
    else:
        wc_result = (
            db.table("widget_configs")
            .insert({
                "tenant_id": tenant_id,
                "bot_name": "Wade",
                "primary_color": "#1E90FF",
                "greeting_message": GREETING_MESSAGE,
                "position": "bottom-right",
                "collect_name": True,
                "collect_email": True,
                "collect_phone": True,
                "show_watermark": False,
                "knowledge_base": KNOWLEDGE_BASE_TEXT,
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
                "timezone": "America/New_York",
                "hours": BUSINESS_HOURS,  # dict straight into jsonb - json.dumps double-encoded it (GH #422)
                "slot_duration_minutes": 60,
                "buffer_minutes": 15,
                "max_advance_days": 14,
            })
            .execute()
        )
        if not bh_result.data:
            logger.error("Failed to insert business_hours: %s", bh_result)
            sys.exit(1)
        logger.info("business_hours inserted")

    # ── 4. FAQ entries ────────────────────────────────────────────────────────
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

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("DEMO SEED COMPLETE")
    logger.info("  tenant_id : %s", tenant_id)
    logger.info("  api_key   : %s", api_key)
    logger.info("  plan      : professional")
    logger.info("  email     : %s", DEMO_OWNER_EMAIL)
    logger.info("  Supabase  : %s", supabase_url)
    logger.info("")
    logger.info("Embed snippet:")
    logger.info(
        '  <script src="http://localhost:8000/widget/agentnexlify-widget.js"'
        ' data-api-key="%s"'
        ' data-api-base="http://localhost:8000"'
        ' data-brand-color="#1E90FF"></script>',
        api_key,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
