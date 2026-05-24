"""Billing handler bodies extracted from auth.py.

Four service functions:
- `checkout(tenant_id, plan, source, promo_code)` — Stripe checkout session.
- `portal(tenant_id)` — Stripe customer portal session.
- `change_plan(tenant_id, new_plan)` — Modify subscription with proration.
- `cancel_subscription(tenant_id, reason, reason_detail, feedback)` — Cancel
  at period end with reason capture.

All four use `from backend.routers import auth as _auth` lazy lookup so the
existing test patch surface (`backend.routers.auth.<symbol>` for
`get_service_supabase`, `ensure_stripe_configured`, `stripe`,
`get_or_create_customer`, `ensure_plan_prices_configured`, `PLAN_PRICES`,
`log_activity`, `settings`) continues to intercept.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def checkout(
    *,
    tenant_id: str,
    plan: str,
    source: str | None,
    promo_code: str | None,
) -> dict:
    from backend.routers import auth as _auth

    if not plan or plan not in _auth.PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(_auth.PLAN_PRICES)}",
        )
    try:
        prices = _auth.ensure_plan_prices_configured(plan)
        _auth.ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = _auth.get_service_supabase()
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

    customer = _auth.get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    if source == "wizard":
        success_url = (
            f"{_auth.settings.frontend_url}/onboarding?step=7"
            "&session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = f"{_auth.settings.frontend_url}/onboarding?step=6&cancelled=1"
    else:
        success_url = (
            f"{_auth.settings.frontend_url}/billing/success"
            "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = f"{_auth.settings.frontend_url}/billing/cancel"

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

    if promo_code:
        promos = _auth.stripe.PromotionCode.list(code=promo_code, active=True, limit=1)
        if promos.data:
            session_params["discounts"] = [{"promotion_code": promos.data[0].id}]
        else:
            raise HTTPException(status_code=400, detail="Invalid promo code")

    session = _auth.stripe.checkout.Session.create(**session_params)
    return {"checkout_url": session.url}


def portal(*, tenant_id: str) -> dict:
    from backend.routers import auth as _auth

    db = _auth.get_service_supabase()
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
            status_code=400,
            detail="No billing account. Upgrade to a paid plan first.",
        )

    try:
        _auth.ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    session = _auth.stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{_auth.settings.frontend_url}/billing",
    )
    return {"portal_url": session.url}


def change_plan(*, tenant_id: str, new_plan: str) -> dict:
    from backend.routers import auth as _auth

    if not new_plan or new_plan not in _auth.PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(_auth.PLAN_PRICES)}",
        )
    try:
        new_price_id = _auth.ensure_plan_prices_configured(new_plan)["monthly"]
        _auth.ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = _auth.get_service_supabase()
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

    subs = _auth.stripe.Subscription.list(
        customer=customer_id, status="active", limit=1
    )
    if not subs.data:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Use checkout to subscribe.",
        )

    subscription = subs.data[0]
    sub_item_id = subscription["items"]["data"][0]["id"]
    _auth.stripe.Subscription.modify(
        subscription.id,
        items=[{"id": sub_item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
        metadata={"tenant_id": tenant_id, "plan": new_plan},
    )

    db.table("tenants").update({"plan": new_plan}).eq("id", tenant_id).execute()

    logger.info(
        "Plan changed for tenant %s: %s -> %s", tenant_id, current_plan, new_plan
    )
    return {"status": "changed", "old_plan": current_plan, "new_plan": new_plan}


_ALLOWED_CANCEL_REASONS = {
    "too_expensive",
    "missing_feature",
    "not_enough_leads",
    "switching_tools",
    "setup_too_hard",
    "temporary_pause",
    "other",
}


def cancel_subscription(
    *,
    tenant_id: str,
    reason: str,
    reason_detail: str,
    feedback: str,
) -> dict:
    from backend.routers import auth as _auth

    if reason not in _ALLOWED_CANCEL_REASONS:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    reason_detail = (reason_detail or "")[:1000]
    feedback = (feedback or "")[:1000]

    db = _auth.get_service_supabase()
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
        _auth.ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    subs = _auth.stripe.Subscription.list(
        customer=customer_id, status="active", limit=1
    )
    if not subs.data:
        raise HTTPException(status_code=400, detail="No active subscription")

    subscription = subs.data[0]
    subscription_id = getattr(subscription, "id", None)
    if subscription_id is None and isinstance(subscription, dict):
        subscription_id = subscription.get("id")
    _auth.stripe.Subscription.modify(
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

    _auth.log_activity(
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
