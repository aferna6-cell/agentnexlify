"""Escalations router — dashboard surface for backend/services/escalations.py.

List, assign, and resolve first-class escalation records (Phase 1a of the
Nexlify capabilities roadmap). Tenant is derived from the JWT (no tenant_id
path segment) — matches frontend/src/utils/api/escalations.js, already
shipped by the frontend lane. NOT registered in backend/main.py by this
lane — the orchestrator wires the router in.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services.escalations import (
    list_escalations,
    mark_first_response,
    resolve_escalation,
)
from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])


class ResolveRequest(BaseModel):
    resolution: str = "resolved"


class AssignRequest(BaseModel):
    assigned_to: str | None = None


def _attach_session_ids(db, tenant_id: str, rows: list[dict]) -> list[dict]:
    """Enrich each escalation row with conversation_session_id — the
    dashboard's ConversationsPage keys on session_id, not the conversations
    UUID (see docs/dev-knowledge/architecture-decisions.md "Conversation
    lookup: dual-key resolution"). Best-effort: on failure, rows are
    returned unchanged rather than blocking the list."""
    conv_ids = sorted({r["conversation_id"] for r in rows if r.get("conversation_id")})
    if not conv_ids:
        return rows
    try:
        convs = (
            tenant_select(db, "conversations", tenant_id, "id, session_id")
            .in_("id", conv_ids)
            .execute()
        )
    except Exception:
        logger.warning(
            "escalations: session_id enrichment failed tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return rows
    session_by_conv = {c["id"]: c.get("session_id") for c in (convs.data or [])}
    for row in rows:
        row["conversation_session_id"] = session_by_conv.get(row.get("conversation_id"))
    return rows


@router.get("")
async def get_escalations(
    status: str | None = Query(None),
    claims: dict = Depends(_get_current_tenant),
):
    """List escalations for the tenant, newest first. Optional ?status=
    filter. Each row carries conversation_id (the escalations FK) and
    conversation_session_id (for the dashboard's conversation lookup)."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        rows = list_escalations(db, client_id=tenant_id, status=status)
        rows = _attach_session_ids(db, tenant_id, rows)
    except Exception:
        logger.error(
            "escalations: list failed tenant_id=%s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to list escalations")
    return {"escalations": rows}


@router.post("/{escalation_id}/resolve")
async def resolve_escalation_route(
    escalation_id: str,
    req: ResolveRequest,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Resolve (or dismiss) an escalation. Clears the "handoff" tag on its
    conversation once no other open escalation remains for it."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    resolved_by = claims.get("email") or claims.get("user_id")
    try:
        updated = resolve_escalation(
            db,
            escalation_id,
            client_id=tenant_id,
            resolution=req.resolution,
            resolved_by=resolved_by,
        )
    except Exception:
        logger.error(
            "escalations: resolve failed escalation_id=%s tenant_id=%s",
            escalation_id,
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to resolve escalation")
    if not updated:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return updated


@router.post("/{escalation_id}/assign")
async def assign_escalation_route(
    escalation_id: str,
    req: AssignRequest,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Assign (or unassign, when assigned_to is null) an escalation.

    Assigning sets assigned_to, moves status to in_progress, and stamps
    first_response_at if this is the first action taken on it. Unassigning
    (assigned_to=null) only clears assigned_to — status/first_response_at
    are left as-is."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()

    try:
        existing = (
            tenant_select(db, "escalations", tenant_id, "id")
            .eq("id", escalation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "escalations: assign lookup failed escalation_id=%s tenant_id=%s",
            escalation_id,
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to look up escalation")
    if not existing.data:
        raise HTTPException(status_code=404, detail="Escalation not found")

    updates: dict = {"assigned_to": req.assigned_to}
    if req.assigned_to:
        updates["status"] = "in_progress"

    try:
        tenant_update(db, "escalations", tenant_id, updates).eq(
            "id", escalation_id
        ).execute()
    except Exception:
        logger.error(
            "escalations: assign update failed escalation_id=%s tenant_id=%s",
            escalation_id,
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to assign escalation")

    if req.assigned_to:
        mark_first_response(db, escalation_id, client_id=tenant_id)

    try:
        final = (
            tenant_select(db, "escalations", tenant_id, "*")
            .eq("id", escalation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "escalations: assign re-fetch failed escalation_id=%s tenant_id=%s",
            escalation_id,
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to load updated escalation")
    if not final.data:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return final.data[0]
