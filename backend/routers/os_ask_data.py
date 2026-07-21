"""Ask-your-business endpoint (suite item 2)."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services.biz_answers import SUPPORTED, answer_question

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    # Suite surface - agent_os plan (+ legacy) only; 402 upsell otherwise.
    dependencies=[Depends(require_agent_os_access)],
)


class AskDataIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.get("/ask-data/supported")
async def supported_questions(claims: dict = Depends(_get_current_tenant)):
    return {"supported_questions": SUPPORTED}


@router.post("/ask-data")
async def ask_data(body: AskDataIn, claims: dict = Depends(_get_current_tenant)):
    """Answer a business question from live tenant data - deterministic
    templates only, so every number is real."""
    db = get_service_supabase()
    return answer_question(db, claims["tenant_id"], body.question)
