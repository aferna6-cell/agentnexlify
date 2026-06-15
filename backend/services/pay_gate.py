"""Pay-gate helpers - block new unpaid tenants from accessing the product.

Existing tenants are grandfathered via pay_gate_exempt=true (migration 152).
New tenants default to pay_gate_exempt=false and must complete Stripe checkout
before the dashboard or onboarding-complete endpoints are usable.

No `from __future__ import annotations` - this file is imported in FastAPI
route handlers (breaks Pydantic model resolution).
"""

import logging

from fastapi import Depends, HTTPException

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"active", "trialing"}


def is_pay_gated(tenant_row: dict) -> bool:
    """Return True when the tenant must pay before accessing the product.

    A tenant is gated when BOTH conditions are true:
    - pay_gate_exempt is falsy (not grandfathered)
    - plan_status is not in {"active", "trialing"}
    """
    exempt = bool(tenant_row.get("pay_gate_exempt"))
    if exempt:
        return False
    plan_status = tenant_row.get("plan_status") or ""
    return plan_status not in _ACTIVE_STATUSES


async def require_active_plan(claims: dict = Depends(_get_current_tenant)) -> dict:
    """FastAPI dependency - raises HTTP 402 for unpaid non-exempt tenants.

    Usage:
        @router.post("/some-endpoint")
        async def handler(claims: dict = Depends(require_active_plan)):
            ...

    Raises:
        HTTPException(402) with {"error": "payment_required", "upgrade_path": "/billing"}
    """
    tenant_id = claims["tenant_id"]

    try:
        db = get_service_supabase()
        result = (
            db.table("tenants")
            .select("id, pay_gate_exempt, plan_status")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("pay_gate: DB error for tenant %s", tenant_id, exc_info=exc)
        # Fail open on DB error - don't block the user on an infra issue
        return claims

    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_row = result.data[0]
    if is_pay_gated(tenant_row):
        raise HTTPException(
            status_code=402,
            detail={"error": "payment_required", "upgrade_path": "/billing"},
        )

    return claims
