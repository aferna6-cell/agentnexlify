"""Instant KB from website URL - onboarding endpoints.

POST /api/v1/instant-kb/{tenant_id}/draft
  - Fetches the website URL's text, asks Claude for FAQ entries, and returns
    them for owner review. Writes nothing.

POST /api/v1/instant-kb/{tenant_id}/confirm
  - Persists the owner-approved FAQ entries to faq_entries (scoped by tenant_id).

Both endpoints surface clear errors and never crash the onboarding flow.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.dependencies import require_role
from backend.services.instant_kb import (
    InstantKbError,
    draft_faq_entries,
    fetch_website_text,
    persist_faq_entries,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/instant-kb", tags=["instant-kb"])


class InstantKbFaqEntry(BaseModel):
    question: str = Field(..., max_length=500)
    answer: str = Field(..., max_length=2000)
    category: str = Field("general", max_length=50)


class InstantKbDraftRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=500)


class InstantKbDraftResponse(BaseModel):
    faqs: list[InstantKbFaqEntry]
    chars_extracted: int
    source_url: str


class InstantKbConfirmRequest(BaseModel):
    faqs: list[InstantKbFaqEntry] = Field(..., min_length=1, max_length=20)


class InstantKbConfirmResponse(BaseModel):
    saved: int


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# Map service error codes to HTTP status. Client/input problems -> 4xx,
# upstream/AI problems -> 502.
_ERROR_STATUS = {
    "unsafe_url": 400,
    "not_html": 422,
    "empty_page": 422,
    "no_entries": 422,
    "fetch_failed": 502,
    "llm_failed": 502,
    "persist_failed": 500,
}


@router.post("/{tenant_id}/draft", response_model=InstantKbDraftResponse)
@limiter.limit("5/hour")
async def draft_instant_kb(
    request: Request,
    tenant_id: str,
    req: InstantKbDraftRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Fetch the website, draft FAQ entries, and return them for review."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    tenant = (
        db.table("tenants")
        .select("business_name, business_type")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    t = (tenant.data[0] if tenant.data else {}) or {}

    try:
        website_text = await fetch_website_text(req.url)
        faqs = await draft_faq_entries(
            business_name=t.get("business_name") or "",
            business_type=t.get("business_type") or "",
            website_text=website_text,
        )
    except InstantKbError as exc:
        status = _ERROR_STATUS.get(exc.code, 502)
        logger.info("instant_kb.draft rejected tenant=%s code=%s", tenant_id, exc.code)
        raise HTTPException(status_code=status, detail=exc.message)

    logger.info("instant_kb.draft tenant=%s faqs=%d chars=%d", tenant_id, len(faqs), len(website_text))
    return InstantKbDraftResponse(
        faqs=[InstantKbFaqEntry(**f) for f in faqs],
        chars_extracted=len(website_text),
        source_url=req.url,
    )


@router.post("/{tenant_id}/confirm", response_model=InstantKbConfirmResponse)
@limiter.limit("10/hour")
async def confirm_instant_kb(
    request: Request,
    tenant_id: str,
    req: InstantKbConfirmRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Persist the owner-approved FAQ entries."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    entries = [f.model_dump() for f in req.faqs]
    try:
        saved = persist_faq_entries(db, tenant_id, entries)
    except InstantKbError as exc:
        raise HTTPException(status_code=_ERROR_STATUS.get(exc.code, 500), detail=exc.message)

    logger.info("instant_kb.confirm tenant=%s saved=%d", tenant_id, saved)
    return InstantKbConfirmResponse(saved=saved)
