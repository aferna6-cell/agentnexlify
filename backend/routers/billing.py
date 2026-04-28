"""Stripe billing endpoints — checkout, webhooks, and customer portal."""


import hashlib
import html as html_mod
import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field, field_validator

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.models.schemas import CreateCheckoutRequest, CheckoutResponse, PortalResponse
from backend.dependencies import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.fraud_guard import guard_checkout_for_fraud
from backend.services.stripe_service import (
    PLAN_PRICES,
    STRIPE_ADDON_MARKETING_VALUE,
    STRIPE_ADDON_METADATA_KEY,
    cancel_marketing_addon_subscription,
    create_marketing_addon_checkout_session,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class AdminRefundRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    refund_request_id: str = Field(..., min_length=8, max_length=120)
    payment_intent: str | None = None
    charge: str | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    stripe_reason: str | None = None
    internal_reason: str = Field(..., min_length=3, max_length=500)
    requested_by: str = Field(..., min_length=2, max_length=200)

    @field_validator("refund_request_id")
    @classmethod
    def _strip_refund_request_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("refund_request_id is required")
        return cleaned


# ---------------------------------------------------------------------------
# Auth dependency (same pattern as clients.py)
# ---------------------------------------------------------------------------

def _verify_secret(x_api_secret: str = Header(...)):
    import hmac as _hmac
    secret = settings.billing_secret or settings.api_secret_key
    if not secret or not _hmac.compare_digest(x_api_secret, secret):
        raise HTTPException(status_code=403, detail="Invalid API secret")


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    import hmac as _hmac
    secret = _admin_secret()
    if not secret or not x_api_secret or not _hmac.compare_digest(x_api_secret, secret):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _stripe_obj_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if isinstance(value, dict):
        return dict(value)
    result: dict[str, Any] = {}
    for key in ("id", "amount", "currency", "status", "payment_intent", "charge", "reason"):
        if hasattr(value, key):
            result[key] = getattr(value, key)
    return result


def _refund_idempotency_key(req: AdminRefundRequest) -> str:
    key = f"agentnexlify-refund:{req.tenant_id}:{req.refund_request_id}"
    if len(key) <= 255:
        return key
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"agentnexlify-refund:{digest}"


def _refund_response_from_audit(row: dict[str, Any], *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "status": "refunded",
        "stripe_refund_id": row.get("stripe_refund_id"),
        "amount_cents": row.get("amount_cents"),
        "currency": row.get("currency") or "usd",
        "refund_status": row.get("status") or "pending",
        "idempotent_replay": idempotent_replay,
    }


def _find_refund_audit(
    db,
    *,
    tenant_id: str,
    refund_request_id: str | None = None,
    stripe_refund_id: str | None = None,
) -> dict[str, Any] | None:
    query = (
        db.table("billing_refunds")
        .select("stripe_refund_id, amount_cents, currency, status, refund_request_id")
        .eq("tenant_id", tenant_id)
    )
    if refund_request_id:
        query = query.eq("refund_request_id", refund_request_id)
    if stripe_refund_id:
        query = query.eq("stripe_refund_id", stripe_refund_id)
    result = query.limit(1).execute()
    return result.data[0] if result.data else None


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

    # Build line items — plans may have setup fee + monthly
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
        # Return 500 so Stripe retries (Stripe retries for up to 3 days)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    return {"status": "ok"}


AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    15000: "professional",
    25000: "enterprise",
    # Legacy monthly pricing (keep for existing subscribers)
    24900: "growth",
    29900: "autopilot",
    49900: "professional",
    19900: "growth",
    39900: "professional",
    79900: "enterprise",
    # Monthly + setup fee (legacy, setup now waived)
    54800: "growth",         # $249 + $299 setup
    99800: "professional",   # $499 + $499 setup
    189800: "enterprise",    # $899 + $999 setup
    49800: "growth",         # $199 + $299 setup
    89800: "professional",   # $399 + $499 setup
    179800: "enterprise",    # $799 + $999 setup
}

# Keywords to match in product/price descriptions
PLAN_KEYWORDS: dict[str, str] = {
    "starter": "growth",
    "growth": "growth",
    "autopilot": "autopilot",
    "pro": "professional",
    "professional": "professional",
    "enterprise": "enterprise",
}


