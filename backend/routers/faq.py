"""FAQ CRUD endpoints — extracted from auth.py (Phase-2 Rule 9 split)."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import FaqCreateRequest, FaqEntryResponse
from backend.dependencies import block_demo_role, require_role
from backend.services.auth_service import get_current_tenant as _get_current_tenant
from backend.services import faq_service as _faq_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["faq"])


@router.get("/faq/{tenant_id}", response_model=list[FaqEntryResponse])
async def list_faq(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return [FaqEntryResponse(**row) for row in _faq_svc.list_faqs(tenant_id)]


@router.post("/faq/{tenant_id}", response_model=FaqEntryResponse, status_code=201)
async def create_faq(
    tenant_id: str,
    req: FaqCreateRequest,
    claims: dict = Depends(block_demo_role),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    row = _faq_svc.create_faq(tenant_id, req.question, req.answer, req.category)
    return FaqEntryResponse(
        id=str(row["id"]),
        question=row["question"],
        answer=row["answer"],
        category=row.get("category"),
        is_active=row.get("is_active", True),
    )


@router.put("/faq/{tenant_id}/{faq_id}", response_model=FaqEntryResponse)
async def update_faq(
    tenant_id: str,
    faq_id: str,
    req: FaqCreateRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update an existing FAQ entry."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _faq_svc.update_faq(
        tenant_id, faq_id, req.question, req.answer, req.category
    )


@router.delete("/faq/{tenant_id}/{faq_id}", status_code=204)
async def delete_faq(
    tenant_id: str,
    faq_id: str,
    claims: dict = Depends(block_demo_role),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    _faq_svc.delete_faq(tenant_id, faq_id)
