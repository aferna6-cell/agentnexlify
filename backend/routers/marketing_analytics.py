"""Marketing Analytics endpoints — dashboard metrics and trend data."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.addon_gate import require_marketing_addon

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/marketing",
    tags=["marketing-analytics"],
    dependencies=[Depends(require_marketing_addon)],
)


class DashboardMetrics(BaseModel):
    total_campaigns: int = 0
    campaigns_sent: int = 0
    total_recipients: int = 0
    total_sent: int = 0
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    email_vs_sms_breakdown: dict = Field(default_factory=dict)
    top_performing_campaign: dict | None = None


class TrendDataPoint(BaseModel):
    date: str
    open_rate: float = 0.0
    click_rate: float = 0.0
    send_volume: int = 0


@router.get("/{tenant_id}/dashboard")
async def get_marketing_dashboard(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get marketing dashboard summary metrics for a tenant."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        campaigns_result = (
            db.table("marketing_campaigns")
            .select(
                "id, name, type, status, total_recipients, total_sent, "
                "total_opened, total_clicked, sent_at"
            )
            .eq("tenant_id", tenant_id)
            .execute()
        )
        campaigns = campaigns_result.data or []

        total_campaigns = len(campaigns)
        campaigns_sent = sum(1 for c in campaigns if c.get("status") == "sent")
        total_sent = sum(c.get("total_sent", 0) for c in campaigns)
        total_recipients = sum(c.get("total_recipients", 0) for c in campaigns)

        total_opened = sum(c.get("total_opened", 0) for c in campaigns)
        total_clicked = sum(c.get("total_clicked", 0) for c in campaigns)

        avg_open_rate = (
            round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0.0
        )
        avg_click_rate = (
            round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0.0
        )

        email_campaigns = [c for c in campaigns if c.get("type") == "email"]
        sms_campaigns = [c for c in campaigns if c.get("type") == "sms"]
        email_vs_sms_breakdown = {
            "email": len(email_campaigns),
            "sms": len(sms_campaigns),
        }

        top_campaign = None
        best_rate = 0.0
        for c in campaigns:
            if c.get("total_sent", 0) > 0:
                rate = (c.get("total_opened", 0) / c.get("total_sent", 0)) * 100
                if rate > best_rate:
                    best_rate = rate
                    top_campaign = c

        return {
            "total_campaigns": total_campaigns,
            "campaigns_sent": campaigns_sent,
            "total_recipients": total_recipients,
            "total_sent": total_sent,
            "avg_open_rate": avg_open_rate,
            "avg_click_rate": avg_click_rate,
            "email_vs_sms_breakdown": email_vs_sms_breakdown,
            "top_performing_campaign": top_campaign,
        }
    except Exception:
        logger.exception("Failed to get marketing dashboard for tenant %s", tenant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load marketing dashboard"
        )


@router.get("/{tenant_id}/trends")
async def get_marketing_trends(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    period: str = Query("30d", description="30d or 90d"),
):
    """Get time-series trend data for open rate, click rate, and send volume."""
    verify_tenant(claims, tenant_id)

    days = 90 if period == "90d" else 30
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    try:
        db = get_service_supabase()

        campaigns_result = (
            db.table("marketing_campaigns")
            .select(
                "id, name, type, status, sent_at, total_sent, total_opened, total_clicked"
            )
            .eq("tenant_id", tenant_id)
            .eq("status", "sent")
            .execute()
        )
        campaigns = campaigns_result.data or []

        sends_result = (
            db.table("campaign_sends")
            .select(
                "id, campaign_id, tenant_id, status, sent_at, opened_at, clicked_at"
            )
            .eq("tenant_id", tenant_id)
            .gte("sent_at", start_date)
            .execute()
        )
        sends = sends_result.data or []

        date_map: dict[str, dict] = {}
        for send in sends:
            sent_at = send.get("sent_at", "")
            if not sent_at:
                continue
            date_key = sent_at[:10]
            if date_key not in date_map:
                date_map[date_key] = {"sent": 0, "opened": 0, "clicked": 0}
            status = send.get("status")
            if status in ("sent", "delivered"):
                date_map[date_key]["sent"] += 1
            if status == "opened" or send.get("opened_at"):
                date_map[date_key]["opened"] += 1
            if status == "clicked" or send.get("clicked_at"):
                date_map[date_key]["clicked"] += 1

        trend_data = []
        current = datetime.now(timezone.utc).date()
        for i in range(days):
            date = (current - timedelta(days=i)).isoformat()
            data = date_map.get(date, {"sent": 0, "opened": 0, "clicked": 0})
            sent = data["sent"]
            open_rate = round((data["opened"] / sent * 100), 1) if sent > 0 else 0.0
            click_rate = round((data["clicked"] / sent * 100), 1) if sent > 0 else 0.0
            trend_data.append(
                {
                    "date": date,
                    "open_rate": open_rate,
                    "click_rate": click_rate,
                    "send_volume": sent,
                }
            )

        trend_data.reverse()
        return {"trends": trend_data, "period": period, "days": days}
    except Exception:
        logger.exception("Failed to get marketing trends for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load marketing trends")
