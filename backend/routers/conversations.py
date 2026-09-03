"""Conversation listing endpoints — extracted from auth.py (Phase-2 Rule 9 split)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import block_demo_role
from backend.services.auth_service import get_current_tenant as _get_current_tenant
from backend.services import conversations_service as _conv_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["conversations"])


@router.get("/conversations/{tenant_id}")
async def list_conversations(
    tenant_id: str,
    channel: str | None = None,
    search: str | None = Query(None, max_length=200),
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _conv_svc.list_conversations(tenant_id, channel=channel, search=search)


@router.get("/conversations/{tenant_id}/{session_id}")
async def get_conversation_messages(
    tenant_id: str,
    session_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _conv_svc.get_conversation_messages(tenant_id, session_id)


@router.put("/conversations/{tenant_id}/{session_id}/tags")
async def update_conversation_tags(
    tenant_id: str,
    session_id: str,
    req: dict,
    claims: dict = Depends(block_demo_role),
):
    """Update tags on a conversation. Body: {"tags": ["tag1", "tag2"]}"""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _conv_svc.update_conversation_tags(
        tenant_id, session_id, req.get("tags", [])
    )
