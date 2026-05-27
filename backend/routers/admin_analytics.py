"""Platform-wide admin analytics — cross-tenant growth, revenue, and plan metrics.

All endpoints are protected by the API secret key (not JWT), since these are
internal admin tools for AgentNexLiFy staff only.
"""

import logging
from starlette.requests import Request
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["platform-admin"])


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None = Header(None)) -> None:
    """Verify the caller has the platform admin secret."""
    import hmac as _hmac

    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not _hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


# --- Platform Overview ---


@router.get("/overview")
@limiter.limit("10/minute")
async def get_platform_overview(
    request: Request, x_api_secret: str | None = Header(None)
):
    """Get platform-wide overview: total tenants, active subscriptions, MRR."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        # Total tenants
        total_tenants = (
            db.table("tenants").select("id", count="exact").execute()
        ).count or 0

        # Active paid subscriptions
        active_result = (
            db.table("tenants")
            .select("plan, stripe_subscription_id")
            .eq("plan_status", "active")
            .neq("plan", "free")
            .execute()
        )
        active_paid = [
            t for t in active_result.data or [] if t.get("stripe_subscription_id")
        ]
        active_count = len(active_paid)

        # Plan breakdown
        plan_breakdown = {}
        for t in active_result.data or []:
            plan = t.get("plan", "unknown")
            plan_breakdown[plan] = plan_breakdown.get(plan, 0) + 1

        # This month's new signups
        month_start = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
        )
        new_this_month = (
            db.table("tenants")
            .select("id", count="exact")
            .gte("created_at", month_start)
            .execute()
        ).count or 0

        # Churned this month (cancelled subscriptions)
        try:
            churned_this_month = (
                db.table("tenants")
                .select("id", count="exact")
                .eq("plan_status", "cancelled")
                .gte("updated_at", month_start)
                .execute()
            ).count or 0
        except Exception:
            # updated_at column may not exist yet
            churned_this_month = 0

        # Free trial stats
        try:
            free_trial_active = (
                db.table("tenants")
                .select("id", count="exact")
                .eq("plan", "free")
                .eq("plan_status", "active")
                .filter("free_trial_started_at", "not.is", "null")
                .execute()
            ).count or 0
        except Exception:
            free_trial_active = 0

        # Businesses with admin promotions (table may not exist yet)
        promoted_count = 0
        try:
            promoted = (
                db.table("admin_promotions")
                .select("tenant_id")
                .filter("tenant_id", "not.is", "null")
                .execute()
            )
            promoted_count = len(
                {
                    row.get("tenant_id")
                    for row in (promoted.data or [])
                    if row.get("tenant_id")
                }
            )
        except Exception:
            logger.warning("Failed to fetch promoted tenants count", exc_info=True)

        # MRR calculation (rough estimate from active plans)
        PLAN_PRICES = {
            "growth": 9900,
            "professional": 15000,
            "autopilot": 29900,
            "enterprise": 25000,
        }
        mrr_cents = 0
        for t in active_paid:
            mrr_cents += PLAN_PRICES.get(t.get("plan", ""), 0)

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

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get platform overview")
        raise HTTPException(status_code=500, detail="Failed to load platform overview")


# --- Monthly Growth Trends ---


@limiter.limit("10/minute")
@router.get("/monthly-growth")
async def get_monthly_growth(
    request: Request,
    x_api_secret: str | None = Header(None),
    months: int = Query(12, ge=1, le=36),
):
    """Get month-by-month growth data for the past N months."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        # Calculate the start month
        now = datetime.now(timezone.utc)
        # Step back by calendar months (not timedelta) to avoid skipping months
        m = now.month - (months - 1)
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        start_month = now.replace(
            year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # New signups per month
        signups_result = (
            db.table("tenants")
            .select("created_at, plan, plan_status")
            .gte("created_at", start_month.isoformat())
            .order("created_at")
            .execute()
        )
        signups = signups_result.data or []

        # Aggregate by month
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
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        for s in signups:
            created = s.get("created_at", "")
            if not created:
                continue
            key = created[:7]  # YYYY-MM
            if key in monthly_data:
                monthly_data[key]["new_signups"] += 1
                plan = s.get("plan", "free")
                breakdown = monthly_data[key]["plan_breakdown"]
                breakdown[plan] = breakdown.get(plan, 0) + 1
                if plan != "free":
                    monthly_data[key]["new_paid"] += 1
                else:
                    monthly_data[key]["new_free"] += 1

        # Calculate cumulative totals
        cumulative = 0
        sorted_months = sorted(monthly_data.keys())
        for m in sorted_months:
            cumulative += monthly_data[m]["new_signups"]
            monthly_data[m]["total_at_end"] = cumulative

        # Churned per month (from platform_monthly_revenue if available)
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

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get monthly growth")
        raise HTTPException(status_code=500, detail="Failed to load monthly growth")


# --- Weekly Growth (Last 7 Days) ---


@limiter.limit("10/minute")
@router.get("/weekly-growth")
async def get_weekly_growth(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Get day-by-day growth for the last 7 days — the quick 'what happened this week' view."""
    _verify_admin_secret(x_api_secret)

    PLAN_PRICES = {
        "growth": 9900,
        "professional": 15000,
        "autopilot": 29900,
        "enterprise": 25000,
    }

    try:
        db = get_service_supabase()

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # All tenants created in the last 7 days
        signups_result = (
            db.table("tenants")
            .select("id, business_name, plan, plan_status, created_at, owner_email")
            .gte("created_at", week_ago.isoformat())
            .order("created_at", desc=True)
            .execute()
        )
        signups = signups_result.data or []

        # Daily breakdown
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
            key = created[:10]  # YYYY-MM-DD
            if key in daily_data:
                daily_data[key]["signups"] += 1
                plan = s.get("plan", "free")
                if plan != "free":
                    daily_data[key]["paid"] += 1
                    daily_data[key]["revenue_cents"] += PLAN_PRICES.get(plan, 0)
                else:
                    daily_data[key]["free"] += 1

        # Current active paid subs
        active_paid = (
            db.table("tenants")
            .select("plan, stripe_subscription_id")
            .eq("plan_status", "active")
            .neq("plan", "free")
            .execute()
        )
        active_data = active_paid.data or []
        active_count = len([t for t in active_data if t.get("stripe_subscription_id")])

        # New this week vs previous week
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
            "this_week_revenue_cents": sum(
                d["revenue_cents"] for d in daily_data.values()
            ),
            "active_paid_subscriptions": active_count,
            "week_delta": week_delta,
            "week_delta_pct": week_delta_pct,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get weekly growth")
        raise HTTPException(status_code=500, detail="Failed to load weekly growth")


# --- Plan Distribution ---


@limiter.limit("10/minute")
@router.get("/plan-distribution")
async def get_plan_distribution(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Get current distribution of plans across all tenants."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        result = db.table("tenants").select("plan, plan_status").execute()
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
            distribution.append(
                {
                    "plan": plan,
                    "active": counts.get("active", 0),
                    "cancelled": counts.get("cancelled", 0),
                    "paused": counts.get("paused", 0),
                    "total": total_plan,
                    "percentage": (
                        round(total_plan / total * 100, 1) if total > 0 else 0
                    ),
                }
            )

        return {
            "total_tenants": total,
            "distribution": distribution,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get plan distribution")
        raise HTTPException(status_code=500, detail="Failed to load plan distribution")


# --- Revenue Trends ---


@limiter.limit("10/minute")
@router.get("/revenue-trends")
async def get_revenue_trends(
    request: Request,
    x_api_secret: str | None = Header(None),
    months: int = Query(12, ge=1, le=36),
):
    """Get monthly revenue trends from pre-computed aggregates."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        now = datetime.now(timezone.utc)
        # Step back by calendar months (not timedelta) to avoid skipping months
        m = now.month - (months - 1)
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        start_month = now.replace(
            year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0
        )

        result = (
            db.table("platform_monthly_revenue")
            .select("*")
            .gte("month", start_month.isoformat()[:10])
            .order("month")
            .execute()
        )

        rows = result.data or []

        # If no pre-computed data, calculate live from tenants
        if not rows:
            return await _calculate_live_revenue(db, start_month, now, months)

        return {
            "revenue_trends": rows,
            "source": "precomputed",
        }

    except Exception:
        # Table may not exist yet, fall back to live calculation
        try:
            db = get_service_supabase()
            now = datetime.now(timezone.utc)
            start_month = (
                now.replace(day=1) - timedelta(days=30 * (months - 1))
            ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return await _calculate_live_revenue(db, start_month, now, months)
        except Exception:
            return {"revenue_trends": [], "source": "unavailable"}


async def _calculate_live_revenue(db, start_month, now, months):
    """Calculate revenue live from tenant data when no pre-computed aggregates exist."""
    PLAN_PRICES = {
        "growth": 9900,
        "professional": 15000,
        "autopilot": 29900,
        "enterprise": 25000,
    }

    # Get all tenants with paid plans
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

        # Count tenants who had active paid subscription during this month
        month_revenue_cents = 0
        month_subscriptions = 0
        new_signups = sum(
            1 for t in paid_tenants if t.get("created_at", "")[:7] == month_key
        )

        for t in paid_tenants:
            # Tenant existed during this month
            created = t.get("created_at", "")
            if created and created[:7] > month_key:
                continue

            if t.get("plan_status") == "active" and t.get("stripe_subscription_id"):
                month_revenue_cents += PLAN_PRICES.get(t.get("plan", ""), 0)
                month_subscriptions += 1

        monthly_data.append(
            {
                "month": month_key + "-01",
                "mrr_cents": month_revenue_cents,
                "mrr_dollars": round(month_revenue_cents / 100, 2),
                "total_subscriptions": month_subscriptions,
                "new_signups": new_signups,
                "churned": 0,  # Would need historical tracking for accurate churn
            }
        )

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return {
        "revenue_trends": monthly_data,
        "source": "live",
    }


# --- Promoted / Free Businesses ---


@limiter.limit("10/minute")
@router.get("/promoted-businesses")
async def get_promoted_businesses(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Get all businesses that have been given free access or discounts."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        result = (
            db.table("admin_promotions")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return {"promotions": result.data or []}

    except Exception:
        # Table may not exist until migration is applied
        return {
            "promotions": [],
            "note": "Apply migration 089 to enable promotion tracking",
        }


# --- Tenant List (Admin View) ---


@limiter.limit("10/minute")
@router.get("/tenants")
async def list_all_tenants(
    request: Request,
    x_api_secret: str | None = Header(None),
    plan: str | None = Query(None),
    plan_status: str | None = Query(None),
    business_type: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all tenants with admin-level details (not tenant-scoped)."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

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
            # PostgREST OR expression; comma must be removed to avoid splitting clauses.
            search_term = search.strip().replace(",", " ")
            search_pattern = f"%{search_term}%"
            query = query.or_(
                "business_name.ilike.{p},owner_email.ilike.{p},owner_name.ilike.{p}".format(
                    p=search_pattern
                )
            )

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        result = query.execute()
        tenants = result.data or []
        total = result.count or 0

        return {"tenants": tenants, "total": total}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list tenants")
        raise HTTPException(status_code=500, detail="Failed to list tenants")


# --- Industry Breakdown ---


@limiter.limit("10/minute")
@router.get("/industry-breakdown")
async def get_industry_breakdown(
    request: Request,
    x_api_secret: str | None = Header(None),
):
    """Get tenant distribution by industry/business type."""
    _verify_admin_secret(x_api_secret)

    try:
        db = get_service_supabase()

        result = db.table("tenants").select("business_type, plan").execute()
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
                "paid_percentage": (
                    round(counts["paid"] / counts["total"] * 100, 1)
                    if counts["total"] > 0
                    else 0
                ),
            }
            for industry, counts in sorted(
                industry_counts.items(), key=lambda x: x[1]["total"], reverse=True
            )
        ]

        return {"breakdown": breakdown}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get industry breakdown")
        raise HTTPException(status_code=500, detail="Failed to load industry breakdown")
