"""Deep research endpoint (round-3 item 3). Suite surface - plan-gated."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.os_research import (
    MAX_TOPIC_LEN,
    research_to_project,
    run_research,
)
from backend.services.os_web_sources import MAX_URLS
from backend.services.platform_flags import flag_enabled

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


class ResearchIn(BaseModel):
    topic: str = Field(min_length=10, max_length=MAX_TOPIC_LEN)
    # Research v2: up to MAX_URLS owner-provided web pages join the corpus
    # (SSRF-gated server-side; each capped and cited in provenance).
    urls: list[str] | None = Field(default=None, max_length=MAX_URLS)


@router.post("/research")
async def research(body: ResearchIn, claims: dict = Depends(_get_current_tenant)):
    """Synthesize a propose-only research brief from the tenant's own
    sources plus optional web pages. The brief parks at the approval gate."""
    db = get_service_supabase()
    try:
        out = await run_research(db, claims["tenant_id"], body.topic, body.urls)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if out.get("error"):
        raise HTTPException(status_code=422, detail=out["error"])
    return out


@router.post("/research/{run_id}/to-project")
async def research_run_to_project(
    run_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Seed a multi-department project from a research brief's findings.

    The project parks as an approvable draft plan - same lifecycle as any
    project. Mirrors the /projects surface's flag gate.
    """
    if not flag_enabled("os_projects_enabled"):
        raise HTTPException(status_code=404, detail="Projects not enabled")
    db = get_service_supabase()
    try:
        return await research_to_project(db, claims["tenant_id"], run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
