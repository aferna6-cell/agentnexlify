"""Webhook delivery log endpoint — shows recent deliveries per webhook."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.get("/{tenant_id}/{webhook_id}/deliveries")
async def list_webhook_deliveries(
    tenant_id: str,
    webhook_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    claims: dict = Depends(_get_current_tenant),
):
    """Return recent webhook_logs for a specific webhook."""
    verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    # Verify webhook belongs to tenant
    try:
        wh_check = (
            db.table("webhooks")
            .select("id")
            .eq("id", webhook_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to verify webhook %s for tenant %s", webhook_id, tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load webhook")

    if not wh_check.data:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Fetch recent logs
    try:
        result = (
            db.table("webhook_logs")
            .select("id, webhook_id, event, payload, response_status, success, created_at")
            .eq("webhook_id", webhook_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch webhook logs for webhook %s", webhook_id)
        raise HTTPException(status_code=500, detail="Failed to load delivery logs")

    deliveries = result.data or []

    # Compute summary stats from full set (not just the paginated page)
    try:
        total_res = (
            db.table("webhook_logs")
            .select("success")
            .eq("webhook_id", webhook_id)
            .execute()
        )
        all_logs = total_res.data or []
        total = len(all_logs)
        succeeded = sum(1 for d in all_logs if d.get("success"))
        failed = total - succeeded
    except Exception:
        # Fall back to page-level stats if the count query fails
        total = len(deliveries)
        succeeded = sum(1 for d in deliveries if d.get("success"))
        failed = total - succeeded

    return {
        "deliveries": deliveries,
        "summary": {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
        },
    }
