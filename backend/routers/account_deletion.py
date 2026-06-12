"""GDPR / CCPA account deletion endpoint (launch rubric 1.3).

POST /api/v1/account/delete permanently erases the calling tenant: every
tenant-scoped row, the Stripe customer (cancelling subscriptions), and the
tenants row itself. Owner-only, rate-limited, and gated on the caller typing
DELETE explicitly — this is the single most destructive endpoint in the API.

client_id is always the JWT tenant_id — never a path/body value.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant, block_demo_role
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.account_deletion import delete_tenant_account

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/account",
    tags=["account"],
    dependencies=[Depends(block_demo_role)],
)


class AccountDeleteRequest(BaseModel):
    confirm: str = Field(min_length=1, max_length=32)


@router.post("/delete")
@limiter.limit("3/hour")
async def delete_account(
    request: Request,
    req: AccountDeleteRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Permanently delete this account and all of its data.

    Requirements: owner role + ``confirm`` body field equal to "DELETE".
    Irreversible. Returns a per-table purge report for the audit trail.
    """
    role = (claims.get("role") or "").lower()
    if role != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")
    if req.confirm != "DELETE":
        raise HTTPException(
            status_code=400,
            detail='Type "DELETE" in the confirm field to erase this account.',
        )

    client_id = claims["tenant_id"]
    db = get_service_supabase()
    logger.warning("GDPR deletion requested client_id=%s", client_id)
    report = delete_tenant_account(db, client_id)
    return {"status": "deleted", **report.as_dict()}
