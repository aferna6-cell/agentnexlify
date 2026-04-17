"""Analytics router package. Exposes a single `router` combining all analytics sub-modules."""

from fastapi import APIRouter

from backend.routers.analytics._common import _period_to_days  # re-export for tests + back-compat
from backend.routers.analytics.dashboard import router as dashboard_router
from backend.routers.analytics.operations import router as operations_router
from backend.routers.analytics.insights import router as insights_router
from backend.routers.analytics.control_center import router as control_center_router
from backend.routers.analytics.recovery import router as recovery_router

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
router.include_router(dashboard_router)
router.include_router(operations_router)
router.include_router(insights_router)
router.include_router(control_center_router)
router.include_router(recovery_router)
