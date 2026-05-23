"""Automation sequences API — CRUD for email follow-up sequences and campaigns."""



from backend.services.task_utils import safe_create_task
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.models.schemas import (
    LeadStageUpdate,
    SequenceCreateRequest,
    SequenceUpdateRequest,
)
from backend.dependencies import _get_current_tenant, require_role
from backend.services.automation_engine import trigger_sequence
from backend.services.sequence_campaign import dispatch_campaign, fetch_campaign_leads
from backend.services.sequence_templates import TEMPLATES, build_sequence_from_template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sequences", tags=["sequences"])


def _verify_tenant(tenant_id: str, claims: dict) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")


@router.get("/{tenant_id}")
async def list_sequences(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """List all sequences with step count and execution stats."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    seqs = (
        db.table("automation_sequences")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    seq_ids = [s["id"] for s in (seqs.data or [])]
    if not seq_ids:
        return {"sequences": []}

    # Batch fetch steps and executions for all sequences (avoids N+1)
    all_steps = (
        db.table("automation_steps")
        .select("sequence_id")
        .in_("sequence_id", seq_ids)
        .execute()
    )
    all_execs = (
        db.table("automation_executions")
        .select("sequence_id,status")
        .in_("sequence_id", seq_ids)
        .execute()
    )

    # Build lookup maps
    step_counts = {}
    for s in (all_steps.data or []):
        step_counts[s["sequence_id"]] = step_counts.get(s["sequence_id"], 0) + 1

    exec_by_seq = {}
    for e in (all_execs.data or []):
        exec_by_seq.setdefault(e["sequence_id"], []).append(e["status"])

    result = []
    for seq in seqs.data:
        sid = seq["id"]
        statuses = exec_by_seq.get(sid, [])
        result.append({
            **seq,
            "step_count": step_counts.get(sid, 0),
            "total_enrolled": len(statuses),
            "active_count": sum(1 for st in statuses if st == "in_progress"),
            "completed_count": sum(1 for st in statuses if st == "completed"),
        })

    return {"sequences": result}


@router.post("/{tenant_id}")
async def create_sequence(
    tenant_id: str,
    req: SequenceCreateRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new sequence with steps."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    # Create sequence
    seq_result = db.table("automation_sequences").insert({
        "tenant_id": tenant_id,
        "name": req.name,
        "trigger_event": req.trigger_event,
        "trigger_config": req.trigger_config,
    }).execute()
    seq = seq_result.data[0]

    # Create steps
    steps_data = []
    for step in req.steps:
        steps_data.append({
            "sequence_id": seq["id"],
            "step_order": step.step_order,
            "delay_minutes": step.delay_minutes,
            "action_type": step.action_type,
            "subject_template": step.subject_template,
            "body_template": step.body_template,
        })

    if steps_data:
        db.table("automation_steps").insert(steps_data).execute()

    return {"sequence": seq, "steps_created": len(steps_data)}


@router.get("/{tenant_id}/stats")
async def get_sequence_stats(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Dashboard stats for sequences."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    # Active sequences count
    active_seqs = (
        db.table("automation_sequences")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .execute()
    )

    # Emails sent today — join through automation_executions (automation_logs has no tenant_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
    tenant_executions = (
        db.table("automation_executions")
        .select("id")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    tenant_exec_ids = [e["id"] for e in (tenant_executions.data or [])]
    if tenant_exec_ids:
        logs = (
            db.table("automation_logs")
            .select("id", count="exact")
            .in_("execution_id", tenant_exec_ids)
            .eq("action", "email_sent")
            .gte("created_at", today)
            .execute()
        )
    else:
        logs = type("FakeResult", (), {"count": 0})()

    # Total active executions
    active_execs = (
        db.table("automation_executions")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "in_progress")
        .execute()
    )

    # Email opens today
    try:
        opens = (
            db.table("email_events")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("event_type", "open")
            .gte("created_at", today)
            .execute()
        )
        opens_today = opens.count or 0
    except Exception:
        opens_today = 0  # Table may not exist yet

    # Total opens (all time)
    try:
        total_opens = (
            db.table("email_events")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("event_type", "open")
            .execute()
        )
        total_open_count = total_opens.count or 0
    except Exception:
        total_open_count = 0

    return {
        "active_sequences": active_seqs.count or 0,
        "emails_sent_today": logs.count or 0,
        "active_executions": active_execs.count or 0,
        "opens_today": opens_today,
        "total_opens": total_open_count,
    }


@router.get("/{tenant_id}/{seq_id}")
async def get_sequence_detail(
    tenant_id: str, seq_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Get sequence detail with steps and recent logs."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    seq = (
        db.table("automation_sequences")
        .select("*")
        .eq("id", seq_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not seq.data:
        raise HTTPException(status_code=404, detail="Sequence not found")

    steps = (
        db.table("automation_steps")
        .select("*")
        .eq("sequence_id", seq_id)
        .order("step_order")
        .execute()
    )

    # Execution stats
    execs = (
        db.table("automation_executions")
        .select("status")
        .eq("sequence_id", seq_id)
        .execute()
    )
    exec_data = execs.data or []

    # Recent logs (join through executions)
    exec_ids = [e["id"] for e in (
        db.table("automation_executions")
        .select("id")
        .eq("sequence_id", seq_id)
        .execute()
    ).data or []]

    logs: list[dict[str, Any]] = []
    if exec_ids:
        logs_result = (
            db.table("automation_logs")
            .select("*")
            .in_("execution_id", exec_ids)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        logs = logs_result.data or []

    return {
        "sequence": seq.data[0],
        "steps": steps.data or [],
        "stats": {
            "total_enrolled": len(exec_data),
            "active": sum(1 for e in exec_data if e["status"] == "in_progress"),
            "completed": sum(1 for e in exec_data if e["status"] == "completed"),
            "failed": sum(1 for e in exec_data if e["status"] == "failed"),
        },
        "recent_logs": logs,
    }


@router.put("/{tenant_id}/{seq_id}")
async def update_sequence(
    tenant_id: str,
    seq_id: str,
    req: SequenceUpdateRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update sequence and optionally replace steps."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    # Verify exists
    existing = (
        db.table("automation_sequences")
        .select("id")
        .eq("id", seq_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Sequence not found")

    # Update sequence fields
    updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if req.name is not None:
        updates["name"] = req.name
    if req.trigger_event is not None:
        updates["trigger_event"] = req.trigger_event
    if req.trigger_config is not None:
        updates["trigger_config"] = req.trigger_config

    db.table("automation_sequences").update(updates).eq("id", seq_id).execute()

    # Replace steps if provided
    if req.steps is not None:
        # Delete old steps
        db.table("automation_steps").delete().eq("sequence_id", seq_id).execute()
        # Insert new steps
        steps_data = []
        for step in req.steps:
            steps_data.append({
                "sequence_id": seq_id,
                "step_order": step.step_order,
                "delay_minutes": step.delay_minutes,
                "action_type": step.action_type,
                "subject_template": step.subject_template,
                "body_template": step.body_template,
            })
        if steps_data:
            db.table("automation_steps").insert(steps_data).execute()

    return {"updated": True}


@router.delete("/{tenant_id}/{seq_id}")
async def delete_sequence(
    tenant_id: str, seq_id: str, claims: dict = Depends(require_role("owner", "admin"))
):
    """Delete a sequence (cascade deletes steps/executions/logs)."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    result = (
        db.table("automation_sequences")
        .delete()
        .eq("id", seq_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Sequence not found")

    return {"deleted": True}


@router.post("/{tenant_id}/{seq_id}/toggle")
async def toggle_sequence(
    tenant_id: str, seq_id: str, claims: dict = Depends(require_role("owner", "admin"))
):
    """Toggle sequence active/inactive."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    seq = (
        db.table("automation_sequences")
        .select("id, is_active")
        .eq("id", seq_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not seq.data:
        raise HTTPException(status_code=404, detail="Sequence not found")

    new_state = not seq.data[0]["is_active"]
    db.table("automation_sequences").update({
        "is_active": new_state,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", seq_id).execute()

    return {"is_active": new_state}


@router.post("/{tenant_id}/templates")
async def create_from_template(
    tenant_id: str,
    template_id: str = Body(..., embed=True),
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a sequence from a pre-built template."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()
    try:
        return build_sequence_from_template(db, tenant_id, template_id)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template. Available: {list(TEMPLATES.keys())}",
        )


# --- Lead stage update with automation trigger ---

leads_router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@leads_router.patch("/{tenant_id}/{lead_id}/stage")
async def update_lead_stage(
    tenant_id: str,
    lead_id: str,
    req: LeadStageUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a lead's stage and fire automation triggers."""
    _verify_tenant(tenant_id, claims)
    db = get_service_supabase()

    # Verify lead belongs to tenant
    lead = (
        db.table("leads")
        .select("id, status")
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_stage = lead.data[0]["status"]
    db.table("leads").update({"status": req.stage}).eq("id", lead_id).execute()

    # Fire automation trigger
    if old_stage != req.stage:
        safe_create_task(
            trigger_sequence(
                tenant_id, lead_id, "lead_stage_change",
                {"old_stage": old_stage, "new_stage": req.stage},
            ),
            name="trigger_lead_stage_change",
        )

    return {"lead_id": lead_id, "old_stage": old_stage, "new_stage": req.stage}


# ---------------------------------------------------------------------------
# One-time campaign blast (lead re-engagement)
# ---------------------------------------------------------------------------

class CampaignRequest(BaseModel):
    subject: str = Field(..., max_length=200)
    body_html: str = Field(..., max_length=10000)
    channel: str = Field(default="email", pattern="^(email|sms)$")
    filters: dict = Field(default_factory=dict)


@router.post("/{tenant_id}/campaigns/send")
async def send_campaign(
    tenant_id: str,
    req: CampaignRequest,
    tenant: dict = Depends(require_role("owner", "admin")),
):
    """Send a one-time email/SMS blast to a filtered segment of leads.

    Filters (all optional):
    - status: lead status string (e.g. "new", "contacted")
    - tags: list of tags (leads must have at least one)
    - min_score: minimum lead score
    - created_after: ISO date string
    - created_before: ISO date string
    """
    _verify_tenant(tenant_id, tenant)
    db = get_service_supabase()
    leads = fetch_campaign_leads(db, tenant_id, req.filters)
    return await dispatch_campaign(
        leads,
        tenant_id=tenant_id,
        channel=req.channel,
        subject=req.subject,
        body_html=req.body_html,
        plan=tenant.get("plan") or "free",
    )
