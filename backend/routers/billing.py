"""Stripe billing endpoints — checkout, webhooks, and customer portal."""


import html as html_mod
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Header, Request

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.models.schemas import CreateCheckoutRequest, CheckoutResponse, PortalResponse
from backend.routers.auth import _get_current_tenant
from backend.services.stripe_service import (
    PLAN_PRICES,
    STRIPE_ADDON_MARKETING_VALUE,
    STRIPE_ADDON_METADATA_KEY,
    cancel_marketing_addon_subscription,
    create_marketing_addon_checkout_session,
    get_or_create_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Auth dependency (same pattern as clients.py)
# ---------------------------------------------------------------------------

def _verify_secret(x_api_secret: str = Header(...)):
    import hmac as _hmac
    secret = settings.billing_secret or settings.api_secret_key
    if not secret or not _hmac.compare_digest(x_api_secret, secret):
        raise HTTPException(status_code=403, detail="Invalid API secret")


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

    # Build line items — plans may have setup fee + monthly
    prices = PLAN_PRICES[req.plan]
    line_items = []
    if "setup" in prices:
        line_items.append({"price": prices["setup"], "quantity": 1})
    line_items.append({"price": prices["monthly"], "quantity": 1})

    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.frontend_url}/billing/cancel",
        "metadata": {"tenant_id": req.tenant_id, "plan": req.plan},
        "subscription_data": {
            "metadata": {"tenant_id": req.tenant_id, "plan": req.plan},
        },
    }

    # Attach promo code if provided
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
        # Handle both pre-v11 and v11+ stripe SDK exception names
        if "SignatureVerification" in type(exc).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature")
        raise HTTPException(status_code=400, detail="Webhook verification failed") from exc

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook received: type=%s, id=%s", event_type, event.get("id"))
    db = get_service_supabase()

    try:
        if event_type == "checkout.session.completed":
            if _is_marketing_addon_subscription(data):
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
        # Return 500 so Stripe retries (Stripe retries for up to 3 days)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    return {"status": "ok"}


AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    24900: "growth",
    49900: "professional",
    89900: "enterprise",
    # Legacy monthly pricing (keep for existing subscribers)
    19900: "growth",
    39900: "professional",
    79900: "enterprise",
    # Monthly + setup fee (first invoice, setup currently waived)
    54800: "growth",         # $249 + $299 setup
    99800: "professional",   # $499 + $499 setup
    189800: "enterprise",    # $899 + $999 setup
    # Legacy monthly + setup fee
    49800: "growth",         # $199 + $299 setup
    89800: "professional",   # $399 + $499 setup
    179800: "enterprise",    # $799 + $999 setup
}

# Keywords to match in product/price descriptions
PLAN_KEYWORDS: dict[str, str] = {
    "growth": "growth",
    "professional": "professional",
    "enterprise": "enterprise",
}


def _resolve_plan(session: dict) -> str | None:
    """Determine plan from metadata, line items, or amount."""
    metadata = session.get("metadata", {})
    plan = metadata.get("plan")
    logger.info("_resolve_plan: metadata.plan=%s", plan)
    if plan and plan in {"free", "growth", "professional", "enterprise"}:
        return plan

    # Try amount_total (in cents)
    amount = session.get("amount_total")
    logger.info("_resolve_plan: amount_total=%s, known amounts=%s", amount, list(AMOUNT_TO_PLAN.keys()))
    if amount and amount in AMOUNT_TO_PLAN:
        return AMOUNT_TO_PLAN[amount]

    # Try matching plan name from display_items or line_items descriptions
    for field in ("display_items", "line_items"):
        items = session.get(field, {})
        if isinstance(items, dict):
            items = items.get("data", [])
        for item in (items or []):
            desc = (
                item.get("description", "")
                or item.get("price", {}).get("nickname", "")
                or item.get("plan", {}).get("nickname", "")
                or ""
            ).lower()
            logger.info("_resolve_plan: checking line item desc=%s", desc)
            for keyword, plan_name in PLAN_KEYWORDS.items():
                if keyword in desc:
                    return plan_name

    logger.warning("_resolve_plan: could not determine plan from session")
    return None


