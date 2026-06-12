"""Billing endpoints under /api/v1/auth/billing/* (JWT-authenticated proxies).

Extracted from backend/routers/auth.py (audit 2026-06-10 H1 — auth.py was a
1,600-line god file holding five concerns). Same URL prefix, same contracts;
only the module moved. Tests that patch stripe/settings for these endpoints
patch backend.routers.auth_billing.* now.

Critical rules: no `from __future__ import annotations`; never log secrets.
"""

import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.config import settings
from backend.dependencies import require_role, block_demo_role
from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.activity import log_activity
from backend.services.stripe_service import (
    PLAN_PRICES,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["billing"],
    dependencies=[Depends(block_demo_role)],
)


def get_service_supabase():
    """Module-level indirection so tests can patch auth_billing.get_service_supabase."""
    return _get_service_supabase()


@router.post("/billing/checkout")
async def billing_checkout(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Create Stripe checkout session (JWT auth, no API secret needed)."""
    body = await request.json()
    tenant_id = claims["tenant_id"]
    plan = body.get("plan")

    if not plan or plan not in PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}",
        )
    try:
        prices = ensure_plan_prices_configured(plan)
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("id, owner_email, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    source = body.get("source")  # "wizard" | None
    if source == "wizard":
        # Wizard order (2026-06-11): Plan is step 5; widget steps 6-7 are optional.
        success_url = f"{settings.frontend_url}/onboarding?step=6&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/onboarding?step=5&cancelled=1"
    else:
        success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/billing/cancel"

    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"tenant_id": tenant_id, "plan": plan},
        "subscription_data": {"metadata": {"tenant_id": tenant_id, "plan": plan}},
    }
    if plan == "growth":
        session_params["subscription_data"]["trial_period_days"] = 7

    promo_code = body.get("promo_code")
    if promo_code:
        promos = stripe.PromotionCode.list(code=promo_code, active=True, limit=1)
        if promos.data:
            session_params["discounts"] = [{"promotion_code": promos.data[0].id}]
        else:
            raise HTTPException(status_code=400, detail="Invalid promo code")

    session = stripe.checkout.Session.create(**session_params)
    return {"checkout_url": session.url}


@router.get("/billing/portal/{tenant_id}")
async def billing_portal(tenant_id: str, claims: dict = Depends(require_role("owner"))):
    """Create Stripe customer portal session (JWT auth)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    customer_id = result.data[0].get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account. Upgrade to a paid plan first."
        )

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )
    return {"portal_url": session.url}


@router.post("/billing/change-plan")
async def billing_change_plan(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Change subscription plan (upgrade/downgrade) with proration."""
    body = await request.json()
    new_plan = body.get("plan")
    tenant_id = claims["tenant_id"]

    if not new_plan or new_plan not in PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES)}",
        )
    try:
        new_price_id = ensure_plan_prices_configured(new_plan)["monthly"]
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account. Subscribe first."
        )

    current_plan = tenant.get("plan") or "free"
    if current_plan == new_plan:
        raise HTTPException(status_code=400, detail="Already on this plan")

    # Find active subscription
    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Use checkout to subscribe.",
        )

    subscription = subs.data[0]
    sub_item_id = subscription["items"]["data"][0]["id"]
    # Modify subscription with proration
    updated = stripe.Subscription.modify(
        subscription.id,
        items=[{"id": sub_item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
        metadata={"tenant_id": tenant_id, "plan": new_plan},
    )

    # Update tenant plan immediately (webhook will also fire)
    db.table("tenants").update({"plan": new_plan}).eq("id", tenant_id).execute()

    logger.info(
        "Plan changed for tenant %s: %s -> %s", tenant_id, current_plan, new_plan
    )
    return {"status": "changed", "old_plan": current_plan, "new_plan": new_plan}


@router.post("/billing/cancel")
async def billing_cancel(
    request: Request,
    claims: dict = Depends(require_role("owner")),
):
    """Cancel subscription at end of billing period."""
    tenant_id = claims["tenant_id"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    allowed_reasons = {
        "too_expensive",
        "missing_feature",
        "not_enough_leads",
        "switching_tools",
        "setup_too_hard",
        "temporary_pause",
        "other",
    }
    reason = str(body.get("reason") or "").strip()
    if reason not in allowed_reasons:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    reason_detail = str(body.get("reason_detail") or body.get("detail") or "").strip()[
        :1000
    ]
    feedback = str(body.get("feedback") or "").strip()[:1000]

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("stripe_customer_id, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account")

    if tenant.get("plan") == "free":
        raise HTTPException(status_code=400, detail="Already on free plan")

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
    if not subs.data:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Cancel at period end (don't immediately revoke access)
    subscription = subs.data[0]
    subscription_id = getattr(subscription, "id", None)
    if subscription_id is None and isinstance(subscription, dict):
        subscription_id = subscription.get("id")
    stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True,
        metadata={
            "tenant_id": tenant_id,
            "cancellation_reason": reason,
        },
    )

    current_period_end = getattr(subscription, "current_period_end", None)
    if current_period_end is None and isinstance(subscription, dict):
        current_period_end = subscription.get("current_period_end")
    current_period_end_iso = None
    if isinstance(current_period_end, (int, float)):
        current_period_end_iso = datetime.fromtimestamp(
            current_period_end,
            tz=timezone.utc,
        ).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        db.table("tenants").update(
            {
                "cancellation_requested_at": now_iso,
                "cancellation_reason": reason,
                "cancellation_reason_detail": reason_detail or None,
            }
        ).eq("id", tenant_id).execute()
        db.table("tenant_cancellation_events").insert(
            {
                "tenant_id": tenant_id,
                "stripe_subscription_id": subscription_id,
                "plan": tenant.get("plan"),
                "reason": reason,
                "reason_detail": reason_detail or None,
                "feedback": feedback or None,
                "current_period_end": current_period_end_iso,
            }
        ).execute()
    except Exception:
        logger.warning(
            "Failed to persist cancellation reason for tenant %s",
            tenant_id,
            exc_info=True,
        )

    log_activity(
        tenant_id=tenant_id,
        activity_type="subscription_cancellation_scheduled",
        description="Subscription cancellation scheduled at period end",
        metadata={
            "reason": reason,
            "has_reason_detail": bool(reason_detail),
            "current_period_end": current_period_end_iso,
        },
    )

    logger.info("Subscription cancellation scheduled for tenant %s", tenant_id)
    return {
        "status": "cancellation_scheduled",
        "current_period_end": current_period_end,
    }
