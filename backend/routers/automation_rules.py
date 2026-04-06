"""Automation Rules CRUD endpoints with trigger evaluation and execution logs."""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automation-rules", tags=["automation-rules"])

VALID_TRIGGER_TYPES = {
    "lead_captured",
    "tag_added",
    "tag_removed",
    "form_submitted",
    "appointment_created",
    "appointment_completed",
    "pipeline_stage_changed",
    "lead_score_threshold",
    "email_opened",
    "email_clicked",
    "scheduled_daily",
    "scheduled_weekly",
    "website_visit",
    "smart_list_matched",
}

VALID_CONDITION_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "greater_than",
    "less_than",
    "is_empty",
    "is_not_empty",
}

VALID_ACTION_TYPES = {
    "send_email",
    "add_tag",
    "remove_tag",
    "update_lead_status",
    "enroll_in_sequence",
    "create_task",
    "notify_team",
    "send_campaign",
    "update_lead_score",
}


TRIGGER_SCHEMAS: dict[str, dict] = {
    "lead_captured": {
        "description": "Fires when a new lead is captured",
        "config_fields": [],
    },
    "tag_added": {
        "description": "Fires when a specific tag is added to a lead",
        "config_fields": [{"name": "tag", "type": "string", "required": True}],
    },
    "tag_removed": {
        "description": "Fires when a specific tag is removed from a lead",
        "config_fields": [{"name": "tag", "type": "string", "required": True}],
    },
    "form_submitted": {
        "description": "Fires when a form is submitted",
        "config_fields": [{"name": "form_id", "type": "uuid", "required": True}],
    },
    "appointment_created": {
        "description": "Fires when an appointment is booked",
        "config_fields": [],
    },
    "appointment_completed": {
        "description": "Fires when an appointment is completed",
        "config_fields": [],
    },
    "pipeline_stage_changed": {
        "description": "Fires when a lead changes pipeline stage",
        "config_fields": [
            {"name": "from_stage", "type": "string"},
            {"name": "to_stage", "type": "string"},
        ],
    },
    "lead_score_threshold": {
        "description": "Fires when lead score crosses a threshold",
        "config_fields": [
            {"name": "direction", "type": "string", "required": True},
            {"name": "threshold", "type": "number", "required": True},
        ],
    },
    "email_opened": {
        "description": "Fires when a lead opens an email",
        "config_fields": [
            {"name": "campaign_id", "type": "uuid"},
            {"name": "sequence_id", "type": "uuid"},
        ],
    },
    "email_clicked": {
        "description": "Fires when a lead clicks an email link",
        "config_fields": [
            {"name": "campaign_id", "type": "uuid"},
            {"name": "sequence_id", "type": "uuid"},
        ],
    },
    "scheduled_daily": {
        "description": "Fires daily at a configured time",
        "config_fields": [
            {"name": "time", "type": "string", "required": True},
            {"name": "days", "type": "array"},
        ],
    },
    "scheduled_weekly": {
        "description": "Fires weekly on a configured day and time",
        "config_fields": [
            {"name": "day", "type": "string", "required": True},
            {"name": "time", "type": "string", "required": True},
        ],
    },
    "website_visit": {
        "description": "Fires when a lead visits the website",
        "config_fields": [],
    },
    "smart_list_matched": {
        "description": "Fires when a lead matches a smart list criteria",
        "config_fields": [{"name": "smart_list_id", "type": "uuid", "required": True}],
    },
}


class ConditionItem(BaseModel):
    field: str
    operator: str
    value: str | int | float | bool | None = None


class ActionItem(BaseModel):
    type: str = Field(..., description="Action type")
    config: dict = Field(default_factory=dict)


class AutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str
    trigger_config: dict = Field(default_factory=dict)
    conditions: list[ConditionItem] = Field(default_factory=list)
    actions: list[ActionItem] = Field(..., min_length=1)
    is_active: bool = True
    priority: int = 0


class AutomationRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    conditions: list[ConditionItem] | None = None
    actions: list[ActionItem] | None = None
    is_active: bool | None = None
    priority: int | None = None


class EvaluateTriggerRequest(BaseModel):
    trigger_type: str
    trigger_config: dict = Field(default_factory=dict)
    lead_id: str | None = None
    context: dict = Field(default_factory=dict)