def _resolve_tenant_id(db, session: dict) -> str | None:
    """Determine tenant_id from metadata or customer_email."""
    metadata = session.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    if tenant_id:
        logger.info("_resolve_tenant_id: found tenant_id in metadata: %s", tenant_id)
        return tenant_id

    # Fall back to email lookup
    email = (
        session.get("customer_email")
        or session.get("customer_details", {}).get("email")
    )
    logger.info(
        "_resolve_tenant_id: no metadata tenant_id, trying email lookup: "
        "customer_email=%s, customer_details.email=%s",
        session.get("customer_email"),
        session.get("customer_details", {}).get("email"),
    )
    if not email:
        logger.warning("_resolve_tenant_id: no email found in session")
        return None

    search_email = email.lower().strip()
    logger.info("_resolve_tenant_id: searching tenants for owner_email=%s", search_email)
    result = (
        db.table("tenants")
        .select("id, owner_email")
        .eq("owner_email", search_email)
        .limit(1)
        .execute()
    )
    logger.info("_resolve_tenant_id: query result data=%s", result.data)
    if result.data:
        return str(result.data[0]["id"])
    return None


def _handle_checkout_completed(db, session: dict) -> None:
    logger.info(
        "checkout.session.completed: customer_email=%s, customer=%s, "
        "metadata=%s, amount_total=%s, subscription=%s, mode=%s, status=%s",
        session.get("customer_email"),
        session.get("customer"),
        session.get("metadata"),
        session.get("amount_total"),
        session.get("subscription"),
        session.get("mode"),
        session.get("status"),
    )

    tenant_id = _resolve_tenant_id(db, session)
    plan = _resolve_plan(session)

    logger.info("checkout.session.completed: resolved tenant_id=%s, plan=%s", tenant_id, plan)

    if not tenant_id:
        logger.warning(
            "checkout.session.completed: could not resolve tenant (email=%s, metadata=%s)",
            session.get("customer_email"), session.get("metadata"),
        )
        return
    if not plan:
        logger.warning(
            "checkout.session.completed: could not resolve plan (amount=%s, metadata=%s)",
            session.get("amount_total"), session.get("metadata"),
        )
        return

    update_data = {
        "plan": plan,
        "plan_status": "active",
        "stripe_customer_id": session.get("customer"),
        "stripe_subscription_id": session.get("subscription"),
    }
    logger.info("checkout.session.completed: updating tenant %s with %s", tenant_id, update_data)

    update_result = db.table("tenants").update(update_data).eq("id", tenant_id).execute()
    logger.info("checkout.session.completed: update result data=%s", update_result.data)

    logger.info("Tenant %s upgraded to %s", tenant_id, plan)


