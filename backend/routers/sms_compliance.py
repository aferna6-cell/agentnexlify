"""SMS compliance dashboard — view and manage opt-outs.

Read/manage surface over the sms_opt_outs ledger (migration 160). The
enforcement gate lives in backend/services/sms_compliance.py — every outbound
SMS path calls is_suppressed() there; this router only exposes the ledger to
the dashboard and lets the owner record manual opt-outs/opt-ins.

client_id (not tenant_id) on sms_opt_outs — matches leads/conversations.
Phone numbers are masked to last 4 digits in every response.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.sms_compliance import last10, record_opt_in, record_opt_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sms-compliance", tags=["sms-compliance"])


class OptOutRow(BaseModel):
    id: str
    phone_masked: str
    source: str | None = None
    created_at: str


class OptOutListResponse(BaseModel):
    items: list[OptOutRow]
    total: int


class ManualPhoneRequest(BaseModel):
    phone: str


@router.get("/opt-outs", response_model=OptOutListResponse)
async def list_opt_outs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    offset = (page - 1) * per_page
    result = (
        db.table("sms_opt_outs")
        .select("id, phone_last10, source, created_at", count="exact")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )

    items = []
    for row in result.data or []:
        p = row.get("phone_last10") or ""
        items.append(
            OptOutRow(
                id=str(row["id"]),
                phone_masked=f"***-***-{p[-4:]}" if len(p) >= 4 else "****",
                source=row.get("source"),
                created_at=row.get("created_at") or "",
            )
        )

    return OptOutListResponse(items=items, total=result.count or 0)


@router.get("/stats")
async def opt_out_stats(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    result = (
        db.table("sms_opt_outs")
        .select("id", count="exact")
        .eq("client_id", client_id)
        .execute()
    )
    return {"total_opt_outs": result.count or 0}


@router.post("/opt-out")
async def manual_opt_out(
    req: ManualPhoneRequest,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    if not last10(req.phone):
        raise HTTPException(status_code=400, detail="Invalid phone number")
    db = get_service_supabase()
    record_opt_out(db, client_id, req.phone, source="manual_dashboard")
    return {"success": True, "detail": "Opt-out recorded"}


@router.post("/opt-in")
async def manual_opt_in(
    req: ManualPhoneRequest,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    if not last10(req.phone):
        raise HTTPException(status_code=400, detail="Invalid phone number")
    db = get_service_supabase()
    record_opt_in(db, client_id, req.phone)
    return {"success": True, "detail": "Opt-in recorded (opt-out removed)"}