@router.get("/{tenant_id}/triggers")
async def list_trigger_types(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all available trigger types with their config schemas."""
    verify_tenant(claims, tenant_id)

    triggers = []
    for trigger_type, schema in TRIGGER_SCHEMAS.items():
        triggers.append(
            {
                "trigger_type": trigger_type,
                "description": schema["description"],
                "config_fields": schema["config_fields"],
            }
        )
    return {"triggers": triggers}


@router.get("/{tenant_id}")
async def list_automation_rules(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    is_active: bool | None = Query(None),
    trigger_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List automation rules for a tenant."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
        query = (
            db.table("automation_rules")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("priority", desc=True)
            .range(offset, offset + limit - 1)
        )

        if is_active is not None:
            query = query.eq("is_active", is_active)
        if trigger_type:
            query = query.eq("trigger_type", trigger_type)

        result = query.execute()
        items = result.data or []

        count_query = (
            db.table("automation_rules")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
        )
        if is_active is not None:
            count_query = count_query.eq("is_active", is_active)
        if trigger_type:
            count_query = count_query.eq("trigger_type", trigger_type)
        count_result = count_query.execute()
        total = count_result.count if count_result.count is not None else len(items)

        return {"automation_rules": items, "total": total}
    except Exception:
        logger.exception("Failed to list automation rules for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list automation rules")


@router.post("/{tenant_id}")
async def create_automation_rule(
    tenant_id: str,
    req: AutomationRuleCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new automation rule."""
    verify_tenant(claims, tenant_id)

    if req.trigger_type not in VALID_TRIGGER_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger_type. Must be one of: {', '.join(sorted(VALID_TRIGGER_TYPES))}",
        )

    for action in req.actions:
        if action.type not in VALID_ACTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action type '{action.type}'. Must be one of: {', '.join(sorted(VALID_ACTION_TYPES))}",
            )

    try:
        db = get_supabase()
        payload = {
            "tenant_id": tenant_id,
            "name": req.name,
            "description": req.description,
            "trigger_type": req.trigger_type,
            "trigger_config": req.trigger_config,
            "conditions": [c.model_dump() for c in req.conditions],
            "actions": [a.model_dump() for a in req.actions],
            "is_active": req.is_active,
            "priority": req.priority,
        }
        result = db.table("automation_rules").insert(payload).execute()
        if not result.data:
            raise HTTPException(
                status_code=500, detail="Failed to create automation rule"
            )
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create automation rule for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create automation rule")


@router.get("/{tenant_id}/{rule_id}")
async def get_automation_rule(
    tenant_id: str,
    rule_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single automation rule."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
        result = (
            db.table("automation_rules")
            .select("*")
            .eq("id", rule_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Automation rule not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get automation rule %s", rule_id)
        raise HTTPException(status_code=500, detail="Failed to get automation rule")


@router.put("/{tenant_id}/{rule_id}")
async def update_automation_rule(
    tenant_id: str,
    rule_id: str,
    req: AutomationRuleUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update an automation rule."""
    verify_tenant(claims, tenant_id)

    if req.trigger_type and req.trigger_type not in VALID_TRIGGER_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger_type: {req.trigger_type}",
        )

    if req.actions:
        for action in req.actions:
            if action.type not in VALID_ACTION_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action type '{action.type}'",
                )

    updates = {}
    for k, v in req.model_dump().items():
        if v is not None:
            if k in ("conditions", "actions"):
                updates[k] = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in v
                ]
            else:
                updates[k] = v

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        db = get_supabase()
        result = (
            db.table("automation_rules")
            .update(updates)
            .eq("id", rule_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Automation rule not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update automation rule %s", rule_id)
        raise HTTPException(status_code=500, detail="Failed to update automation rule")


@router.delete("/{tenant_id}/{rule_id}", status_code=204)
async def delete_automation_rule(
    tenant_id: str,
    rule_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete an automation rule."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()
        result = (
            db.table("automation_rules")
            .delete()
            .eq("id", rule_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Automation rule not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete automation rule %s", rule_id)
        raise HTTPException(status_code=500, detail="Failed to delete automation rule")


@router.post("/{tenant_id}/{rule_id}/toggle")
async def toggle_automation_rule(
    tenant_id: str,
    rule_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Enable or disable an automation rule."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()

        rule_result = (
            db.table("automation_rules")
            .select("id, is_active")
            .eq("id", rule_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not rule_result.data:
            raise HTTPException(status_code=404, detail="Automation rule not found")

        new_active = not rule_result.data[0]["is_active"]
        result = (
            db.table("automation_rules")
            .update(
                {
                    "is_active": new_active,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", rule_id)
            .execute()
        )
        return {"id": rule_id, "is_active": new_active}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to toggle automation rule %s", rule_id)
        raise HTTPException(status_code=500, detail="Failed to toggle automation rule")


@router.get("/{tenant_id}/{rule_id}/logs")
async def get_automation_rule_logs(
    tenant_id: str,
    rule_id: str,
    claims: dict = Depends(_get_current_tenant),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get execution history logs for an automation rule."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_supabase()

        rule_result = (
            db.table("automation_rules")
            .select("id")
            .eq("id", rule_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not rule_result.data:
            raise HTTPException(status_code=404, detail="Automation rule not found")

        result = (
            db.table("automation_rule_executions")
            .select("*")
            .eq("automation_rule_id", rule_id)
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        count_result = (
            db.table("automation_rule_executions")
            .select("id", count="exact")
            .eq("automation_rule_id", rule_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        total = (
            count_result.count
            if count_result.count is not None
            else len(result.data or [])
        )

        return {"logs": result.data or [], "total": total}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get logs for automation rule %s", rule_id)
        raise HTTPException(
            status_code=500, detail="Failed to load automation rule logs"
        )


@router.post("/{tenant_id}/evaluate")
async def evaluate_automation_trigger(
    tenant_id: str,
    req: EvaluateTriggerRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Manually evaluate trigger conditions for testing purposes."""
    verify_tenant(claims, tenant_id)

    from backend.services.automation_engine import evaluate_trigger

    try:
        matches, lead_data = await evaluate_trigger(
            trigger_type=req.trigger_type,
            trigger_config=req.trigger_config,
            tenant_id=tenant_id,
            lead_id=req.lead_id,
            context=req.context,
        )
        return {
            "trigger_type": req.trigger_type,
            "trigger_config": req.trigger_config,
            "matches": matches,
            "lead_data": lead_data,
        }
    except Exception:
        logger.exception("Failed to evaluate trigger for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to evaluate trigger")
