"""Add trial and promo FAQ entries to the MTOptions tenant chatbot.

Adds 3 FAQ entries so the bot correctly answers questions about:
  - Standard 10-day free trial
  - Promotional 30- or 60-day extended trials
  - How to apply a promo code at registration

Idempotent: skips any entry whose question already exists for this tenant.

Usage:
    python scripts/seed_mtoptions_faq_trial.py

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in environment or .env file.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TRIAL_FAQS = [
    {
        "question": "How long is the free trial?",
        "answer": (
            "Our standard free trial is 10 days — no credit card required. "
            "You get full access to the platform during the trial so you can "
            "see exactly how it works for your business."
        ),
        "category": "Pricing & Trials",
    },
    {
        "question": "Do you offer extended trials or promotional periods?",
        "answer": (
            "Yes! We occasionally run promotions that extend the trial to 30 or 60 days. "
            "If you have a promo code, enter it in the promo field during registration "
            "to automatically activate your extended trial."
        ),
        "category": "Pricing & Trials",
    },
    {
        "question": "How do I use a promo code?",
        "answer": (
            "When you sign up, you'll see a promo code field on the registration page. "
            "Enter your code there before completing registration and your extended trial "
            "or discount will be applied automatically. "
            "If you already signed up and forgot to enter a code, email us at "
            "support@agentnexlify.com and we'll apply it manually."
        ),
        "category": "Pricing & Trials",
    },
]


def main() -> None:
    try:
        from backend.config import settings
        from backend.models.database import get_supabase
    except ImportError as exc:
        logger.error("Import failed: %s — run from the project root", exc)
        sys.exit(1)

    if not settings.supabase_url or not settings.supabase_service_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    db = get_supabase()

    # 1. Find the MTOptions tenant
    tenant_id: str | None = None
    for field, value in [
        ("owner_email", "support@mtoptions.com"),
        ("business_slug", "mtoptions"),
    ]:
        try:
            result = (
                db.table("tenants")
                .select("id, business_name")
                .eq(field, value)
                .limit(1)
                .execute()
            )
            if result.data:
                tenant_id = result.data[0]["id"]
                logger.info(
                    "Found MTOptions tenant: id=%s name=%s",
                    tenant_id,
                    result.data[0].get("business_name"),
                )
                break
        except Exception as exc:
            logger.warning("Could not query by %s: %s", field, exc)

    if not tenant_id:
        logger.error(
            "MTOptions tenant not found. "
            "Tried owner_email='support@mtoptions.com' and business_slug='mtoptions'."
        )
        sys.exit(1)

    # 2. Load existing FAQ questions to avoid duplicates
    existing_questions: set[str] = set()
    try:
        existing = (
            db.table("faq_entries")
            .select("question")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        existing_questions = {
            row["question"].strip().lower() for row in (existing.data or [])
        }
        logger.info("Tenant has %d existing FAQ entries", len(existing_questions))
    except Exception as exc:
        logger.warning("Could not load existing FAQs: %s", exc)

    # 3. Insert new entries (skip duplicates)
    inserted = 0
    skipped = 0
    for faq in TRIAL_FAQS:
        if faq["question"].strip().lower() in existing_questions:
            logger.info("SKIP (already exists): %s", faq["question"])
            skipped += 1
            continue
        try:
            db.table("faq_entries").insert(
                {
                    "tenant_id": tenant_id,
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "category": faq["category"],
                    "is_active": True,
                }
            ).execute()
            logger.info("INSERTED: %s", faq["question"])
            inserted += 1
        except Exception as exc:
            logger.error("Failed to insert FAQ '%s': %s", faq["question"], exc)

    logger.info("Done. %d inserted, %d skipped (already existed).", inserted, skipped)


if __name__ == "__main__":
    main()
