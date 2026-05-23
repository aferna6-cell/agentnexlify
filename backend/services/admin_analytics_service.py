"""Platform-wide admin analytics aggregation logic.

Pulled out of `backend/routers/admin_analytics.py` so the router stays
focused on auth + HTTP. Owns the pure DB queries + aggregations for
overview, growth trends, plan distribution, revenue, and breakdowns.

DB helper accepts `db: Any` so test patches at
`backend.routers.admin_analytics.get_service_supabase` still apply.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


PLAN_PRICES: dict[str, int] = {
    "growth": 9900,
    "professional": 15000,
    "autopilot": 29900,
    "enterprise": 25000,
}


def _step_back_calendar_months(now: datetime, months: int) -> datetime:
    """Step back N calendar months from `now`, snap to day 1 / midnight UTC."""
    m = now.month - (months - 1)
    y = now.year
    while m <= 0:
        m += 12
        y -= 1
    return now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month(current: datetime) -> datetime:
    if current.month == 12:
        return current.replace(year=current.year + 1, month=1)
    return current.replace(month=current.month + 1)


def compute_platform_overview(db: Any) -> dict[str, Any]:
    """Total tenants, active paid subs, MRR, signups, churn, promotions."""
    total_tenants = (
        db.table("tenants").select("id", count="exact").execute()
    ).count or 0

    active_result = (
        db.table("tenants")
        .select("plan, stripe_subscription_id")
        .eq("plan_status", "active")
        .neq("plan", "free")
        .execute()
    )
    active_paid = [
        t for t in active_result.data or []
        if t.get("stripe_subscription_id")
    ]
    active_count = len(active_paid)

    plan_breakdown: dict[str, int] = {}
    for t in active_result.data or []:
        plan = t.get("plan", "unknown")
        plan_breakdown[plan] = plan_breakdown.get(plan, 0) + 1

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    new_this_month = (
        db.table("tenants")
        .select("id", count="exact")
        .gte("created_at", month_start)
        .execute()
    ).count or 0

    try:
        churned_this_month = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("plan_status", "cancelled")
            .gte("updated_at", month_start)
            .execute()
        ).count or 0
    except Exception:
        churned_this_month = 0

    try:
        free_trial_active = (
            db.table("tenants")
            .select("id", count="exact")
            .eq("plan", "free")
            .eq("plan_status", "active")
            .not_.is_("free_trial_started_at", "null")
            .execute()
        ).count or 0
    except Exception:
        free_trial_active = 0

    promoted_count = 0
    try:
        promoted = (
            db.table("admin_promotions")
            .select("tenant_id")
            .not_.is_("tenant_id", "null")
            .execute()
        )
        promoted_count = len({
            row.get("tenant_id")
            for row in (promoted.data or [])
            if row.get("tenant_id")
        })
    except Exception:
        logger.warning("Failed to fetch promoted tenants count", exc_info=True)

    mrr_cents = sum(PLAN_PRICES.get(t.get("plan", ""), 0) for t in active_paid)

    return {
        "total_tenants": total_tenants,
        "active_paid_subscriptions": active_count,
        "mrr_cents": mrr_cents,
        "mrr_dollars": round(mrr_cents / 100, 2),
        "plan_breakdown": plan_breakdown,
        "new_signups_this_month": new_this_month,
        "churned_this_month": churned_this_month,
        "free_trial_active": free_trial_active,
        "promoted_business": promoted_count,
    }


def compute_monthly_growth(db: Any, months: int) -> dict[str, Any]:
    """Month-by-month new signups + plan breakdown + cumulative totals."""
    now = datetime.now(timezone.utc)
    start_month = _step_back_calendar_months(now, months)

    signups_result = (
        db.table("tenants")
        .select("created_at, plan, plan_status")
        .gte("created_at", start_month.isoformat())
        .order("created_at")
        .execute()
    )
    signups = signups_result.data or []

    monthly_data: dict[str, dict] = {}
    current = start_month
    while current <= now:
        key = current.strftime("%Y-%m")
        monthly_data[key] = {
            "month": key,
            "new_signups": 0,
            "total_at_end": 0,
            "plan_breakdown": {},
            "new_paid": 0,
            "new_free": 0,
        }
        current = _next_month(current)

    for s in signups:
        created = s.get("created_at", "")
        if not created:
            continue
        key = created[:7]
        if key in monthly_data:
            monthly_data[key]["new_signups"] += 1
            plan = s.get("plan", "free")
            breakdown = monthly_data[key]["plan_breakdown"]
            breakdown[plan] = breakdown.get(plan, 0) + 1
            if plan != "free":
                monthly_data[key]["new_paid"] += 1
            else:
                monthly_data[key]["new_free"] += 1

    cumulative = 0
    sorted_months = sorted(monthly_data.keys())
    for m in sorted_months:
        cumulative += monthly_data[m]["new_signups"]
        monthly_data[m]["total_at_end"] = cumulative

    churned_result = (
        db.table("platform_monthly_revenue")
        .select("month, churned")
        .gte("month", start_month.replace(day=1).isoformat()[:10])
        .execute()
    )
    for row in churned_result.data or []:
        key = row["month"][:7] if row.get("month") else ""
        if key in monthly_data:
            monthly_data[key]["churned"] = row.get("churned", 0)

    return {
        "monthly_data": [monthly_data[k] for k in sorted_months],
        "total_months": len(sorted_months),
    }


def compute_weekly_growth(db: Any) -> dict[str, Any]:
    """Day-by-day signups + revenue for the trailing 7-day window."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    signups_result = (
        db.table("tenants")
        .select("id, business_name, plan, plan_status, created_at, owner_email")
        .gte("created_at", week_ago.isoformat())
        .order("created_at", desc=True)
        .execute()
    )
    signups = signups_result.data or []

    daily_data: dict[str, dict] = {}
    for i in range(7):
        day = (now - timedelta(days=6 - i)).date()
        key = day.isoformat()
        daily_data[key] = {
            "date": key,
            "label": day.strftime("%a %d"),
            "signups": 0,
            "paid": 0,
            "free": 0,
            "revenue_cents": 0,
        }

    for s in signups:
        created = s.get("created_at", "")
        if not created:
            continue
        key = created[:10]
        if key in daily_data:
            daily_data[key]["signups"] += 1
            plan = s.get("plan", "free")
            if plan != "free":
                daily_data[key]["paid"] += 1
                daily_data[key]["revenue_cents"] += PLAN_PRICES.get(plan, 0)
            else:
                daily_data[key]["free"] += 1

    active_paid = (
        db.table("tenants")
        .select("plan, stripe_subscription_id")
        .eq("plan_status", "active")
        .neq("plan", "free")
        .execute()
    )
    active_data = active_paid.data or []
    active_count = len([t for t in active_data if t.get("stripe_subscription_id")])

    two_weeks_ago = now - timedelta(days=14)
    prev_week_signups = (
        db.table("tenants")
        .select("id", count="exact")
        .gte("created_at", two_weeks_ago.isoformat())
        .lt("created_at", week_ago.isoformat())
        .execute()
    ).count or 0
    this_week_signups = len(signups)

    week_delta = this_week_signups - prev_week_signups
    week_delta_pct = 0
    if prev_week_signups > 0:
        week_delta_pct = round((week_delta / prev_week_signups) * 100, 0)

    return {
        "daily_data": [daily_data[k] for k in sorted(daily_data.keys())],
        "this_week_signups": this_week_signups,
        "this_week_paid": sum(d["paid"] for d in daily_data.values()),
        "this_week_revenue_cents": sum(d["revenue_cents"] for d in daily_data.values()),
        "active_paid_subscriptions": active_count,
        "week_delta": week_delta,
        "week_delta_pct": week_delta_pct,
    }


