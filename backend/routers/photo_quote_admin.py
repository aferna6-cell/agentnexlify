"""Quote Requests dashboard API (#42).

``GET /api/photo-quotes/{tenant_id}`` — the tenant admin's quote history +
current-month usage meter. Tenant-authenticated (``_get_current_tenant``).
Read-side logic lives in ``photo_quote_admin_service`` + ``photo_quote_usage``.

No ``from __future__ import annotations`` (CLAUDE.md Rule 5). ``quote_requests``
is ``client_id``-scoped (migration 108).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.services import (
    photo_quote_admin_service,
    photo_quote_telemetry,
    photo_quote_usage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photo-quotes", tags=["photo-quote-admin"])


class QuoteFeedback(BaseModel):
    quote_id: str
    feedback: str  # correct | too_low | too_high | unclear


@router.get("/{tenant_id}")
async def list_photo_quotes(
    tenant_id: str,
    limit: int = Query(100, ge=1, le=500),
    industry: str = Query(None),
    needs_human: bool = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    claims: dict = Depends(_get_current_tenant),
):
    """Return ``{items, usage, telemetry}`` for the Quote Requests dashboard."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    items = photo_quote_admin_service.list_quote_requests(
        tenant_id,
        limit=limit,
        industry=industry,
        needs_human=needs_human,
        start_date=start_date,
        end_date=end_date,
    )
    usage = photo_quote_usage.get_usage_summary(tenant_id)
    telemetry = {
        "error_rate": photo_quote_telemetry.compute_error_rate(tenant_id),
        "conversion": photo_quote_telemetry.compute_conversion_rate(tenant_id),
    }
    return {"items": items, "usage": usage, "telemetry": telemetry}


@router.post("/{tenant_id}/feedback")
async def submit_quote_feedback(
    tenant_id: str,
    payload: QuoteFeedback,
    claims: dict = Depends(_get_current_tenant),
):
    """Record the tenant's rating on one quote (#44 pilot instrumentation)."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    if payload.feedback not in photo_quote_telemetry.VALID_FEEDBACK:
        raise HTTPException(status_code=422, detail="Invalid feedback value")
    ok = photo_quote_telemetry.record_feedback(
        tenant_id, payload.quote_id, payload.feedback
    )
    return {"ok": ok}
