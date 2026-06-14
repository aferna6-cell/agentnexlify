"""Marketing feature plan gate.

The Marketing Suite add-on ($49.99/mo) was retired 2026-06-10 — marketing
features (SEO Hub, Social Media, Campaigns, Marketing Dashboard, A/B Tests,
Automation Rules, Trigger Logs) are now included with the Growth tier
(`autopilot`) and above, and surfaced primarily through the Agent OS
marketing department rather than standalone dashboard pages.

Used as a FastAPI router-level dependency. Returns 402 Payment Required with
an upgrade payload when the tenant's plan is below the Growth tier.
"""

import logging

from fastapi import Depends, HTTPException

from backend.models.database import get_service_supabase
from backend.services.auth_service import get_current_tenant

logger = logging.getLogger(__name__)

MARKETING_PLANS = {"autopilot", "professional", "enterprise"}
MARKETING_UPGRADE_PATH = "/billing"


def _tenant_plan(tenant_id: str) -> str:
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return ""
    return str(result.data[0].get("plan") or "")


async def require_marketing_access(
    claims: dict = Depends(get_current_tenant),
) -> dict:
    """Dependency: 402 if the tenant's plan does not include marketing."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")

    plan = _tenant_plan(tenant_id)
    if plan not in MARKETING_PLANS:
        logger.info(
            "Marketing plan gate blocked tenant=%s plan=%s", tenant_id, plan
        )
        raise HTTPException(
            status_code=402,
            detail={
                "error": "plan_upgrade_required",
                "message": (
                    "Marketing tools (SEO, social media, campaigns, A/B "
                    "testing, automation rules) are included with the Growth "
                    "plan and above. Upgrade to unlock them — your AI staff "
                    "in Agent OS will put them to work for you."
                ),
                "upgrade_path": MARKETING_UPGRADE_PATH,
            },
        )
    return claims
