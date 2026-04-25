"""Revenue Analytics — unified financial reporting across invoices, pipeline, orders, and bids."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/revenue", tags=["revenue"])

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes
_QUERY_LIMIT = 10000


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    if len(_cache) > 200:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (time.time(), data)


def _period_to_days(period: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _parse_dt(raw: str) -> datetime:
    """Parse an ISO datetime string from Supabase into a timezone-aware datetime."""
    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ------------------------------------------------------------------
# 1. Revenue Overview
# ------------------------------------------------------------------

@router.get("/{tenant_id}/overview")
async def revenue_overview(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Unified revenue overview: invoices + pipeline + orders + bids."""
    verify_tenant(claims, tenant_id)

    cache_key = f"revenue_overview:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days * 2)).isoformat()
    now_iso = now.isoformat()
    db = get_service_supabase()

    # -- Invoices --
    invoice_paid = 0.0
    invoice_outstanding = 0.0
    invoice_overdue = 0.0
    invoice_count = 0
    prev_invoice_paid = 0.0

    try:
        inv_result = (
            db.table("invoices")
            .select("id, status, total, amount_paid, due_date, created_at, paid_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        today_str = now.strftime("%Y-%m-%d")
        for inv in inv_result.data or []:
            created = inv.get("created_at", "")
            total = float(inv.get("total") or 0)
            paid_amount = float(inv.get("amount_paid") or 0)
            status = inv.get("status", "")
            due_date = inv.get("due_date") or ""

            is_current = created >= start

            if is_current:
                invoice_count += 1
                if status == "paid":
                    invoice_paid += total
                elif status in ("sent", "viewed"):
                    if due_date and due_date < today_str:
                        invoice_overdue += total - paid_amount
                    else:
                        invoice_outstanding += total - paid_amount
            else:
                # Previous period
                if status == "paid":
                    prev_invoice_paid += total
    except Exception:
        logger.warning("Revenue: failed to fetch invoices for %s", tenant_id, exc_info=True)

    # -- Pipeline Won Deals --
    pipeline_won = 0.0
    pipeline_value = 0.0
    prev_pipeline_won = 0.0
    won_count = 0

    try:
        # Get won stage names
        stages_result = (
            db.table("pipeline_stages")
            .select("name, is_won")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        won_stage_names = {
            s["name"].lower()
            for s in (stages_result.data or [])
            if s.get("is_won")
        }

        if won_stage_names:
            leads_result = (
                db.table("leads")
                .select("status, deal_value, stage_changed_at, created_at")
                .eq("client_id", tenant_id)
                .limit(_QUERY_LIMIT)
                .execute()
            )
            for lead in leads_result.data or []:
                status_lower = (lead.get("status") or "").lower()
                deal_val = float(lead.get("deal_value") or 0)

                if status_lower not in won_stage_names:
                    pipeline_value += deal_val
                    continue

                changed_at = lead.get("stage_changed_at") or lead.get("created_at") or ""
                if changed_at >= start:
                    pipeline_won += deal_val
                    won_count += 1
                elif changed_at >= prev_start:
                    prev_pipeline_won += deal_val
    except Exception:
        logger.warning("Revenue: failed to fetch pipeline data for %s", tenant_id, exc_info=True)

    # -- Orders (restaurant revenue) --
    order_revenue = 0.0
    order_count = 0
    prev_order_revenue = 0.0

    try:
        orders_result = (
            db.table("orders")
            .select("total, status, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", now_iso)
            .neq("status", "cancelled")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for order in orders_result.data or []:
            total = float(order.get("total") or 0)
            created = order.get("created_at", "")
            if created >= start:
                order_revenue += total
                order_count += 1
            else:
                prev_order_revenue += total
    except Exception:
        logger.warning("Revenue: failed to fetch orders for %s", tenant_id, exc_info=True)

    # -- Bids --
    bid_accepted_value = 0.0
    bid_total_count = 0
    bid_accepted_count = 0
    prev_bid_accepted_value = 0.0

    try:
        bids_result = (
            db.table("bids")
            .select("total, status, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", prev_start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for bid in bids_result.data or []:
            total = float(bid.get("total") or 0)
            created = bid.get("created_at", "")
            status = bid.get("status", "")
            if created >= start:
                bid_total_count += 1
                if status == "accepted":
                    bid_accepted_value += total
                    bid_accepted_count += 1
            else:
                if status == "accepted":
                    prev_bid_accepted_value += total
    except Exception:
        logger.warning("Revenue: failed to fetch bids for %s", tenant_id, exc_info=True)

    # -- Totals --
    total_revenue = round(invoice_paid + pipeline_won + order_revenue + bid_accepted_value, 2)
    prev_total_revenue = round(prev_invoice_paid + prev_pipeline_won + prev_order_revenue + prev_bid_accepted_value, 2)

    bid_win_rate = round(bid_accepted_count / bid_total_count * 100, 1) if bid_total_count > 0 else 0.0

    result = {
        "total_revenue": total_revenue,
        "revenue_change": _pct_change(total_revenue, prev_total_revenue),
        "invoices": {
            "paid": round(invoice_paid, 2),
            "outstanding": round(invoice_outstanding, 2),
            "overdue": round(invoice_overdue, 2),
            "count": invoice_count,
            "paid_change": _pct_change(invoice_paid, prev_invoice_paid),
        },
        "pipeline": {
            "won_value": round(pipeline_won, 2),
            "active_value": round(pipeline_value, 2),
            "won_count": won_count,
            "won_change": _pct_change(pipeline_won, prev_pipeline_won),
        },
        "orders": {
            "revenue": round(order_revenue, 2),
            "count": order_count,
            "revenue_change": _pct_change(order_revenue, prev_order_revenue),
        },
        "bids": {
            "accepted_value": round(bid_accepted_value, 2),
            "total_count": bid_total_count,
            "accepted_count": bid_accepted_count,
            "win_rate": bid_win_rate,
            "accepted_change": _pct_change(bid_accepted_value, prev_bid_accepted_value),
        },
        "period": period,
    }

    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 2. Revenue Over Time (daily breakdown)
# ------------------------------------------------------------------

@router.get("/{tenant_id}/trend")
async def revenue_trend(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Daily revenue breakdown for charting."""
    verify_tenant(claims, tenant_id)

    cache_key = f"revenue_trend:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    now_iso = now.isoformat()
    db = get_service_supabase()

    daily: dict[str, dict[str, float]] = defaultdict(
        lambda: {"invoices": 0.0, "orders": 0.0, "pipeline": 0.0, "bids": 0.0}
    )

    # Invoices: use paid_at for revenue timing (fallback to created_at)
    try:
        inv_result = (
            db.table("invoices")
            .select("total, status, paid_at, created_at")
            .eq("tenant_id", tenant_id)
            .eq("status", "paid")
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for inv in inv_result.data or []:
            date_str = (inv.get("paid_at") or inv.get("created_at", ""))[:10]
            if date_str:
                daily[date_str]["invoices"] += float(inv.get("total") or 0)
    except Exception:
        logger.warning("Revenue trend: invoices query failed for %s", tenant_id, exc_info=True)

    # Orders
    try:
        orders_result = (
            db.table("orders")
            .select("total, created_at")
            .eq("tenant_id", tenant_id)
            .neq("status", "cancelled")
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for order in orders_result.data or []:
            date_str = (order.get("created_at") or "")[:10]
            if date_str:
                daily[date_str]["orders"] += float(order.get("total") or 0)
    except Exception:
        logger.warning("Revenue trend: orders query failed for %s", tenant_id, exc_info=True)

    # Pipeline won deals
    try:
        stages_result = (
            db.table("pipeline_stages")
            .select("name, is_won")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        won_stage_names = {
            s["name"].lower()
            for s in (stages_result.data or [])
            if s.get("is_won")
        }
        if won_stage_names:
            leads_result = (
                db.table("leads")
                .select("status, deal_value, stage_changed_at")
                .eq("client_id", tenant_id)
                .limit(_QUERY_LIMIT)
                .execute()
            )
            for lead in leads_result.data or []:
                if (lead.get("status") or "").lower() not in won_stage_names:
                    continue
                changed = lead.get("stage_changed_at") or ""
                date_str = changed[:10]
                if date_str and changed >= start:
                    daily[date_str]["pipeline"] += float(lead.get("deal_value") or 0)
    except Exception:
        logger.warning("Revenue trend: pipeline query failed for %s", tenant_id, exc_info=True)

    # Bids accepted
    try:
        bids_result = (
            db.table("bids")
            .select("total, status, created_at")
            .eq("tenant_id", tenant_id)
            .eq("status", "accepted")
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for bid in bids_result.data or []:
            date_str = (bid.get("created_at") or "")[:10]
            if date_str:
                daily[date_str]["bids"] += float(bid.get("total") or 0)
    except Exception:
        logger.warning("Revenue trend: bids query failed for %s", tenant_id, exc_info=True)

    # Build complete date range
    today = now.date()
    data = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        entry = daily.get(d, {"invoices": 0.0, "orders": 0.0, "pipeline": 0.0, "bids": 0.0})
        total = round(entry["invoices"] + entry["orders"] + entry["pipeline"] + entry["bids"], 2)
        data.append({
            "date": d,
            "invoices": round(entry["invoices"], 2),
            "orders": round(entry["orders"], 2),
            "pipeline": round(entry["pipeline"], 2),
            "bids": round(entry["bids"], 2),
            "total": total,
        })

    result = {"data": data}
    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 3. Top Customers by Revenue
# ------------------------------------------------------------------

@router.get("/{tenant_id}/top-customers")
async def top_customers(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    limit: int = Query(10, ge=1, le=50),
    claims: dict = Depends(_get_current_tenant),
):
    """Top customers ranked by total revenue (invoices paid + orders)."""
    verify_tenant(claims, tenant_id)

    cache_key = f"revenue_top_customers:{tenant_id}:{period}:{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()
    now_iso = now.isoformat()
    db = get_service_supabase()

    customer_revenue: dict[str, float] = defaultdict(float)
    customer_names: dict[str, str] = {}
    customer_invoice_count: dict[str, int] = defaultdict(int)

    # Paid invoices with lead_id
    try:
        inv_result = (
            db.table("invoices")
            .select("lead_id, total, status, created_at")
            .eq("tenant_id", tenant_id)
            .eq("status", "paid")
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        lead_ids = set()
        for inv in inv_result.data or []:
            lid = inv.get("lead_id")
            if lid:
                customer_revenue[lid] += float(inv.get("total") or 0)
                customer_invoice_count[lid] += 1
                lead_ids.add(lid)

        # Fetch lead names
        if lead_ids:
            leads_result = (
                db.table("leads")
                .select("id, name, email")
                .eq("client_id", tenant_id)
                .limit(_QUERY_LIMIT)
                .execute()
            )
            for lead in leads_result.data or []:
                if lead.get("id") in lead_ids:
                    customer_names[lead["id"]] = lead.get("name") or lead.get("email") or "Unknown"
    except Exception:
        logger.warning("Revenue top-customers: invoices query failed for %s", tenant_id, exc_info=True)

    # Sort by revenue, take top N
    sorted_customers = sorted(customer_revenue.items(), key=lambda x: x[1], reverse=True)[:limit]

    result = {
        "customers": [
            {
                "lead_id": lid,
                "name": customer_names.get(lid, "Unknown"),
                "revenue": round(rev, 2),
                "invoice_count": customer_invoice_count.get(lid, 0),
            }
            for lid, rev in sorted_customers
        ]
    }

    _set_cache(cache_key, result)
    return result


# ------------------------------------------------------------------
# 4. Revenue by Source Breakdown
# ------------------------------------------------------------------

@router.get("/{tenant_id}/breakdown")
async def revenue_breakdown(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Revenue breakdown by source type for pie/donut chart."""
    verify_tenant(claims, tenant_id)

    cache_key = f"revenue_breakdown:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Reuse overview data for the breakdown
    overview = await revenue_overview(tenant_id, period, claims)

    sources = []
    if overview["invoices"]["paid"] > 0:
        sources.append({"source": "Invoices", "value": overview["invoices"]["paid"]})
    if overview["pipeline"]["won_value"] > 0:
        sources.append({"source": "Pipeline Deals", "value": overview["pipeline"]["won_value"]})
    if overview["orders"]["revenue"] > 0:
        sources.append({"source": "Orders", "value": overview["orders"]["revenue"]})
    if overview["bids"]["accepted_value"] > 0:
        sources.append({"source": "Accepted Bids", "value": overview["bids"]["accepted_value"]})

    result = {"sources": sources, "total": overview["total_revenue"]}
    _set_cache(cache_key, result)
    return result
