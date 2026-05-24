"""Stripe billing endpoints — thin router that re-exports helpers from siblings.

Split per Rule 9 (god class >600 lines) into:
- billing_helpers.py — auth deps, dict converters, refund audit helpers, AdminRefundRequest
- billing_webhooks.py — plan/tenant resolvers + webhook event handlers
- billing_addon.py — marketing add-on detection + lifecycle handlers

Tests patch `backend.routers.billing.X` for symbols like `log_activity`,
`stripe.Refund.create`, `ensure_stripe_configured`, `_verify_admin_secret`,
`get_service_supabase`, `get_or_create_customer`, etc. Those symbols MUST
remain importable from this namespace — they are re-exported below.
"""


import logging
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Header, Request

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.models.schemas import CreateCheckoutRequest, CheckoutResponse, PortalResponse
from backend.dependencies import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.stripe_service import (
    PLAN_PRICES,
    cancel_marketing_addon_subscription,
    create_marketing_addon_checkout_session,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)

from backend.routers.billing_helpers import (
    AdminRefundRequest,
    _admin_secret,
    _find_refund_audit,
    _refund_idempotency_key,
    _refund_response_from_audit,
    _stripe_obj_to_dict,
    _verify_admin_secret,
    _verify_secret,
)
from backend.routers.billing_webhooks import (
    AMOUNT_TO_PLAN,
    PLAN_KEYWORDS,
    _handle_checkout_completed,
    _handle_payment_failed,
    _handle_subscription_deleted,
    _handle_subscription_updated,
    _resolve_plan,
    _resolve_tenant_from_subscription,
    _resolve_tenant_id,
    _safe_invoice_snapshot,
    _unix_to_iso,
)
from backend.routers.billing_addon import (
    _handle_addon_checkout_completed,
    _handle_addon_subscription_deleted,
    _handle_addon_subscription_updated,
    _is_marketing_addon_subscription,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# POST /api/v1/billing/create-checkout
# ---------------------------------------------------------------------------

@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(req: CreateCheckoutRequest, _=Depends(_verify_secret)):
    """Create a Stripe Checkout session for a subscription plan."""
    if req.plan not in PLAN_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan '{req.plan}'. Must be one of: {', '.join(PLAN_PRICES)}",
        )
    try:
        prices = ensure_plan_prices_configured(req.plan)
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = db.table("tenants").select("id, owner_email, business_name").eq("id", req.tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=req.tenant_id,
        business_name=tenant.get("business_name"),
    )

    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    success_path = (
        f"{settings.frontend_url}/onboarding?step=6&session_id={{CHECKOUT_SESSION_ID}}"
        if req.source == "wizard"
        else f"{settings.frontend_url}/dashboard?checkout_success=1&session_id={{CHECKOUT_SESSION_ID}}"
    )
    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": success_path,
        "cancel_url": f"{settings.frontend_url}/billing/cancel",
        "metadata": {"tenant_id": req.tenant_id, "plan": req.plan},
        "subscription_data": {
            "metadata": {"tenant_id": req.tenant_id, "plan": req.plan},
        },
    }
    if req.plan == "growth":
        session_params["subscription_data"]["trial_period_days"] = 7

    if req.promo_code:
        promos = stripe.PromotionCode.list(code=req.promo_code, active=True, limit=1)
        if promos.data:
            session_params["discounts"] = [{"promotion_code": promos.data[0].id}]
        else:
            raise HTTPException(status_code=400, detail="Invalid promo code")

    session = stripe.checkout.Session.create(**session_params)
    logger.info(
        "Created checkout session %s for tenant %s plan %s",
        session.id, req.tenant_id, req.plan,
    )
    return CheckoutResponse(checkout_url=session.url)


# ---------------------------------------------------------------------------
# POST /api/v1/billing/webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. No auth header — verified via signature."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as exc:
        if "SignatureVerification" in type(exc).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature")
        raise HTTPException(status_code=400, detail="Webhook verification failed") from exc

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook received: type=%s, id=%s", event_type, event.get("id"))
    db = get_service_supabase()

    try:
        if event_type == "checkout.session.completed":
            metadata = data.get("metadata") or {}
            if metadata.get("invoice_id") and metadata.get("tenant_id"):
                from backend.routers.stripe_webhooks import _handle_invoice_payment

                _handle_invoice_payment(db, data)
            elif _is_marketing_addon_subscription(data):
                _handle_addon_checkout_completed(db, data)
            else:
                _handle_checkout_completed(db, data)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            if _is_marketing_addon_subscription(data):
                _handle_addon_subscription_updated(db, data)
            else:
                _handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            if _is_marketing_addon_subscription(data):
                _handle_addon_subscription_deleted(db, data)
            else:
                _handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Stripe webhook handler failed for event %s", event_type)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/billing/admin/refund
