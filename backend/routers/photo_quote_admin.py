"""Quote Requests dashboard API (#42).

``GET /api/photo-quotes/{tenant_id}`` — the tenant admin's quote history +
current-month usage meter. Tenant-authenticated (``_get_current_tenant``).
Read-side logic lives in ``photo_quote_admin_service`` + ``photo_quote_usage``.

No ``from __future__ import annotations`` (CLAUDE.md Rule 5). ``quote_requests``
is ``client_id``-scoped (migration 108).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import _get_current_tenant
from backend.services import photo_quote_admin_service, photo_quote_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photo-quotes", tags=["photo-quote-admin"])


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
    """Return ``{items, usage}`` for the tenant's Quote Requests dashboard."""
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
    return {"items": items, "usage": usage}
