"""Agent OS semantic memory — P0 router.

Durable facts/preferences/decisions the orchestrator recalls across threads.
Listing + creating is open to any authenticated tenant user; editing and
deleting are owner-only — memory shapes every future routing decision.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services import os_memory as memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

_KINDS = sorted(memory_service.VALID_KINDS)


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    kind: str = Field(default="fact")


class RememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MemoryUpdateRequest(BaseModel):
    content: str | None = Field(default=None, max_length=4000)
    kind: str | None = None
    is_pinned: bool | None = None


@router.get("/memory")
async def list_memory(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return memory_service.list_memory(db, client_id)


@router.post("/memory", status_code=201)
async def create_memory(
    req: MemoryCreateRequest, claims: dict = Depends(_get_current_tenant)
):
    client_id = claims["tenant_id"]
    if req.kind not in memory_service.VALID_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {_KINDS}")
    db = get_service_supabase()
    return await memory_service.write_memory(
        db,
        client_id,
        content=req.content.strip(),
        kind=req.kind,
        source="manual",
        created_by="owner",
    )


@router.post("/memory/remember", status_code=201)
async def remember(req: RememberRequest, claims: dict = Depends(_get_current_tenant)):
    """Quick 'remember this' — stores a fact with manual provenance."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return await memory_service.write_memory(
        db,
        client_id,
        content=req.content.strip(),
        kind="fact",
        source="manual",
        created_by="owner",
    )


@router.patch("/memory/{memory_id}")
async def update_memory(
    memory_id: str,
    req: MemoryUpdateRequest,
    claims: dict = Depends(require_role("owner")),
):
    client_id = claims["tenant_id"]
    if req.kind is not None and req.kind not in memory_service.VALID_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {_KINDS}")
    db = get_service_supabase()
    updated = await memory_service.update_memory(
        db,
        client_id,
        memory_id,
        content=req.content.strip() if req.content is not None else None,
        kind=req.kind,
        is_pinned=req.is_pinned,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return updated


@router.delete("/memory/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, claims: dict = Depends(require_role("owner"))):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    if not memory_service.delete_memory(db, client_id, memory_id):
        raise HTTPException(status_code=404, detail="Memory entry not found")
