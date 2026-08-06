"""Dashboard insights — daily focus picks + Nexlify Score.

Deterministic reads over existing tables (no LLM, no plan gate — both
plans get these; they drive daily-active use on chatbot and agent_os
alike). New module per Rule 12.
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.models.database import get_service_supabase
from backend.services.daily_focus import compute_daily_focus
from backend.services.response_score import compute_response_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/{tenant_id}/daily-focus")
async def get_daily_focus(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Up to 3 prioritized things to do today, each with a why."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return {"picks": compute_daily_focus(db, tenant_id)}


@router.get("/{tenant_id}/response-score")
async def get_response_score(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Composite 0-100 responsiveness score with per-component breakdown."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    return compute_response_score(db, tenant_id)
