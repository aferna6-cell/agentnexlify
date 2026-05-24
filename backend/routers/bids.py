"""Bids router — aggregator.

Originally a 607-line god class; split 2026-05-24 under Rule 9 / Rule 12.

Layout:
  - bids_models.py   — Pydantic models + `_verify_tenant` + module logger
  - bids_static.py   — list/create/stats/templates/ai-generate (no `{bid_id}`)
  - bids_dynamic.py  — get/update/delete/status/pdf (uses `{bid_id}`)

Static router MUST be included BEFORE the dynamic router so `/{tenant_id}/stats`,
`/{tenant_id}/templates`, and `/{tenant_id}/ai-generate` aren't shadowed by the
catch-all `/{tenant_id}/{bid_id}` route. See `.claude/rules/api-conventions.md`.
"""

from fastapi import APIRouter

from backend.models.database import get_service_supabase
from backend.routers.bids_dynamic import router as _dynamic_router
from backend.routers.bids_models import (
    AIBidGenerateRequest,
    BidCreate,
    BidItemModel,
    BidStatusUpdate,
    BidTemplateCreate,
    BidUpdate,
    _verify_tenant,
    logger,
)
from backend.routers.bids_static import router as _static_router

__all__ = [
    "router",
    "get_service_supabase",
    "logger",
    "AIBidGenerateRequest",
    "BidCreate",
    "BidItemModel",
    "BidStatusUpdate",
    "BidTemplateCreate",
    "BidUpdate",
    "_verify_tenant",
]

router = APIRouter(prefix="/api/v1/bids", tags=["bids"])
router.include_router(_static_router)
router.include_router(_dynamic_router)
