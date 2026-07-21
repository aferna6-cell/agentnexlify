"""Deep research endpoint (round-3 item 3). Suite surface - plan-gated."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.os_research import MAX_TOPIC_LEN, run_research

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


class ResearchIn(BaseModel):
    topic: str = Field(min_length=10, max_length=MAX_TOPIC_LEN)


@router.post("/research")
async def research(body: ResearchIn, claims: dict = Depends(_get_current_tenant)):
    """Synthesize a propose-only research brief from the tenant's own
    sources. The brief parks at the normal approval gate."""
    db = get_service_supabase()
    try:
        out = await run_research(db, claims["tenant_id"], body.topic)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if out.get("error"):
        raise HTTPException(status_code=422, detail=out["error"])
    return out
