"""Intake AI — photo-triage (#R1) + instant quoting (#R2).

POST /api/v1/photo-triage — widget-key auth (no dashboard session), mirrors
`backend/routers/widget_lead.py`'s `_get_widget_config(api_key)` resolution.
Claude vision (backend/services/photo_triage.py) assesses urgency + scope
from 1-3 uploaded photos. Never blocks the widget flow: on any triage
failure this returns 200 with `{"status": "unavailable"}`, not an error the
widget has to special-case — only an invalid api_key or a DB outage on the
widget-config lookup itself raises (404 / 503, same as widget_lead.py).

POST /api/v1/quotes/build — JWT-protected (dashboard-initiated). Drafts an
itemized Good/Better/Best quote (backend/services/quote_builder.py)
grounded in the tenant's own `service_types` catalog — the moat is real
tenant prices, never invented ones.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.routers.widget_chat_helpers import _get_tenant, _get_widget_config
from backend.services.photo_triage import triage_photos
from backend.services.quote_builder import build_quote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["intake-ai"])


class PhotoTriageImage(BaseModel):
    media_type: str = Field(..., max_length=50)
    data: str = Field(..., min_length=1)


class PhotoTriageRequest(BaseModel):
    api_key: str = Field(..., max_length=100)
    images: list[PhotoTriageImage] = Field(..., min_length=1)
    note: str | None = Field(None, max_length=2000)
    session_id: str | None = Field(None, max_length=100)


class PhotoTriageResponse(BaseModel):
    status: str = "ok"
    urgency: str | None = None
    category: str | None = None
    scope_summary: str | None = None
    recommended_action: str | None = None


class QuoteBuildRequest(BaseModel):
    job_description: str = Field(..., min_length=1, max_length=5000)
    triage: dict | None = None
    lead_id: str | None = Field(None, max_length=100)


class QuoteOut(BaseModel):
    id: str
    tenant_id: str
    lead_id: str | None = None
    job_description: str
    triage: dict | None = None
    tiers: dict
    status: str
    created_at: str | None = None
    updated_at: str | None = None


@router.post("/photo-triage", response_model=PhotoTriageResponse)
@limiter.limit("20/minute")
async def photo_triage_endpoint(request: Request, req: PhotoTriageRequest):
    """Widget-facing photo triage. See module docstring for the auth +
    failure-mode contract."""
    widget = _get_widget_config(req.api_key)
    tenant_id = widget["tenant_id"]

    business_type = ""
    try:
        tenant = _get_tenant(tenant_id)
        business_type = tenant.get("business_type") or ""
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "photo_triage_endpoint: tenant lookup failed tenant=%s",
            tenant_id,
            exc_info=True,
        )

    triage = await triage_photos(
        business_type=business_type,
        images=[img.model_dump() for img in req.images],
        note=req.note,
    )
    if not triage:
        return PhotoTriageResponse(status="unavailable")
    return PhotoTriageResponse(status="ok", **triage)


@router.post("/quotes/build", response_model=QuoteOut)
async def quote_build_endpoint(
    req: QuoteBuildRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Dashboard-initiated instant quote grounded in the tenant's own
    service_types catalog."""
    tenant_id = claims["tenant_id"]
    try:
        row = await build_quote(
            tenant_id=tenant_id,
            job_description=req.job_description,
            triage=req.triage,
            lead_id=req.lead_id,
        )
    except Exception:
        logger.error(
            "quote_build_endpoint: build_quote failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to build quote")

    if not row:
        raise HTTPException(status_code=502, detail="Failed to build quote")
    return row