def _resolve_plan(session: dict) -> str | None:
    """Determine plan from metadata, line items, or amount."""
    metadata = session.get("metadata", {})
    plan = metadata.get("plan")
    logger.info("_resolve_plan: metadata.plan=%s", plan)
    if plan and plan in {"free", "growth", "professional", "autopilot", "enterprise"}:
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

    fraud_reason = guard_checkout_for_fraud(session)
    if fraud_reason:
        logger.warning(
            "checkout.session.completed: fraud detected for tenant %s — %s. Pausing activation.",
            tenant_id, fraud_reason,
        )
        update_data = {
            "plan": plan,
            "plan_status": "paused",
            "stripe_customer_id": session.get("customer"),
            "stripe_subscription_id": session.get("subscription"),
        }
        db.table("tenants").update(update_data).eq("id", tenant_id).execute()
        log_activity(
            tenant_id=tenant_id,
            event_type="fraud_alert",
            description=f"Checkout flagged: {fraud_reason}. Subscription paused pending review.",
            metadata={"fraud_reason": fraud_reason, "session_id": session.get("id")},
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


def _unix_to_iso(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _safe_invoice_snapshot(invoice: dict) -> dict[str, Any]:
    return {
        "id": invoice.get("id"),
        "customer": invoice.get("customer"),
        "subscription": invoice.get("subscription"),
        "amount_due": invoice.get("amount_due"),
        "currency": invoice.get("currency"),
        "attempt_count": invoice.get("attempt_count"),
        "next_payment_attempt": invoice.get("next_payment_attempt"),
        "hosted_invoice_url": invoice.get("hosted_invoice_url"),
        "invoice_pdf": invoice.get("invoice_pdf"),
        "status": invoice.get("status"),
    }


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
    now_iso = datetime.now(timezone.utc).isoformat()
    attempt_count = int(invoice.get("attempt_count") or 0)
    next_payment_attempt_iso = _unix_to_iso(invoice.get("next_payment_attempt"))
    hosted_invoice_url = invoice.get("hosted_invoice_url")
    invoice_pdf = invoice.get("invoice_pdf")
    amount_due = invoice.get("amount_due")
    currency = (invoice.get("currency") or "usd").lower()
    subscription_id = invoice.get("subscription")

    db.table("tenants").update({
        "plan_status": "paused",
        "billing_dunning_last_sent_at": now_iso,
        "billing_dunning_attempt_count": attempt_count,
    }).eq("id", tenant_id).execute()

    logger.info("Tenant %s payment failed, plan paused", tenant_id)

    # Send payment failure notification email
    owner_email = tenant.get("owner_email")
    email_result: dict[str, Any] = {"success": False, "detail": "owner_email_missing"}
    if owner_email:
        try:
            from backend.services.email_sender import send_email
            business_name = html_mod.escape(tenant.get("business_name") or "your business")
            invoice_link = ""
            if hosted_invoice_url:
                safe_invoice_url = html_mod.escape(str(hosted_invoice_url))
                invoice_link = (
                    f"<p><a href=\"{safe_invoice_url}\">Review and pay the open invoice</a>.</p>"
                )
            next_retry = ""
            if next_payment_attempt_iso:
                next_retry = (
                    f"<p>Stripe has a retry scheduled around "
                    f"{html_mod.escape(next_payment_attempt_iso)}.</p>"
                )
            email_result = await send_email(
                to=owner_email,
                subject="Payment failed — your AgentNexLiFy subscription is paused",
                body_html=(
                    f"<h2>Hi,</h2>"
                    f"<p>We were unable to process the payment for <strong>{business_name}</strong>'s subscription.</p>"
                    f"<p>Your account has been temporarily paused. To restore service, please update your payment method in the billing portal.</p>"
                    f"{invoice_link}"
                    f"{next_retry}"
                    f"<p>Billing portal: <a href=\"{html_mod.escape(settings.frontend_url.rstrip('/'))}/billing\">open billing settings</a></p>"
                    f"<p>If you need help, reply to this email.</p>"
                    f"<p>— The AgentNexLiFy Team</p>"
                ),
                tenant_id=tenant_id,
            )
        except Exception:
            email_result = {"success": False, "detail": "send_failed"}
            logger.warning("Failed to send payment failure email to %s", owner_email, exc_info=True)

    try:
        db.table("billing_dunning_events").insert({
            "tenant_id": tenant_id,
            "stripe_invoice_id": invoice.get("id") or "",
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "attempt_count": attempt_count,
            "next_payment_attempt": next_payment_attempt_iso,
            "amount_due_cents": amount_due,
            "currency": currency,
            "hosted_invoice_url": hosted_invoice_url,
            "invoice_pdf": invoice_pdf,
            "email_sent": bool(email_result.get("success")),
            "email_detail": str(email_result.get("detail") or "")[:500],
            "raw_invoice": _safe_invoice_snapshot(invoice),
        }).execute()
    except Exception:
        logger.warning(
            "Failed to insert dunning event for tenant %s invoice %s",
            tenant_id,
            invoice.get("id"),
            exc_info=True,
        )


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
