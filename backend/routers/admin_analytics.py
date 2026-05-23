"""Platform-wide admin analytics — cross-tenant growth, revenue, and plan metrics.

All endpoints are protected by the API secret key (not JWT), since these are
internal admin tools for AgentNexLiFy staff only.

Heavy lifting lives in `backend/services/admin_analytics_service.py`; this
router stays thin on auth + HTTP shape.
"""

import logging

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.requests import Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.admin_analytics_service import (
    compute_industry_breakdown,
    compute_monthly_growth,
    compute_plan_distribution,
    compute_platform_overview,
    compute_revenue_trends,
    compute_weekly_growth,
    list_admin_tenants,
    list_promoted_businesses,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None = Header(None)) -> None:
    """Verify the caller has the platform admin secret."""
    import hmac as _hmac
    admin_secret = _admin_secret()
    if not admin_secret or not x_api_secret or not _hmac.compare_digest(x_api_secret, admin_secret):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


@router.get("/overview")
@limiter.limit("10/minute")
async def get_platform_overview(request: Request, x_api_secret: str | None = Header(None)):
    _verify_admin_secret(x_api_secret)
    try:
        return compute_platform_overview(get_service_supabase())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get platform overview")
        raise HTTPException(status_code=500, detail="Failed to load platform overview")


@limiter.limit("10/minute")
@router.get("/monthly-growth")
async def get_monthly_growth(
    request: Request,
    x_api_secret: str | None = Header(None),
    months: int = Query(12, ge=1, le=36),
):
    _verify_admin_secret(x_api_secret)
    try:
        return compute_monthly_growth(get_service_supabase(), months)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get monthly growth")
        raise HTTPException(status_code=500, detail="Failed to load monthly growth")


@limiter.limit("10/minute")
@router.get("/weekly-growth")
async def get_weekly_growth(request: Request, x_api_secret: str | None = Header(None)):
    _verify_admin_secret(x_api_secret)
    try:
        return compute_weekly_growth(get_service_supabase())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get weekly growth")
        raise HTTPException(status_code=500, detail="Failed to load weekly growth")


@limiter.limit("10/minute")
@router.get("/plan-distribution")
async def get_plan_distribution(request: Request, x_api_secret: str | None = Header(None)):
    _verify_admin_secret(x_api_secret)
    try:
        return compute_plan_distribution(get_service_supabase())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get plan distribution")
        raise HTTPException(status_code=500, detail="Failed to load plan distribution")


@limiter.limit("10/minute")
@router.get("/revenue-trends")
async def get_revenue_trends(
    request: Request,
    x_api_secret: str | None = Header(None),
    months: int = Query(12, ge=1, le=36),
):
    _verify_admin_secret(x_api_secret)
    return compute_revenue_trends(get_service_supabase(), months)


@limiter.limit("10/minute")
@router.get("/promoted-businesses")
async def get_promoted_businesses(request: Request, x_api_secret: str | None = Header(None)):
    _verify_admin_secret(x_api_secret)
    return list_promoted_businesses(get_service_supabase())


@limiter.limit("10/minute")
@router.get("/tenants")
async def list_all_tenants(
    request: Request,
    x_api_secret: str | None = Header(None),
    plan: str | None = Query(None),
    plan_status: str | None = Query(None),
    business_type: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    _verify_admin_secret(x_api_secret)
    try:
        return list_admin_tenants(
            get_service_supabase(),
            plan=plan,
            plan_status=plan_status,
            business_type=business_type,
            search=search,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list tenants")
        raise HTTPException(status_code=500, detail="Failed to list tenants")


@limiter.limit("10/minute")
@router.get("/industry-breakdown")
async def get_industry_breakdown(request: Request, x_api_secret: str | None = Header(None)):
    _verify_admin_secret(x_api_secret)
    try:
        return compute_industry_breakdown(get_service_supabase())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get industry breakdown")
        raise HTTPException(status_code=500, detail="Failed to load industry breakdown")
