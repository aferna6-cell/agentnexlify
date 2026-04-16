"""Marketing Suite add-on access gate.

Gates 7 features behind `tenants.marketing_addon_active`:
  SEO Audit Hub, Social Media, Marketing Campaigns, Marketing Dashboard,
  A/B Tests, Automation Rules, Trigger Logs.

Used as a FastAPI router-level dependency. Returns 402 Payment Required
when access is missing, with an upgrade URL payload the frontend uses to
trigger the upsell modal.
"""

import logging

from fastapi import Depends, HTTPException

from backend.models.database import get_service_supabase
from backend.services.auth_service import get_current_tenant

logger = logging.getLogger(__name__)


MARKETING_ADDON_UPGRADE_PATH = "/billing/marketing-addon"


def _tenant_has_addon(tenant_id: str) -> bool:
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("marketing_addon_active")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return False
    return bool(result.data[0].get("marketing_addon_active"))


async def require_marketing_addon(
    claims: dict = Depends(get_current_tenant),
) -> dict:
    """Dependency: 402 if tenant lacks the Marketing Suite add-on."""
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")

    if not _tenant_has_addon(tenant_id):
        logger.info(
            "Marketing addon gate blocked tenant=%s on marketing feature", tenant_id
        )
        raise HTTPException(
            status_code=402,
            detail={
                "error": "marketing_addon_required",
                "message": (
                    "This feature requires the Marketing Suite add-on "
                    "($49.99/mo). Subscribe to unlock SEO, social media, "
                    "campaigns, A/B testing, and automation rules."
                ),
                "upgrade_path": MARKETING_ADDON_UPGRADE_PATH,
                "price_usd_monthly": 49.99,
            },
        )
    return claims
