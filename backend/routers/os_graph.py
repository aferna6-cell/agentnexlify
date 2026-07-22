"""Agent OS knowledge graph — the owner's "what do you know about my business" view.

GET returns the full graph (nodes grouped client-side, edges for relations).
DELETE is the owner's "forget this" — removes a node and its edges (FK
cascade). Owner-only on delete, same bar as memory edits.

client_id is always the JWT tenant_id — never a path/body value.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.models.database import get_service_supabase
from backend.services import os_graph_memory

logger = logging.getLogger(__name__)

# Stage-3 plan gate (2026-07-22, audit H1): suite surface - agent_os
# plan (+ legacy) only; 402 upsell otherwise.
router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os"],
    dependencies=[Depends(require_agent_os_access)],
)


def _is_owner(claims: dict) -> bool:
    role = claims.get("role") or ""
    return role.lower() == "owner"


@router.get("/graph")
async def get_graph(claims: dict = Depends(_get_current_tenant)):
    """Everything the OS has learned about this business, as nodes + edges."""
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return os_graph_memory.list_graph(db, client_id)


@router.delete("/graph/nodes/{node_id}")
async def forget_node(node_id: str, claims: dict = Depends(_get_current_tenant)):
    """Owner-only: forget one entity (its edges cascade away with it)."""
    if not _is_owner(claims):
        raise HTTPException(status_code=403, detail="Owner role required")
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    if not os_graph_memory.delete_node(db, client_id, node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return {"deleted": node_id}
