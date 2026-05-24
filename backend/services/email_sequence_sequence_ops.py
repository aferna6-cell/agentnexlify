"""Sequence-level DB operations for the email-sequence router.

CRUD helpers around the ``email_sequences`` table. Each helper takes the
Supabase client as a parameter so tests can patch the parent ``get_service_supabase``
and propagate the mock.

These helpers raise ``HTTPException`` directly. Routes stay thin shells.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from backend.services.email_sequence_schemas import SequenceCreate, SequenceUpdate

logger = logging.getLogger(__name__)

__all__ = [
    "list_sequences_for_tenant",
    "create_sequence_for_tenant",
    "get_sequence_for_tenant",
    "update_sequence_for_tenant",
    "soft_delete_sequence",
]


def _enrich_sequence_counts(db: Any, sequences: list[dict]) -> list[dict]:
    """Attach step_count + enrollment_count to each sequence dict."""
    enriched = []
    for seq in sequences:
        seq_id = seq["id"]

        try:
            step_count_res = (
                db.table("email_sequence_steps")
                .select("id", count="exact")
                .eq("sequence_id", seq_id)
                .execute()
            )
            seq["step_count"] = (
                step_count_res.count if step_count_res.count is not None else 0
            )
        except Exception:
            logger.warning(
                "Failed to fetch step count for sequence %s", seq_id, exc_info=True
            )
            seq["step_count"] = 0

        try:
            enroll_count_res = (
                db.table("email_sequence_enrollments")
                .select("id", count="exact")
                .eq("sequence_id", seq_id)
                .execute()
            )
            seq["enrollment_count"] = (
                enroll_count_res.count if enroll_count_res.count is not None else 0
            )
        except Exception:
            logger.warning(
                "Failed to fetch enrollment count for sequence %s",
                seq_id,
                exc_info=True,
            )
            seq["enrollment_count"] = 0

        enriched.append(seq)
    return enriched


def list_sequences_for_tenant(db: Any, tenant_id: str) -> dict:
    """Return all sequences for tenant, enriched with step + enrollment counts."""
    try:
        result = (
            db.table("email_sequences")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        sequences = result.data or []
    except Exception:
        logger.exception("Failed to list email sequences for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list sequences")

    enriched = _enrich_sequence_counts(db, sequences)
    return {"sequences": enriched, "total": len(enriched)}


def create_sequence_for_tenant(
    db: Any, tenant_id: str, req: SequenceCreate
) -> dict:
    """Create a new sequence for tenant, optionally inserting initial steps."""
    try:
        seq_result = (
            db.table("email_sequences")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "name": req.name,
                    "trigger_type": req.trigger_type,
                    "trigger_config": req.trigger_config,
                    "is_active": req.is_active,
                }
            )
            .execute()
        )
        if not seq_result.data:
            raise HTTPException(status_code=500, detail="Failed to create sequence")
        sequence = seq_result.data[0]
        sequence_id = sequence["id"]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create email sequence for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create sequence")

    created_steps = []
    for step in req.steps:
        try:
            step_result = (
                db.table("email_sequence_steps")
                .insert(
                    {
                        "sequence_id": sequence_id,
                        "step_order": step.step_order,
                        "delay_days": step.delay_days,
                        "delay_hours": step.delay_hours,
                        "subject": step.subject,
                        "body": step.body,
                        "email_type": step.email_type,
                        "is_active": step.is_active,
                    }
                )
                .execute()
            )
            if step_result.data:
                created_steps.append(step_result.data[0])
        except Exception:
            logger.exception(
                "Failed to create step %d for sequence %s",
                step.step_order,
                sequence_id,
            )

    sequence["steps"] = created_steps
    return sequence


def get_sequence_for_tenant(db: Any, tenant_id: str, sequence_id: str) -> dict:
    """Return one sequence with its steps + enrollment stats."""
    try:
        seq_result = (
            db.table("email_sequences")
            .select("*")
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not seq_result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
        sequence = seq_result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to get sequence %s for tenant %s", sequence_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to get sequence")

    try:
        steps_result = (
            db.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id)
            .order("step_order")
            .execute()
        )
        sequence["steps"] = steps_result.data or []
    except Exception:
        logger.warning(
            "Failed to fetch steps for sequence %s", sequence_id, exc_info=True
        )
        sequence["steps"] = []

    try:
        stats_result = (
            db.table("email_sequence_enrollments")
            .select("status")
            .eq("sequence_id", sequence_id)
            .execute()
        )
        enrollments = stats_result.data or []
        by_status: dict[str, int] = {}
        for e in enrollments:
            s = e["status"]
            by_status[s] = by_status.get(s, 0) + 1
        sequence["enrollment_stats"] = {
            "total": len(enrollments),
            "by_status": by_status,
        }
    except Exception:
        logger.warning(
            "Failed to fetch enrollment stats for sequence %s",
            sequence_id,
            exc_info=True,
        )
        sequence["enrollment_stats"] = {"total": 0, "by_status": {}}

    return sequence


def update_sequence_for_tenant(
    db: Any, tenant_id: str, sequence_id: str, req: SequenceUpdate
) -> dict:
    """Update sequence fields + optionally replace its step list."""
    raw = req.model_dump()
    new_steps = raw.pop("steps", None)
    updates = {k: v for k, v in raw.items() if v is not None}
    if not updates and new_steps is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        if updates:
            result = (
                db.table("email_sequences")
                .update(updates)
                .eq("id", sequence_id)
                .eq("tenant_id", tenant_id)
                .execute()
            )
            if not result.data:
                raise HTTPException(status_code=404, detail="Sequence not found")
            seq = result.data[0]
        else:
            seq_result = (
                db.table("email_sequences")
                .select("*")
                .eq("id", sequence_id)
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            if not seq_result.data:
                raise HTTPException(status_code=404, detail="Sequence not found")
            seq = seq_result.data[0]

        if new_steps is not None:
            db.table("email_sequence_steps").delete().eq(
                "sequence_id", sequence_id
            ).execute()
            for s in new_steps:
                db.table("email_sequence_steps").insert(
                    {
                        "sequence_id": sequence_id,
                        "step_order": s["step_order"],
                        "delay_days": s.get("delay_days", 0),
                        "delay_hours": s.get("delay_hours", 0),
                        "subject": s["subject"],
                        "body": s["body"],
                        "email_type": s.get("email_type", "email"),
                        "is_active": s.get("is_active", True),
                    }
                ).execute()

        return seq
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to update sequence %s for tenant %s", sequence_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to update sequence")


def soft_delete_sequence(db: Any, tenant_id: str, sequence_id: str) -> None:
    """Soft-delete a sequence by flipping is_active=False."""
    try:
        result = (
            db.table("email_sequences")
            .update(
                {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", sequence_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Sequence not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to delete sequence %s for tenant %s", sequence_id, tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to delete sequence")