def compute_plan_distribution(db: Any) -> dict[str, Any]:
    """Current distribution of plans across all tenants."""
    result = (
        db.table("tenants")
        .select("plan, plan_status")
        .execute()
    )
    tenants = result.data or []

    plan_counts: dict[str, dict[str, int]] = {}
    for t in tenants:
        plan = t.get("plan", "unknown")
        status = t.get("plan_status", "unknown")
        if plan not in plan_counts:
            plan_counts[plan] = {"active": 0, "cancelled": 0, "paused": 0}
        plan_counts[plan][status] = plan_counts[plan].get(status, 0) + 1

    total = len(tenants)
    distribution = []
    for plan, counts in sorted(plan_counts.items()):
        total_plan = sum(counts.values())
        distribution.append({
            "plan": plan,
            "active": counts.get("active", 0),
            "cancelled": counts.get("cancelled", 0),
            "paused": counts.get("paused", 0),
            "total": total_plan,
            "percentage": round(total_plan / total * 100, 1) if total > 0 else 0,
        })

    return {
        "total_tenants": total,
        "distribution": distribution,
    }


def _calculate_live_revenue(
    db: Any, start_month: datetime, now: datetime
) -> dict[str, Any]:
    """Live MRR calculation when platform_monthly_revenue is missing."""
    paid_tenants = (
        db.table("tenants")
        .select("id, plan, plan_status, stripe_subscription_id, created_at")
        .neq("plan", "free")
        .execute()
    ).data or []

    monthly_data = []
    current = start_month
    while current <= now:
        month_key = current.strftime("%Y-%m")

        month_revenue_cents = 0
        month_subscriptions = 0
        new_signups = sum(
            1
            for t in paid_tenants
            if t.get("created_at", "")[:7] == month_key
        )

        for t in paid_tenants:
            created = t.get("created_at", "")
            if created and created[:7] > month_key:
                continue
            if t.get("plan_status") == "active" and t.get("stripe_subscription_id"):
                month_revenue_cents += PLAN_PRICES.get(t.get("plan", ""), 0)
                month_subscriptions += 1

        monthly_data.append({
            "month": month_key + "-01",
            "mrr_cents": month_revenue_cents,
            "mrr_dollars": round(month_revenue_cents / 100, 2),
            "total_subscriptions": month_subscriptions,
            "new_signups": new_signups,
            "churned": 0,
        })

        current = _next_month(current)

    return {
        "revenue_trends": monthly_data,
        "source": "live",
    }


