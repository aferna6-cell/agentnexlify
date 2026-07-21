"""Recurring Agent OS task CRUD (suite item 1)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.os_routing_memory import KNOWN_DEPARTMENTS
from backend.services.os_scheduled_tasks import MAX_PROMPT_LEN, clamp_interval
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

_TASK_CAP = 20


class TaskIn(BaseModel):
    department: str
    prompt: str = Field(min_length=5, max_length=MAX_PROMPT_LEN)
    interval_days: int = 7
    enabled: bool = True


@router.get("/tasks")
async def list_tasks(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()
    rows = (
        tenant_select(db, "os_scheduled_tasks", claims["tenant_id"], "*")
        .order("created_at", desc=False)
        .limit(_TASK_CAP)
        .execute()
    ).data or []
    return {"tasks": rows, "departments": sorted(KNOWN_DEPARTMENTS)}


@router.post("/tasks")
async def create_task(body: TaskIn, claims: dict = Depends(_get_current_tenant)):
    department = body.department.strip().lower()
    if department not in KNOWN_DEPARTMENTS:
        raise HTTPException(status_code=422, detail="unknown department")
    db = get_service_supabase()
    existing = (
        tenant_select(db, "os_scheduled_tasks", claims["tenant_id"], "id")
        .limit(_TASK_CAP)
        .execute()
    ).data or []
    if len(existing) >= _TASK_CAP:
        raise HTTPException(status_code=422, detail="scheduled task limit reached")
    created = (
        tenant_table(db, "os_scheduled_tasks", claims["tenant_id"])
        .insert(
            {
                "department": department,
                "prompt": body.prompt.strip(),
                "interval_days": clamp_interval(body.interval_days),
                "enabled": body.enabled,
            }
        )
        .execute()
    )
    return created.data[0]


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()
    deleted = (
        tenant_table(db, "os_scheduled_tasks", claims["tenant_id"])
        .delete()
        .eq("id", task_id)
        .execute()
    )
    if not deleted.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


class TaskPatch(BaseModel):
    prompt: str | None = Field(default=None, min_length=5, max_length=MAX_PROMPT_LEN)
    interval_days: int | None = None
    enabled: bool | None = None


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str, body: TaskPatch, claims: dict = Depends(_get_current_tenant)
):
    fields: dict = {}
    if body.prompt is not None:
        fields["prompt"] = body.prompt.strip()
    if body.interval_days is not None:
        fields["interval_days"] = clamp_interval(body.interval_days)
    if body.enabled is not None:
        fields["enabled"] = body.enabled
    if not fields:
        raise HTTPException(status_code=422, detail="nothing to update")
    db = get_service_supabase()
    updated = (
        tenant_table(db, "os_scheduled_tasks", claims["tenant_id"])
        .update(fields)
        .eq("id", task_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated.data[0]


@router.get("/tasks/suggestions")
async def task_suggestions(claims: dict = Depends(_get_current_tenant)):
    """One-click starter recurring tasks for tenants with none yet."""
    from backend.services.os_starter_tasks import suggest_recurring_tasks

    db = get_service_supabase()
    return {"suggestions": suggest_recurring_tasks(db, claims["tenant_id"])}
