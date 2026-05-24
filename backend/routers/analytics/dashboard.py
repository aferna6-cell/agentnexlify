"""Dashboard analytics — aggregator router.

Originally a 628-line god class; split 2026-05-24 (Rule 9: factor god classes
>600 lines, Rule 12: new files over bloat).

Layout:
  - dashboard_overview.py    — KPI overview endpoint
  - dashboard_engagement.py  — conversations / leads / widget trend endpoints
  - dashboard_health.py      — health debug + tester snapshot

Re-exports `get_service_supabase` + `_cache` + `_CACHE_TTL` + `_period_to_days`
so existing tests that patch `backend.routers.analytics.dashboard.<symbol>`
keep working without modification (Rule 8: no half migrations).

Sub-router inclusion order preserves the original endpoint registration order:
overview → conversations → leads → widget → health → snapshot.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from fastapi import APIRouter

from backend.models.database import get_service_supabase
from backend.routers.analytics._common import (
    _CACHE_TTL,
    _cache,
    _period_to_days,
)
from backend.routers.analytics.dashboard_engagement import router as _engagement_router
from backend.routers.analytics.dashboard_health import router as _health_router
from backend.routers.analytics.dashboard_overview import router as _overview_router

__all__ = [
    "router",
    "get_service_supabase",
    "_cache",
    "_CACHE_TTL",
    "_period_to_days",
]

router = APIRouter()
router.include_router(_overview_router)
router.include_router(_engagement_router)
router.include_router(_health_router)