def compute_revenue_trends(db: Any, months: int) -> dict[str, Any]:
    """Pre-computed monthly revenue with live fallback when table empty/missing."""
    now = datetime.now(timezone.utc)
    start_month = _step_back_calendar_months(now, months)

    try:
        result = (
            db.table("platform_monthly_revenue")
            .select("*")
            .gte("month", start_month.isoformat()[:10])
            .order("month")
            .execute()
        )
        rows = result.data or []
        if not rows:
            return _calculate_live_revenue(db, start_month, now)
        return {"revenue_trends": rows, "source": "precomputed"}
    except Exception:
        try:
            start_month_fallback = (now.replace(day=1) - timedelta(days=30 * (months - 1))).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            return _calculate_live_revenue(db, start_month_fallback, now)
        except Exception:
            return {"revenue_trends": [], "source": "unavailable"}


def list_promoted_businesses(db: Any) -> dict[str, Any]:
    """All businesses with free access or discounts; tolerates missing table."""
    try:
        result = (
            db.table("admin_promotions")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"promotions": result.data or []}
    except Exception:
        return {"promotions": [], "note": "Apply migration 089 to enable promotion tracking"}


def list_admin_tenants(
    db: Any,
    *,
    plan: str | None,
    plan_status: str | None,
    business_type: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Paginated admin-view tenant list with optional filters + search."""
    query = db.table("tenants").select(
        "id, business_name, business_type, owner_email, owner_name, "
        "plan, plan_status, stripe_subscription_id, created_at, "
        "free_trial_started_at, city",
        count="exact",
    )

    if plan:
        query = query.eq("plan", plan)
    if plan_status:
        query = query.eq("plan_status", plan_status)
    if business_type:
        query = query.eq("business_type", business_type)
    if search:
        search_term = search.strip().replace(",", " ")
        search_pattern = f"%{search_term}%"
        query = query.or_(
            "business_name.ilike.{p},owner_email.ilike.{p},owner_name.ilike.{p}".format(
                p=search_pattern
            )
        )

    query = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    result = query.execute()
    return {"tenants": result.data or [], "total": result.count or 0}


def compute_industry_breakdown(db: Any) -> dict[str, Any]:
    """Tenant distribution by business_type with paid/free split."""
    result = (
        db.table("tenants")
        .select("business_type, plan")
        .execute()
    )
    tenants = result.data or []

    industry_counts: dict[str, dict[str, int]] = {}
    for t in tenants:
        btype = t.get("business_type", "other")
        plan = t.get("plan", "free")
        if btype not in industry_counts:
            industry_counts[btype] = {"total": 0, "paid": 0, "free": 0}
        industry_counts[btype]["total"] += 1
        if plan != "free":
            industry_counts[btype]["paid"] += 1
        else:
            industry_counts[btype]["free"] += 1

    breakdown = [
        {
            "industry": industry,
            **counts,
            "paid_percentage": round(
                counts["paid"] / counts["total"] * 100, 1
            )
            if counts["total"] > 0
            else 0,
        }
        for industry, counts in sorted(
            industry_counts.items(), key=lambda x: x[1]["total"], reverse=True
        )
    ]

    return {"breakdown": breakdown}
