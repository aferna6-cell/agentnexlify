"""Automation trigger — sequence enrollment entry point."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50

VALID_TRIGGER_EVENTS = {
    "new_lead",
    "lead_stage_change",
    "no_response_24h",
    "appointment_completed",
}


async def trigger_sequence(
    tenant_id: str,
    lead_id: str,
    trigger_event: str,
    trigger_context: dict[str, Any] | None = None,
) -> int:
    """Find matching active sequences and enroll the lead. Returns count of enrollments created."""
    db = get_service_supabase()
    trigger_context = trigger_context or {}

    # Find active sequences for this trigger event
    result = (
        tenant_table(db, "automation_sequences", tenant_id)
        .select("id, trigger_config")
        .eq("trigger_event", trigger_event)
        .eq("is_active", True)
        .execute()
    )

    sequences = result.data or []
    if not sequences:
        return 0

    # Filter sequences by trigger_context before fetching steps
    eligible_seqs = []
    for seq in sequences:
        if trigger_event == "lead_stage_change":
            target = (seq.get("trigger_config") or {}).get("target_stage")
            if target and target != trigger_context.get("new_stage"):
                continue
        eligible_seqs.append(seq)

    if not eligible_seqs:
        return 0

    # Batch-fetch the first active step for all eligible sequences in one query.
    # We fetch step_order + sequence_id so we can group in Python; limit to
    # len(eligible_seqs) rows because we only need one row per sequence and
    # Supabase returns them in step_order order.
    seq_ids = [s["id"] for s in eligible_seqs]
    steps_result = (
        db.table("automation_steps")
        .select("sequence_id, step_order, delay_minutes")
        .in_("sequence_id", seq_ids)
        .eq("is_active", True)
        .order("step_order")
        .limit(len(seq_ids) * 20)  # generous upper bound; deduped in Python below
        .execute()
    )
    # Build mapping sequence_id -> first step (lowest step_order)
    first_step_by_seq: dict[str, dict] = {}
    for step in steps_result.data or []:
        sid = step["sequence_id"]
        if sid not in first_step_by_seq:
            first_step_by_seq[sid] = step

    enrolled = 0
    for seq in eligible_seqs:
        first_step = first_step_by_seq.get(seq["id"])
        if not first_step:
            continue

        delay = first_step["delay_minutes"]
        next_run = datetime.now(timezone.utc) + timedelta(minutes=delay)

        try:
            tenant_table(db, "automation_executions", tenant_id).insert(
                {
                    "sequence_id": seq["id"],
                    "lead_id": lead_id,
                    "tenant_id": tenant_id,
                    "current_step": 1,
                    "status": "in_progress",
                    "next_run_at": next_run.isoformat(),
                }
            ).execute()
            enrolled += 1
            logger.info(
                "Enrolled lead %s in sequence %s (trigger: %s)",
                lead_id,
                seq["id"],
                trigger_event,
            )
        except Exception as _enroll_exc:
            # UNIQUE constraint = already enrolled (expected). Other errors = real problems.
            err_str = str(_enroll_exc).lower()
            if "unique" in err_str or "duplicate" in err_str:
                logger.debug("Lead %s already enrolled in sequence %s", lead_id, seq["id"])
            else:
                logger.warning("Failed to enroll lead %s in sequence %s: %s", lead_id, seq["id"], _enroll_exc, exc_info=True)

    return enrolled
