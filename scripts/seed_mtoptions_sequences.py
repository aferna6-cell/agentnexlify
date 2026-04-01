"""Seed the MTOptions Welcome Sequence in email_sequences.

Looks up the MTOptions tenant by owner_email or business_slug,
then queries existing marketing_campaigns for the welcome content.
Falls back to placeholder content if campaigns are not found locally.

Usage:
    python scripts/seed_mtoptions_sequences.py

Requires that SUPABASE_URL and SUPABASE_SERVICE_KEY are set in the
environment (or in a .env file at the project root).
"""

import os
import sys
from pathlib import Path

# Add the project root to sys.path so backend.config is importable
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        from backend.config import settings
        from backend.models.database import get_supabase
    except ImportError as exc:
        logger.error("Import failed: %s — run from the project root", exc)
        sys.exit(1)

    if not settings.supabase_url or not settings.supabase_service_key:
        logger.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set. "
            "Check your .env file."
        )
        sys.exit(1)

    db = get_supabase()

    # ------------------------------------------------------------------
    # 1. Find the MTOptions tenant
    # ------------------------------------------------------------------
    tenant_id: str | None = None

    for field, value in [("owner_email", "support@mtoptions.com"), ("business_slug", "mtoptions")]:
        try:
            result = (
                db.table("tenants")
                .select("id, business_name, owner_email")
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
            "MTOptions tenant not found by owner_email='support@mtoptions.com' "
            "or business_slug='mtoptions'. Cannot proceed."
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Try to load existing campaign content for the 4 welcome steps
    # ------------------------------------------------------------------
    campaign_bodies: list[dict] = []
    try:
        campaigns_result = (
            db.table("marketing_campaigns")
            .select("name, subject, body, type")
            .eq("tenant_id", tenant_id)
            .order("created_at")
            .limit(10)
            .execute()
        )
        campaign_bodies = campaigns_result.data or []
        logger.info("Found %d existing campaigns for MTOptions", len(campaign_bodies))
    except Exception as exc:
        logger.warning("Could not query marketing_campaigns: %s", exc)

    # ------------------------------------------------------------------
    # 3. Build the 4 steps — use campaign content if available
    # ------------------------------------------------------------------
    PLACEHOLDER_STEPS = [
        {
            "step_order": 1,
            "delay_days": 0,
            "delay_hours": 0,
            "subject": "Welcome to MTOptions — Let's Get Started",
            "body": (
                "<p>Hi {{name}},</p>"
                "<p>Welcome! We're excited to have you on board. "
                "Our team is here to help you navigate your options.</p>"
                "<p>Reply to this email if you have any questions.</p>"
                "<p>— The MTOptions Team</p>"
            ),
            "email_type": "email",
            "is_active": True,
        },
        {
            "step_order": 2,
            "delay_days": 2,
            "delay_hours": 0,
            "subject": "Your Options Snapshot — Day 2 Follow-Up",
            "body": (
                "<p>Hi {{name}},</p>"
                "<p>Just checking in! Here's a quick overview of what we can offer you. "
                "Have you had a chance to review the information we sent?</p>"
                "<p>We'd love to schedule a quick call — reply to book a time.</p>"
                "<p>— The MTOptions Team</p>"
            ),
            "email_type": "email",
            "is_active": True,
        },
        {
            "step_order": 3,
            "delay_days": 4,
            "delay_hours": 0,
            "subject": "Common Questions We Hear — MTOptions",
            "body": (
                "<p>Hi {{name}},</p>"
                "<p>We get a lot of questions, so we put together answers to the most common ones.</p>"
                "<p>If you have a question not covered here, just reply and we'll get back to you within 24 hours.</p>"
                "<p>— The MTOptions Team</p>"
            ),
            "email_type": "email",
            "is_active": True,
        },
        {
            "step_order": 4,
            "delay_days": 7,
            "delay_hours": 0,
            "subject": "Ready to Move Forward? — MTOptions",
            "body": (
                "<p>Hi {{name}},</p>"
                "<p>It's been a week since you first reached out. We want to make sure you have "
                "everything you need to make a confident decision.</p>"
                "<p>Our team is ready to help. Reply or book a call anytime.</p>"
                "<p>— The MTOptions Team</p>"
            ),
            "email_type": "email",
            "is_active": True,
        },
    ]

    # Override placeholder content with real campaign data where available
    steps_to_insert = list(PLACEHOLDER_STEPS)
    for i, step in enumerate(steps_to_insert):
        if i < len(campaign_bodies):
            campaign = campaign_bodies[i]
            if campaign.get("subject"):
                step["subject"] = campaign["subject"]
            if campaign.get("body"):
                step["body"] = campaign["body"]
            logger.info(
                "Step %d: using campaign content from '%s'",
                step["step_order"],
                campaign.get("name", "unknown"),
            )
        else:
            logger.info("Step %d: using placeholder content", step["step_order"])

    # ------------------------------------------------------------------
    # 4. Check if the welcome sequence already exists (idempotent)
    # ------------------------------------------------------------------
    try:
        existing_check = (
            db.table("email_sequences")
            .select("id, name")
            .eq("tenant_id", tenant_id)
            .eq("name", "MTOptions Welcome Sequence")
            .limit(1)
            .execute()
        )
        if existing_check.data:
            existing_id = existing_check.data[0]["id"]
            logger.warning(
                "MTOptions Welcome Sequence already exists (id=%s). "
                "Delete it first to re-seed, or update it via the dashboard.",
                existing_id,
            )
            sys.exit(0)
    except Exception as exc:
        logger.warning("Could not check for existing sequence: %s", exc)

    # ------------------------------------------------------------------
    # 5. Create the sequence
    # ------------------------------------------------------------------
    try:
        seq_result = (
            db.table("email_sequences")
            .insert({
                "tenant_id": tenant_id,
                "name": "MTOptions Welcome Sequence",
                "trigger_type": "lead_captured",
                "trigger_config": {},
                "is_active": True,
            })
            .execute()
        )
        if not seq_result.data:
            logger.error("INSERT into email_sequences returned no data")
            sys.exit(1)
        sequence_id = seq_result.data[0]["id"]
        logger.info("Created email sequence id=%s", sequence_id)
    except Exception as exc:
        logger.error("Failed to create email sequence: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 6. Insert steps
    # ------------------------------------------------------------------
    for step in steps_to_insert:
        payload = {
            "sequence_id": sequence_id,
            "step_order": step["step_order"],
            "delay_days": step["delay_days"],
            "delay_hours": step["delay_hours"],
            "subject": step["subject"],
            "body": step["body"],
            "email_type": step["email_type"],
            "is_active": step["is_active"],
        }
        try:
            step_result = db.table("email_sequence_steps").insert(payload).execute()
            if step_result.data:
                logger.info(
                    "Created step %d (delay: %dd %dh): '%s'",
                    step["step_order"],
                    step["delay_days"],
                    step["delay_hours"],
                    step["subject"][:60],
                )
            else:
                logger.warning("Step %d INSERT returned no data", step["step_order"])
        except Exception as exc:
            logger.error("Failed to insert step %d: %s", step["step_order"], exc)

    logger.info(
        "Seed complete. MTOptions Welcome Sequence (id=%s) with %d steps created for tenant %s.",
        sequence_id,
        len(steps_to_insert),
        tenant_id,
    )


if __name__ == "__main__":
    main()
