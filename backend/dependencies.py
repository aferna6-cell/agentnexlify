"""Shared FastAPI dependencies for AgentNexLiFy backend.

Contains utilities that were previously duplicated across router files.
Import from here instead of defining locally in each router.
"""

import logging

from fastapi import Depends, HTTPException

from backend.services.auth_service import get_current_tenant

logger = logging.getLogger(__name__)

# Public alias — all routers use Depends(_get_current_tenant)
_get_current_tenant = get_current_tenant


def require_role(*allowed_roles):
    """FastAPI dependency factory: restrict endpoint to specific roles."""
    async def checker(claims: dict = Depends(_get_current_tenant)):
        role = claims.get("role", "owner")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return claims
    return checker


def verify_tenant(claims: dict, tenant_id: str) -> None:
    """Verify the JWT claims match the requested tenant. Raises 403 if not."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


async def block_demo_role(claims: dict = Depends(_get_current_tenant)) -> dict:
    """Belt-and-suspenders guard for money/destructive routers.

    GH #669 also registers ``DemoRoleBlockMiddleware`` which blocks
    role=demo mutations outside an allowlist. Keep this Depends on billing,
    phone provisioning, and account deletion so money surfaces that share
    allowlisted prefixes (e.g. ``/api/v1/auth``) stay closed to demo JWTs.
    """
    if claims.get("role") == "demo":
        raise HTTPException(
            status_code=403,
            detail="Not available in demo mode — sign up to use this feature",
        )
    return claims


def get_business_context(db, tenant_id: str) -> tuple[str, str]:
    """Fetch business name and type from the tenants table for AI context.

    Returns a tuple of (business_name, business_type). Falls back to safe
    defaults on any error so callers never need to guard this call.
    """
    try:
        result = (
            db.table("tenants")
            .select("business_name, business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return (
                result.data[0].get("business_name") or "the business",
                result.data[0].get("business_type") or "",
            )
    except Exception:
        logger.warning(
            "Failed to fetch business context for tenant %s", tenant_id, exc_info=True
        )
    return ("the business", "")
