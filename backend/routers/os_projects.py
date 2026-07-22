"""Multi-department OS Projects endpoints (specs/os-projects_spec.md)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services.os_projects import (
    MAX_ASK_LEN,
    plan_project,
    project_steps,
)
from backend.services.platform_flags import flag_enabled
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    # Suite surface - agent_os plan (+ legacy) only; 402 upsell otherwise.
    dependencies=[Depends(require_agent_os_access)],
)

_LIST_CAP = 20


def _require_flag() -> None:
    if not flag_enabled("os_projects_enabled"):
        raise HTTPException(status_code=404, detail="Projects not enabled")


class ProjectIn(BaseModel):
    ask: str = Field(min_length=10, max_length=MAX_ASK_LEN)


@router.post("/projects")
async def create_project(body: ProjectIn, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    try:
        return await plan_project(db, claims["tenant_id"], body.ask)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/projects")
async def list_projects(claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    rows = (
        tenant_select(db, "os_projects", claims["tenant_id"], "*")
        .order("created_at", desc=True)
        .limit(_LIST_CAP)
        .execute()
    ).data or []
    return {"projects": rows}


def _get_project(db, client_id: str, project_id: str) -> dict:
    rows = (
        tenant_select(db, "os_projects", client_id, "*")
        .eq("id", project_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")
    return rows[0]


def _attach_deliverables(db, client_id: str, steps: list[dict]) -> list[dict]:
    """Attach deliverable_status + deliverable_title to steps with runs.

    Lets the project timeline show what each step produced and offer inline
    approve/reject on awaiting steps without a second lookup per step.
    Best-effort: a failure returns the bare steps.
    """
    run_ids = [s.get("agent_run_id") for s in steps if s.get("agent_run_id")]
    if not run_ids:
        return steps
    try:
        runs = (
            tenant_select(
                db, "os_agent_runs", client_id, "id, deliverable, deliverable_status"
            )
            .in_("id", run_ids)
            .execute()
        ).data or []
    except Exception:
        logger.warning("os_projects: deliverable attach failed", exc_info=True)
        return steps
    by_id = {r.get("id"): r for r in runs}
    out = []
    for step in steps:
        run = by_id.get(step.get("agent_run_id"))
        if run:
            deliverable = run.get("deliverable") or {}
            step = {
                **step,
                "deliverable_status": run.get("deliverable_status"),
                "deliverable_title": (
                    deliverable.get("title")
                    if isinstance(deliverable, dict)
                    else None
                ),
            }
        out.append(step)
    return out


@router.get("/projects/{project_id}")
async def get_project(project_id: str, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    project = _get_project(db, claims["tenant_id"], project_id)
    steps = project_steps(db, claims["tenant_id"], project_id)
    return {
        "project": project,
        "steps": _attach_deliverables(db, claims["tenant_id"], steps),
    }


@router.post("/projects/{project_id}/approve")
async def approve_project(project_id: str, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    project = _get_project(db, claims["tenant_id"], project_id)
    if project.get("status") != "draft":
        raise HTTPException(
            status_code=422, detail=f"Project is {project.get('status')}, not draft"
        )
    if not project_steps(db, claims["tenant_id"], project_id):
        raise HTTPException(status_code=422, detail="Project has no plan steps")
    tenant_table(db, "os_projects", claims["tenant_id"]).update(
        {"status": "approved"}
    ).eq("id", project_id).execute()
    return {"status": "approved"}


@router.post("/projects/{project_id}/cancel")
async def cancel_project(project_id: str, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    project = _get_project(db, claims["tenant_id"], project_id)
    if project.get("status") in ("done", "canceled"):
        raise HTTPException(
            status_code=422, detail=f"Project already {project.get('status')}"
        )
    tenant_table(db, "os_projects", claims["tenant_id"]).update(
        {"status": "canceled"}
    ).eq("id", project_id).execute()
    # Unstarted steps never run (spec story 4).
    tenant_table(db, "os_project_steps", claims["tenant_id"]).update(
        {"status": "canceled"}
    ).eq("project_id", project_id).eq("status", "pending").execute()
    return {"status": "canceled"}
