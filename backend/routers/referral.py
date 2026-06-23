"""Referral click tracking — records watermark clicks from tenant-embedded widgets.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/referral", tags=["referral"])


class ReferralClickRequest(BaseModel):
    ref: str
    path: str | None = None
    referrer: str | None = None


@router.post("/click")
@limiter.limit("30/minute")
async def record_referral_click(
    request: Request,
    body: ReferralClickRequest,
):
    """Record a watermark click from an embedded widget.

    `ref` is the tenant's API key (from the widget's data-api-key attribute).
    `path` is the page path on the tenant's site where the click happened.
    `referrer` is the HTTP Referer header captured by the widget.
    """
    db = get_service_supabase()

    try:
        db.table("referral_clicks").insert(
            {
                "ref_tenant_id": body.ref,
                "path": body.path,
                "referrer": body.referrer,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to record referral click for ref=%s", body.ref)

    # Always return 204-equivalent OK — don't leak errors to the browser
    return {"ok": True}