def _resolve_tenant_from_subscription(db, subscription: dict) -> str | None:
    """Get tenant_id from subscription metadata or stripe_customer_id."""
    tenant_id = subscription.get("metadata", {}).get("tenant_id")
    if tenant_id:
        return tenant_id

    customer_id = subscription.get("customer")
    if not customer_id:
        return None

    result = (
        db.table("tenants")
        .select("id")
        .eq("stripe_customer_id", customer_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return str(result.data[0]["id"])
    return None


def _handle_subscription_updated(db, subscription: dict) -> None:
    tenant_id = _resolve_tenant_from_subscription(db, subscription)
    plan = subscription.get("metadata", {}).get("plan")
    if not tenant_id:
        logger.warning("subscription.updated: could not resolve tenant (customer=%s)", subscription.get("customer"))
        return

    _ALLOWED_STATUSES = {"active", "paused", "past_due", "unpaid", "incomplete", "canceled", "trialing", "incomplete_expired"}
    raw_status = subscription.get("status", "active")
    update_data: dict = {"plan_status": raw_status if raw_status in _ALLOWED_STATUSES else "paused"}
    if plan:
        update_data["plan"] = plan

    db.table("tenants").update(update_data).eq("id", tenant_id).execute()
    logger.info("Tenant %s subscription updated (plan=%s)", tenant_id, plan)


def _handle_subscription_deleted(db, subscription: dict) -> None:
    tenant_id = _resolve_tenant_from_subscription(db, subscription)
    if not tenant_id:
        logger.warning("subscription.deleted: could not resolve tenant (customer=%s)", subscription.get("customer"))
        return

    db.table("tenants").update({
        "plan": "free",
        "plan_status": "cancelled",
    }).eq("id", tenant_id).execute()

    logger.info("Tenant %s subscription cancelled, reverted to free", tenant_id)


async def _handle_payment_failed(db, invoice: dict) -> None:
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    result = (
        db.table("tenants")
        .select("id, owner_email, business_name")
        .eq("stripe_customer_id", customer_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("payment_failed for unknown customer %s", customer_id)
        return

    tenant = result.data[0]
    tenant_id = tenant["id"]
    db.table("tenants").update({"plan_status": "paused"}).eq("id", tenant_id).execute()

    logger.info("Tenant %s payment failed, plan paused", tenant_id)

    # Send payment failure notification email
    owner_email = tenant.get("owner_email")
    if owner_email:
        try:
            from backend.services.email_sender import send_email
            business_name = html_mod.escape(tenant.get("business_name") or "your business")
            await send_email(
                to=owner_email,
                subject="Payment failed — your AgentNexLiFy subscription is paused",
                body_html=(
                    f"<h2>Hi,</h2>"
                    f"<p>We were unable to process the payment for <strong>{business_name}</strong>'s subscription.</p>"
                    f"<p>Your account has been temporarily paused. To restore service, please update your payment method in the billing portal.</p>"
                    f"<p>If you need help, reply to this email.</p>"
                    f"<p>— The AgentNexLiFy Team</p>"
                ),
                tenant_id=tenant_id,
            )
        except Exception:
            logger.warning("Failed to send payment failure email to %s", owner_email, exc_info=True)


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

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/billing",
    )
    return PortalResponse(portal_url=session.url)


# ---------------------------------------------------------------------------
# Marketing Suite Add-on — separate $49.99/mo subscription
# ---------------------------------------------------------------------------
#
# Gates 7 features: SEO Audit Hub, Social Media, Marketing Campaigns,
# Marketing Dashboard, A/B Tests, Automation Rules, Trigger Logs.
#
# Add-on is a SEPARATE Stripe subscription (not a subscription item on the
# primary plan) so billing lifecycle is isolated: cancellation of the main
# plan does not cancel the add-on and vice versa.


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

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    try:
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

    cancel_marketing_addon_subscription(sub_id)
    logger.info("Marketing addon cancel-at-period-end for tenant %s sub %s",
                tenant_id, sub_id)
    return {"status": "scheduled_cancel"}


def _is_marketing_addon_subscription(obj: dict) -> bool:
    """Return True when Stripe subscription/checkout metadata tags it as marketing add-on."""
    metadata = obj.get("metadata") or {}
    if metadata.get(STRIPE_ADDON_METADATA_KEY) == STRIPE_ADDON_MARKETING_VALUE:
        return True
    sub_meta = (obj.get("subscription_data") or {}).get("metadata") or {}
    return sub_meta.get(STRIPE_ADDON_METADATA_KEY) == STRIPE_ADDON_MARKETING_VALUE


def _handle_addon_checkout_completed(db, session: dict) -> None:
    tenant_id = _resolve_tenant_id(db, session)
    if not tenant_id:
        logger.warning("addon checkout: could not resolve tenant")
        return
    subscription_id = session.get("subscription")
    from datetime import datetime, timezone
    db.table("tenants").update({
        "marketing_addon_active": True,
        "marketing_addon_stripe_sub_id": subscription_id,
        "marketing_addon_started_at": datetime.now(timezone.utc).isoformat(),
        "marketing_addon_grandfathered": False,
    }).eq("id", tenant_id).execute()
    logger.info("Tenant %s marketing add-on activated via subscription %s",
                tenant_id, subscription_id)


def _handle_addon_subscription_updated(db, subscription: dict) -> None:
    tenant_id = _resolve_tenant_from_subscription(db, subscription)
    if not tenant_id:
        return
    status = subscription.get("status")
    active = status in {"active", "trialing"}
    db.table("tenants").update({
        "marketing_addon_active": active,
        "marketing_addon_stripe_sub_id": subscription.get("id"),
    }).eq("id", tenant_id).execute()
    logger.info("Tenant %s marketing add-on sub %s -> status=%s (active=%s)",
                tenant_id, subscription.get("id"), status, active)


def _handle_addon_subscription_deleted(db, subscription: dict) -> None:
    tenant_id = _resolve_tenant_from_subscription(db, subscription)
    if not tenant_id:
        return
    db.table("tenants").update({
        "marketing_addon_active": False,
        "marketing_addon_stripe_sub_id": None,
    }).eq("id", tenant_id).execute()
    logger.info("Tenant %s marketing add-on cancelled", tenant_id)
