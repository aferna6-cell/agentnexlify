"""Owner-facing per-department instruction editing (enterprise-audit item 4)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import os_custom_instructions
from backend.services.os_routing_memory import KNOWN_DEPARTMENTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])


class InstructionIn(BaseModel):
    text: str = Field(
        max_length=os_custom_instructions.MAX_INSTRUCTION_LEN, default=""
    )


@router.get("/instructions")
async def get_instructions(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()
    return {
        "departments": sorted(KNOWN_DEPARTMENTS),
        "instructions": os_custom_instructions.get_instructions(
            db, claims["tenant_id"]
        ),
        "max_length": os_custom_instructions.MAX_INSTRUCTION_LEN,
    }


@router.put("/instructions/{department}")
async def put_instruction(
    department: str,
    body: InstructionIn,
    claims: dict = Depends(_get_current_tenant),
):
    """Set one department's instruction; empty text clears it."""
    db = get_service_supabase()
    try:
        instructions = os_custom_instructions.set_instruction(
            db, claims["tenant_id"], department, body.text
        )
    except os_custom_instructions.UnknownDepartment as err:
        raise HTTPException(status_code=422, detail=str(err))
    return {"instructions": instructions}
