"""Revenue analytics — monthly revenue tracking from paid invoices, MRR, outstanding."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Simple in-memory cache
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


@router.get("/{tenant_id}/revenue")
async def get_revenue_analytics(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Revenue analytics from paid invoices.

    Returns:
    - monthly: list of {month, revenue, invoice_count} for last 12 months
    - total_revenue: sum of all paid invoices in period
    - total_outstanding: sum of sent/viewed/overdue invoices
    - mrr: monthly recurring revenue from recurring invoices
    - avg_invoice_value: average paid invoice amount
    - paid_count: number of paid invoices
    - overdue_count: number of overdue invoices
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"revenue:{tenant_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    now = datetime.now(timezone.utc)
    twelve_months_ago = (now - timedelta(days=365)).isoformat()

    # Fetch all invoices from the last 12 months
    try:
        result = (
            db.table("invoices")
            .select("id, status, total, paid_at, created_at, is_recurring, recurrence_interval, due_date")
            .eq("tenant_id", tenant_id)
            .gte("created_at", twelve_months_ago)
            .order("created_at")
            .limit(5000)
            .execute()
        )
        invoices = result.data or []
    except Exception:
        logger.warning("Revenue analytics: failed to fetch invoices for %s", tenant_id, exc_info=True)
        invoices = []

    # Aggregate monthly revenue from paid invoices
    monthly_revenue: dict[str, float] = defaultdict(float)
    monthly_count: dict[str, int] = defaultdict(int)
    total_revenue = 0.0
    total_outstanding = 0.0
    paid_totals: list[float] = []
    overdue_count = 0
    mrr = 0.0

    for inv in invoices:
        total_amount = float(inv.get("total") or 0)
        status = inv.get("status") or "draft"

        if status == "paid":
            # Use paid_at for month grouping if available, fallback to created_at
            date_str = inv.get("paid_at") or inv.get("created_at") or ""
            if date_str:
                month_key = date_str[:7]  # YYYY-MM
                monthly_revenue[month_key] += total_amount
                monthly_count[month_key] += 1
            total_revenue += total_amount
            paid_totals.append(total_amount)

        elif status in ("sent", "viewed", "overdue"):
            total_outstanding += total_amount
            if status == "overdue":
                overdue_count += 1

    # Calculate MRR from active recurring invoices
    try:
        recurring_result = (
            db.table("invoices")
            .select("total, recurrence_interval")
            .eq("tenant_id", tenant_id)
            .eq("is_recurring", True)
            .in_("status", ["sent", "paid", "viewed"])
            .limit(500)
            .execute()
        )
        for rinv in (recurring_result.data or []):
            amount = float(rinv.get("total") or 0)
            interval = rinv.get("recurrence_interval") or "monthly"
            if interval == "weekly":
                mrr += amount * 4.33  # ~4.33 weeks per month
            elif interval == "biweekly":
                mrr += amount * 2.17
            elif interval == "monthly":
                mrr += amount
            elif interval == "quarterly":
                mrr += amount / 3
            elif interval == "yearly":
                mrr += amount / 12
    except Exception:
        logger.warning("Revenue analytics: failed to calculate MRR for %s", tenant_id, exc_info=True)

    # Build 12-month timeline
    monthly_data = []
    for i in range(12):
        month_dt = now - timedelta(days=30 * (11 - i))
        month_key = month_dt.strftime("%Y-%m")
        monthly_data.append({
            "month": month_key,
            "revenue": round(monthly_revenue.get(month_key, 0), 2),
            "invoice_count": monthly_count.get(month_key, 0),
        })

    avg_invoice = round(sum(paid_totals) / len(paid_totals), 2) if paid_totals else 0

    response = {
        "monthly": monthly_data,
        "total_revenue": round(total_revenue, 2),
        "total_outstanding": round(total_outstanding, 2),
        "mrr": round(mrr, 2),
        "avg_invoice_value": avg_invoice,
        "paid_count": len(paid_totals),
        "overdue_count": overdue_count,
    }

    _cache[cache_key] = (time.time(), response)
    return response
