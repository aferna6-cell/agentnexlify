"""Pipeline stage automation endpoints — CRUD and execution.

When a lead moves to a pipeline stage, configured automations fire:
- email: Send a templated email to the lead
- create_task: Create an action_item for the team
- notify_team: Email the business owner / team about the stage change
"""

import html
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.email_sender import send_email, render_template, build_unsubscribe_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    type: str = Field(..., pattern="^(email|create_task|notify_team)$")
    subject: str | None = None
    body: str | None = None
    description: str | None = None
    message: str | None = None


class PipelineAutomationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_stage: str = Field(..., min_length=1, max_length=100)
    actions: list[ActionItem] = Field(..., min_length=1, max_length=10)
    is_active: bool = True


class PipelineAutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    trigger_stage: str | None = Field(default=None, min_length=1, max_length=100)
    actions: list[ActionItem] | None = Field(default=None, min_length=1, max_length=10)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/automations")
async def list_pipeline_automations(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all pipeline automations for a tenant."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    try:
        result = (
            db.table("pipeline_automations")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception:
        logger.exception("Failed to list pipeline automations for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load automations")
    return {"automations": result.data or []}


@router.post("/{tenant_id}/automations", status_code=201)
async def create_pipeline_automation(
    tenant_id: str,
    req: PipelineAutomationCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new pipeline stage automation."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    try:
        result = (
            db.table("pipeline_automations")
            .insert({
                "tenant_id": tenant_id,
                "name": req.name,
                "trigger_stage": req.trigger_stage,
                "actions": [a.model_dump() for a in req.actions],
                "is_active": req.is_active,
            })
            .execute()
        )
    except Exception:
        logger.exception("Failed to create pipeline automation for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create automation")
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create automation")
    return result.data[0]


@router.put("/{tenant_id}/automations/{automation_id}")
async def update_pipeline_automation(
    tenant_id: str,
    automation_id: str,
    req: PipelineAutomationUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a pipeline stage automation."""
    verify_tenant(claims, tenant_id)
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.trigger_stage is not None:
        updates["trigger_stage"] = req.trigger_stage
    if req.actions is not None:
        updates["actions"] = [a.model_dump() for a in req.actions]
    if req.is_active is not None:
        updates["is_active"] = req.is_active
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_supabase()
    try:
        result = (
            db.table("pipeline_automations")
            .update(updates)
            .eq("id", automation_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update pipeline automation %s", automation_id)
        raise HTTPException(status_code=500, detail="Failed to update automation")
    if not result.data:
        raise HTTPException(status_code=404, detail="Automation not found")
    return result.data[0]


@router.delete("/{tenant_id}/automations/{automation_id}", status_code=204)
async def delete_pipeline_automation(
    tenant_id: str,
    automation_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a pipeline stage automation."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    try:
        db.table("pipeline_automations").delete().eq("id", automation_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.exception("Failed to delete pipeline automation %s", automation_id)
        raise HTTPException(status_code=500, detail="Failed to delete automation")
    from fastapi.responses import Response
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Execution — called from pipeline.move_lead
# ---------------------------------------------------------------------------

async def execute_pipeline_automations(
    tenant_id: str,
    lead_id: str,
    new_stage: str,
    old_stage: str,
) -> int:
    """Fire all active pipeline automations for the given stage transition.

    Returns count of actions executed.
    """
    db = get_supabase()

    try:
        automations = (
            db.table("pipeline_automations")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("trigger_stage", new_stage)
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to query pipeline automations for stage %s", new_stage)
        return 0

    if not automations.data:
        return 0

    # Load lead details
    try:
        lead_result = (
            db.table("leads")
            .select("id, name, email, phone, email_bounced, unsubscribed")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load lead %s for pipeline automation", lead_id)
        return 0

    if not lead_result.data:
        return 0
    lead = lead_result.data[0]

    # Load tenant
    try:
        tenant_result = (
            db.table("tenants")
            .select("id, business_name, owner_email")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to load tenant %s for pipeline automation", tenant_id)
        return 0

    tenant = tenant_result.data[0] if tenant_result.data else {}
    business_name = tenant.get("business_name") or "Our Team"
    actions_executed = 0

    for automation in automations.data:
        actions = automation.get("actions") or []
        for action in actions:
            action_type = action.get("type", "")
            try:
                if action_type == "email":
                    await _execute_email_action(action, lead, tenant_id, business_name)
                    actions_executed += 1
                elif action_type == "create_task":
                    _execute_create_task_action(action, lead, tenant_id, new_stage, db)
                    actions_executed += 1
                elif action_type == "notify_team":
                    await _execute_notify_team_action(
                        action, lead, tenant, new_stage, old_stage,
                    )
                    actions_executed += 1
                else:
                    logger.warning("Unknown pipeline action type: %s", action_type)
            except Exception:
                logger.exception(
                    "Pipeline automation action failed: type=%s, automation=%s",
                    action_type, automation.get("id"),
                )

    if actions_executed > 0:
        logger.info(
            "Pipeline automations: executed %d actions for lead %s moving to stage '%s'",
            actions_executed, lead_id, new_stage,
        )

    return actions_executed


async def _execute_email_action(
    action: dict, lead: dict, tenant_id: str, business_name: str,
) -> None:
    """Send a templated email to the lead."""
    if not lead.get("email"):
        logger.debug("Pipeline email action skipped: lead %s has no email", lead["id"])
        return
    if lead.get("unsubscribed"):
        logger.debug("Pipeline email action skipped: lead %s is unsubscribed", lead["id"])
        return
    if lead.get("email_bounced"):
        logger.debug("Pipeline email action skipped: lead %s email bounced", lead["id"])
        return

    context = {
        "name": lead.get("name") or "there",
        "email": lead.get("email") or "",
        "business_name": business_name,
    }

    subject = render_template(action.get("subject") or "Update from {{business_name}}", context)
    body_html = render_template(action.get("body") or "<p>Hi {{name}}, we have an update for you.</p>", context)
    unsub_url = build_unsubscribe_url(lead["id"], tenant_id)

    await send_email(
        to=lead["email"],
        subject=subject,
        body_html=body_html,
        tenant_id=tenant_id,
        unsubscribe_url=unsub_url,
        lead_id=lead["id"],
    )


def _execute_create_task_action(
    action: dict, lead: dict, tenant_id: str, stage: str, db,
) -> None:
    """Create an action_item (task) for the team."""
    description = action.get("description") or f"Follow up with {lead.get('name', 'lead')} (moved to {stage})"
    context = {
        "name": lead.get("name") or "Lead",
        "stage": stage,
    }
    # Simple template substitution
    for key, val in context.items():
        description = description.replace("{{" + key + "}}", val)

    db.table("action_items").insert({
        "tenant_id": tenant_id,
        "lead_id": lead["id"],
        "description": description,
        "priority": "medium",
        "status": "open",
    }).execute()


async def _execute_notify_team_action(
    action: dict, lead: dict, tenant: dict, new_stage: str, old_stage: str,
) -> None:
    """Email the business owner about the stage change."""
    owner_email = tenant.get("owner_email")
    if not owner_email:
        return

    tenant_id = tenant.get("id", "")
    business_name = tenant.get("business_name") or "Your Business"
    lead_name = lead.get("name") or lead.get("email") or "A lead"
    raw_message = action.get("message") or f"{lead_name} moved from '{old_stage}' to '{new_stage}'"

    # HTML-escape all interpolated values — lead_name and stage names can be
    # user-supplied via the widget and would otherwise allow HTML injection
    # into the owner's inbox.
    safe_business = html.escape(business_name)
    safe_lead = html.escape(lead_name)
    safe_old = html.escape(old_stage)
    safe_new = html.escape(new_stage)
    safe_message = html.escape(raw_message)

    subject = f"[{safe_business}] Pipeline update: {safe_lead} \u2192 {safe_new}"
    body_html = (
        f"<h2>Pipeline Stage Change</h2>"
        f"<p><strong>{safe_lead}</strong> has moved from "
        f"<em>{safe_old}</em> to <em>{safe_new}</em>.</p>"
        f"<p>{safe_message}</p>"
        f"<p>\u2014 AgentNexLiFy</p>"
    )

    await send_email(
        to=owner_email,
        subject=subject,
        body_html=body_html,
        tenant_id=tenant_id,
    )
