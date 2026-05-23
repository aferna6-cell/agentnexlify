"""Control center analytics endpoint (thin glue → control_center_service)."""

from fastapi import APIRouter, Depends, Query, Request

from backend.dependencies import _get_current_tenant, verify_tenant
from backend.limiter import limiter
from backend.models.schemas import AgentControlCenterResponse
from backend.routers.analytics._common import _get_cached, _set_cache
from backend.services import control_center_service

router = APIRouter()


@router.get("/{tenant_id}/control-center", response_model=AgentControlCenterResponse)
@limiter.limit("30/minute")
async def get_agent_control_center(
    request: Request,
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|14d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Operational view of assistant performance across QA, recovery, and ROI."""
    verify_tenant(claims, tenant_id)

    cache_key = f"control_center:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    response = control_center_service.build_control_center_response(tenant_id, period)
    _set_cache(cache_key, response)
    return response
