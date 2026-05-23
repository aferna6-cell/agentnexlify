"""Email-sequence enrollment helpers.

Extracted from ``backend/routers/email_sequences.py`` so the enroll path can
be tested independently of FastAPI request handling and so the router stays
under the god-class threshold.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


def enroll_lead_in_sequence(
    db,
    sequence_id: str,
    sequence_steps: list[dict],
    lead_id: str,
    tenant_id: str,
) -> str | None:
    """Enroll a lead in a sequence and schedule all active steps.

    Uses ON CONFLICT DO NOTHING to silently skip duplicate enrollments.
    Returns enrollment_id on success or on duplicate (existing id returned).
    Returns None only on database error.
    """
    now = datetime.now(timezone.utc)

    try:
        enroll_result = (
            db.table("email_sequence_enrollments")
            .upsert(
                {
                    "sequence_id": sequence_id,
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "status": "active",
                    "current_step": 0,
                    "enrolled_at": now.isoformat(),
                },
                on_conflict="sequence_id,lead_id",
                ignore_duplicates=True,
            )
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to upsert enrollment for lead %s in sequence %s",
            lead_id,
            sequence_id,
        )
        return None

    if not enroll_result.data:
        # Conflict — lead already enrolled, fetch existing enrollment id
        try:
            existing = (
                db.table("email_sequence_enrollments")
                .select("id")
                .eq("sequence_id", sequence_id)
                .eq("lead_id", lead_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.info(
                    "Lead %s already enrolled in sequence %s (enrollment %s)",
                    lead_id,
                    sequence_id,
                    existing.data[0]["id"],
                )
                return existing.data[0]["id"]
        except Exception:
            logger.exception(
                "Failed to fetch existing enrollment for lead %s", lead_id
            )
        return None

    enrollment_id = enroll_result.data[0]["id"]

    # Schedule a send record for each active step
    active_steps = [s for s in sequence_steps if s.get("is_active", True)]
    for step in active_steps:
        scheduled_for = now + timedelta(
            days=step.get("delay_days", 0),
            hours=step.get("delay_hours", 0),
        )
        try:
            db.table("email_sequence_sends").insert(
                {
                    "enrollment_id": enrollment_id,
                    "step_id": step["id"],
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "status": "pending",
                    "scheduled_for": scheduled_for.isoformat(),
                }
            ).execute()
        except Exception:
            logger.exception(
                "Failed to schedule send for step %s (enrollment %s)",
                step["id"],
                enrollment_id,
            )

    logger.info(
        "Enrolled lead %s in sequence %s — enrollment %s, %d steps scheduled",
        lead_id,
        sequence_id,
        enrollment_id,
        len(active_steps),
    )
    return enrollment_id


async def enroll_lead_in_sequences(tenant_id: str, lead_id: str) -> None:
    """Enroll a lead in all active 'lead_captured' sequences for this tenant.

    Called from widget_lead.py on new lead creation.
    """
    db = get_service_supabase()
    try:
        sequences_result = (
            db.table("email_sequences")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("trigger_type", "lead_captured")
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to query lead_captured sequences for tenant %s", tenant_id
        )
        return

    sequences = sequences_result.data or []
    if not sequences:
        return

    for seq in sequences:
        sequence_id = seq["id"]
        try:
            steps_result = (
                db.table("email_sequence_steps")
                .select("*")
                .eq("sequence_id", sequence_id)
                .order("step_order")
                .execute()
            )
            steps = steps_result.data or []
            enroll_lead_in_sequence(db, sequence_id, steps, lead_id, tenant_id)
        except Exception:
            logger.exception(
                "Failed to enroll lead %s in sequence %s", lead_id, sequence_id
            )