# ---------------------------------------------------------------------------

@router.post("/admin/refund")
async def admin_create_refund(
    req: AdminRefundRequest,
    x_api_secret: str | None = Header(None),
):
    """Issue a Stripe refund and persist an internal audit record."""
    _verify_admin_secret(x_api_secret)
    if not req.payment_intent and not req.charge:
        raise HTTPException(status_code=400, detail="payment_intent or charge is required")
    if req.payment_intent and req.charge:
        raise HTTPException(status_code=400, detail="Provide only one of payment_intent or charge")

    allowed_reasons = {"duplicate", "fraudulent", "requested_by_customer"}
    if req.stripe_reason and req.stripe_reason not in allowed_reasons:
        raise HTTPException(
            status_code=400,
            detail=f"stripe_reason must be one of: {', '.join(sorted(allowed_reasons))}",
        )

    db = get_service_supabase()
    tenant_result = (
        db.table("tenants")
        .select("id, business_name, owner_email, stripe_customer_id")
        .eq("id", req.tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing_refund = _find_refund_audit(
        db,
        tenant_id=req.tenant_id,
        refund_request_id=req.refund_request_id,
    )
    if existing_refund:
        return _refund_response_from_audit(existing_refund, idempotent_replay=True)

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    refund_params: dict[str, Any] = {}
    if req.payment_intent:
        refund_params["payment_intent"] = req.payment_intent
    if req.charge:
        refund_params["charge"] = req.charge
    if req.amount_cents:
        refund_params["amount"] = req.amount_cents
    if req.stripe_reason:
        refund_params["reason"] = req.stripe_reason
    refund_params["metadata"] = {
        "tenant_id": req.tenant_id,
        "refund_request_id": req.refund_request_id,
        "requested_by": req.requested_by,
        "internal_reason": req.internal_reason[:200],
    }

    try:
        refund = stripe.Refund.create(
            **refund_params,
            idempotency_key=_refund_idempotency_key(req),
        )
    except Exception as exc:
        logger.exception("Stripe refund failed for tenant %s", req.tenant_id)
        raise HTTPException(status_code=502, detail="Stripe refund failed") from exc

    refund_data = _stripe_obj_to_dict(refund)
    refund_id = refund_data.get("id")
    if not refund_id:
        raise HTTPException(status_code=502, detail="Stripe refund response missing id")

    audit_row = {
        "tenant_id": req.tenant_id,
        "refund_request_id": req.refund_request_id,
        "stripe_refund_id": refund_id,
        "stripe_payment_intent_id": refund_data.get("payment_intent") or req.payment_intent,
        "stripe_charge_id": refund_data.get("charge") or req.charge,
        "amount_cents": refund_data.get("amount") or req.amount_cents,
        "currency": refund_data.get("currency") or "usd",
        "stripe_reason": refund_data.get("reason") or req.stripe_reason,
        "internal_reason": req.internal_reason,
        "requested_by": req.requested_by,
        "status": refund_data.get("status") or "pending",
        "raw_refund": refund_data,
    }
    try:
        db.table("billing_refunds").insert(audit_row).execute()
    except Exception:
        existing_refund = _find_refund_audit(
            db,
            tenant_id=req.tenant_id,
            stripe_refund_id=refund_id,
        )
        if existing_refund:
            logger.info("Refund audit already exists for refund %s", refund_id)
            return _refund_response_from_audit(existing_refund, idempotent_replay=True)
        logger.exception("Refund audit insert failed for refund %s", refund_id)
        raise HTTPException(status_code=500, detail="Refund created but audit log failed")

    log_activity(
        tenant_id=req.tenant_id,
        activity_type="billing_refund_created",
        description="Admin refund issued",
        metadata={
            "stripe_refund_id": refund_id,
            "amount_cents": audit_row["amount_cents"],
            "currency": audit_row["currency"],
            "requested_by": req.requested_by,
            "stripe_reason": audit_row["stripe_reason"],
        },
    )
    logger.info("Admin refund %s created for tenant %s", refund_id, req.tenant_id)
    return {
        "status": "refunded",
        "stripe_refund_id": refund_id,
        "amount_cents": audit_row["amount_cents"],
        "currency": audit_row["currency"],
        "refund_status": audit_row["status"],
        "idempotent_replay": False,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/billing/portal/{tenant_id}
# ---------------------------------------------------------------------------

@router.get("/portal/{tenant_id}", response_model=PortalResponse)
async def billing_portal(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Create a Stripe Customer Portal session for managing subscriptions."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_service_supabase()
    result = db.table("tenants").select("stripe_customer_id").eq("id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    customer_id = result.data[0].get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="Tenant has no Stripe customer")

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )
    return PortalResponse(portal_url=session.url)


# ---------------------------------------------------------------------------
# Marketing Suite Add-on — separate $49.99/mo subscription
# ---------------------------------------------------------------------------

@router.post("/marketing-addon/checkout", response_model=CheckoutResponse)
async def marketing_addon_checkout(claims: dict = Depends(_get_current_tenant)):
    """Create a Stripe Checkout session for the $49.99/mo Marketing Suite add-on."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("id, owner_email, business_name, marketing_addon_active, "
                "marketing_addon_stripe_sub_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    if tenant.get("marketing_addon_active") and tenant.get(
        "marketing_addon_stripe_sub_id"
    ):
        raise HTTPException(status_code=409, detail="Add-on already active")

    try:
        ensure_stripe_configured()
        customer = get_or_create_customer(
            email=tenant.get("owner_email") or "",
            tenant_id=tenant_id,
            business_name=tenant.get("business_name"),
        )
        session = create_marketing_addon_checkout_session(
            tenant_id=tenant_id,
            customer_id=customer.id,
            success_url=(
                f"{settings.frontend_url}/billing/success"
                "?addon=marketing&session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{settings.frontend_url}/billing/cancel?addon=marketing",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    logger.info("Created marketing addon checkout session %s for tenant %s",
                session.id, tenant_id)
    return CheckoutResponse(checkout_url=session.url)


@router.post("/marketing-addon/cancel")
async def marketing_addon_cancel(claims: dict = Depends(_get_current_tenant)):
    """Cancel the Marketing Suite add-on at period end."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("marketing_addon_stripe_sub_id, marketing_addon_grandfathered")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    sub_id = result.data[0].get("marketing_addon_stripe_sub_id")
    grandfathered = result.data[0].get("marketing_addon_grandfathered")

    if grandfathered and not sub_id:
        raise HTTPException(
            status_code=400,
            detail="Access is grandfathered — no subscription to cancel",
        )
    if not sub_id:
        raise HTTPException(status_code=404, detail="No active add-on subscription")

    try:
        ensure_stripe_configured()
        cancel_marketing_addon_subscription(sub_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    logger.info("Marketing addon cancel-at-period-end for tenant %s sub %s",
                tenant_id, sub_id)
    return {"status": "scheduled_cancel"}


__all__ = [
    "AMOUNT_TO_PLAN",
    "AdminRefundRequest",
    "PLAN_KEYWORDS",
    "_admin_secret",
    "_find_refund_audit",
    "_handle_addon_checkout_completed",
    "_handle_addon_subscription_deleted",
    "_handle_addon_subscription_updated",
    "_handle_checkout_completed",
    "_handle_payment_failed",
    "_handle_subscription_deleted",
    "_handle_subscription_updated",
    "_is_marketing_addon_subscription",
    "_refund_idempotency_key",
    "_refund_response_from_audit",
    "_resolve_plan",
    "_resolve_tenant_from_subscription",
    "_resolve_tenant_id",
    "_safe_invoice_snapshot",
    "_stripe_obj_to_dict",
    "_unix_to_iso",
    "_verify_admin_secret",
    "_verify_secret",
    "admin_create_refund",
    "billing_portal",
    "create_checkout",
    "ensure_stripe_configured",
    "get_or_create_customer",
    "get_service_supabase",
    "log_activity",
    "logger",
    "marketing_addon_cancel",
    "marketing_addon_checkout",
    "router",
    "settings",
    "stripe",
    "stripe_webhook",
]
