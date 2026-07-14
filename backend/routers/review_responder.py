"""Reviews AI router — approval-gated AI review responses.

Drafts an AI reply to a customer review and holds it for human approval
before anything is posted anywhere. See `backend/services/review_responder.py`
for the invariant (no code path auto-posts) and
`.claude/rules/propose-only-records.md` for why this shape exists.

Endpoints are tenant-scoped from the auth token (no `{tenant_id}` in the
path) — matches the approve-by-dashboard shape of the existing os_* approval
routes rather than the `/api/v1/reviews/{tenant_id}/...` shape used by the
older Reputation Manager router (backend/routers/reviews.py). The two
routers are independent: this one owns `review_responses`
(migrations/168_review_responses.sql), that one owns `reviews`.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.review_responder import (
    approve_response,
    draft_response,
    reject_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["review-responder"])


class ReviewDraftRequest(BaseModel):
    review_text: str = Field(..., min_length=1)
    review_rating: int = Field(..., ge=1, le=5)
    review_id: str | None = None
    external_ref: str | None = None


class ReviewResponseOut(BaseModel):
    id: str
    tenant_id: str
    review_id: str | None = None
    external_ref: str | None = None
    review_text: str
    review_rating: int
    draft_reply: str
    status: str
    approved_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    approved_at: str | None = None


def _approver_from_claims(claims: dict) -> str:
    return claims.get("email") or claims.get("name") or "unknown"


@router.post("/draft", response_model=ReviewResponseOut)
async def create_draft(
    req: ReviewDraftRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Draft an AI reply to a customer review. Always stored as status='draft'."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        row = await draft_response(
            db,
            tenant_id=tenant_id,
            review={
                "review_text": req.review_text,
                "review_rating": req.review_rating,
                "review_id": req.review_id,
                "external_ref": req.external_ref,
            },
        )
    except Exception:
        logger.error(
            "review_responder router: draft failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to draft review response")

    if not row:
        raise HTTPException(status_code=502, detail="Failed to draft review response")
    return row


@router.get("/pending", response_model=list[ReviewResponseOut])
async def list_pending(claims: dict = Depends(_get_current_tenant)):
    """List drafts awaiting approval for the current tenant."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        result = (
            db.table("review_responses")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("status", "draft")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        logger.error(
            "review_responder router: list pending failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to load pending review responses")

    return result.data or []


@router.post("/{response_id}/approve", response_model=ReviewResponseOut)
async def approve(
    response_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Approve a pending draft. Never posts anywhere — records the decision
    only. Posting to the external platform is a separate, not-yet-built
    step (see `review_responder.post_response_stub`)."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        row = await approve_response(
            db,
            tenant_id=tenant_id,
            response_id=response_id,
            approver=_approver_from_claims(claims),
        )
    except Exception:
        logger.error(
            "review_responder router: approve failed tenant=%s id=%s",
            tenant_id,
            response_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to approve review response")

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Review response not found or not eligible for approval",
        )
    return row


@router.post("/{response_id}/reject", response_model=ReviewResponseOut)
async def reject(
    response_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Reject a pending draft."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        row = await reject_response(
            db,
            tenant_id=tenant_id,
            response_id=response_id,
            approver=_approver_from_claims(claims),
        )
    except Exception:
        logger.error(
            "review_responder router: reject failed tenant=%s id=%s",
            tenant_id,
            response_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to reject review response")

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Review response not found or not eligible for rejection",
        )
    return row
