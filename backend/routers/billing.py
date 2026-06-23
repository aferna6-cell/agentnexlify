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
from backend.dependencies import _get_current_tenant, block_demo_role
from backend.services.activity import log_activity
from backend.services.fraud_guard import guard_checkout_for_fraud
from backend.services.idempotency import check_and_record, delete_key, record_response
from backend.services.stripe_service import (
    PLAN_PRICES,
    ensure_plan_prices_configured,
    ensure_stripe_configured,
    get_or_create_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/billing",
    tags=["billing"],
    dependencies=[Depends(block_demo_role)],
)


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
        # Card only — disables Stripe Link so customers don't get Link's own
        # wallet/verification emails (they read like phishing for a new customer).
        "payment_method_types": ["card"],
        "customer": customer.id,
        "line_items": line_items,
        "success_url": success_path,
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
    event_id = event.get("id", "")
    logger.info("Stripe webhook received: type=%s, id=%s", event_type, event_id)
    db = get_service_supabase()

    # Idempotency: Stripe retries delivery for up to 3 days on any non-2xx, and
    # this endpoint may receive the same event the /api/v1/webhooks/stripe one
    # does. Dedup on (stripe, event_id) so a redelivery never double-activates a
    # subscription or double-fires the owner alert.
    is_new, _cached = await check_and_record(db, "stripe", event_id)
    if not is_new:
        logger.info("Stripe duplicate event %s — skipping reprocess", event_id)
        return {"status": "ok"}
    idempotency_key = f"stripe:{event_id}"

    try:
        if event_type == "checkout.session.completed":
            metadata = data.get("metadata") or {}
            if metadata.get("invoice_id") and metadata.get("tenant_id"):
                from backend.routers.stripe_webhooks import _handle_invoice_payment

                _handle_invoice_payment(db, data)
            elif metadata.get("kind") == "usage_pack":
                _handle_usage_pack_completed(db, data)
            elif _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on checkout event (add-on retired 2026-06-10)")
            else:
                activation = _handle_checkout_completed(db, data)
                if activation:
                    from backend.services.owner_alerts import notify_new_paid_signup
                    await notify_new_paid_signup(
                        plan=activation["plan"],
                        amount_total=activation["amount_total"],
                        tenant_id=activation["tenant_id"],
                        customer_email=activation.get("customer_email"),
                    )
                    # First paid invoice → reward whoever referred this tenant.
                    # Idempotent (UNIQUE referred_tenant_id) + never raises.
                    from backend.services.referral_reward import (
                        grant_referral_reward_for_signup,
                    )
                    await grant_referral_reward_for_signup(
                        referred_tenant_id=activation["tenant_id"],
                    )
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            if _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on subscription event (add-on retired 2026-06-10)")
            else:
                _handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            if _is_legacy_marketing_addon(data):
                logger.info("Ignoring legacy marketing add-on subscription event (add-on retired 2026-06-10)")
            else:
                _handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)
        elif event_type == "invoice.payment_succeeded":
            # Dunning recovery: a recovered card un-pauses the tenant. Without
            # this branch a tenant whose card recovered stayed paused forever on
            # this endpoint (the /webhooks/stripe endpoint already handled it).
            await _handle_payment_succeeded(db, data)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Stripe webhook handler failed for event %s", event_type)
        # Release the in-flight idempotency row so Stripe's retry reprocesses
        # instead of short-circuiting on the NULL-response row and permanently
        # dropping the event (GH #308).
        await delete_key(db, idempotency_key)
        # Return 500 so Stripe retries (Stripe retries for up to 3 days)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    response_body = {"status": "ok"}
    await record_response(db, idempotency_key, 200, response_body)
    return response_body


AMOUNT_TO_PLAN: dict[int, str] = {
    # Current pricing (2026-06-15 repricing)
    1999: "chatbot",         # $19.99/mo chatbot plan
    9999: "agent_os",        # $99.99/mo agent_os plan
}

# Keywords to match in product/price descriptions
PLAN_KEYWORDS: dict[str, str] = {
    "chatbot": "chatbot",
    "agent_os": "agent_os",
    "agent os": "agent_os",
}


def _resolve_plan(session: dict) -> str | None:
    """Determine plan from metadata, line items, or amount."""
    metadata = session.get("metadata", {})
    plan = metadata.get("plan")
    logger.info("_resolve_plan: metadata.plan=%s", plan)
    if plan and plan in {"free", "chatbot", "agent_os"}:
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


def _is_legacy_marketing_addon(obj: dict) -> bool:
    """The $49.99 Marketing Suite add-on was retired 2026-06-10 (features now
    plan-included and surfaced via Agent OS). Events from any still-live
    legacy add-on subscription must NOT reach the main plan handlers — they
    would overwrite the tenant's primary plan_status. Recognize them by the
    Stripe metadata tag and ignore."""
    metadata = obj.get("metadata") or {}
    if metadata.get("addon") == "marketing":
        return True
    sub_meta = (obj.get("subscription_data") or {}).get("metadata") or {}
    return sub_meta.get("addon") == "marketing"


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


def _handle_checkout_completed(db, session: dict) -> dict | None:
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
        return None
    if not plan:
        payment_status = session.get("payment_status", "unknown")
        session_id = session.get("id", "unknown")
        customer = session.get("customer", "unknown")
        # LOUD error — greppable / alertable in log aggregators (Railway, Sentry,
        # Datadog, etc. alert on ERROR-level lines).
        # Fires when a comped ($0 / 100%-off coupon) checkout or any checkout
        # completes but carries no resolvable plan in metadata or line items.
        # The tenant is NOT activated.  No default plan is assigned — that would
        # be a billing risk.  Owner must fix the Stripe checkout metadata (add a
        # 'plan' key) and resend or manually activate the tenant.
        logger.error(
            "checkout.session.completed: TENANT NOT ACTIVATED — plan unresolvable. "
            "session_id=%s customer=%s payment_status=%s tenant_id=%s "
            "amount_total=%s metadata=%s. "
            "Action required: add 'plan' key to Stripe checkout/subscription metadata "
            "for this session and manually activate the tenant if comped.",
            session_id,
            customer,
            payment_status,
            tenant_id,
            session.get("amount_total"),
            session.get("metadata"),
        )
        return None

    fraud_reason = guard_checkout_for_fraud(session)
    if fraud_reason:
        logger.warning(
            "checkout.session.completed: fraud detected for tenant %s - %s. Pausing activation.",
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
            activity_type="fraud_alert",
            description=f"Checkout flagged: {fraud_reason}. Subscription paused pending review.",
            metadata={"fraud_reason": fraud_reason, "session_id": session.get("id")},
        )
        return None

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

    # Feature 3: log paid conversion for funnel analytics
    try:
        log_activity(
            tenant_id=tenant_id,
            activity_type="subscription_activated",
            description=f"Subscription activated: plan={plan}",
            metadata={"plan": plan, "amount_total": session.get("amount_total", 0)},
        )
    except Exception as exc:
        logger.warning(
            "checkout.session.completed: log_activity failed (tenant=%s)",
            tenant_id,
            exc_info=exc,
        )

    # Return activation info so the async caller can send the owner alert (Feature 5)
    return {
        "event": "activated",
        "plan": plan,
        "amount_total": session.get("amount_total", 0),
        "tenant_id": tenant_id,
        "customer_email": session.get("customer_email"),
    }


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

    trial_end = subscription.get("trial_end")
    update_data["stripe_trial_end"] = _unix_to_iso(trial_end) if trial_end else None

    db.table("tenants").update(update_data).eq("id", tenant_id).execute()
    logger.info("Tenant %s subscription updated (plan=%s)", tenant_id, plan)


def _handle_usage_pack_completed(db, session: dict) -> None:
    """Webhook handler for a completed usage-pack one-time purchase.

    Inserts a tenant_usage_packs row to raise the effective AI token cap
    for the current billing period. Idempotent via stripe_session_id UNIQUE.
    """
    from backend.routers.billing_usage import USAGE_PACK_TOKENS

    metadata = session.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    stripe_session_id = session.get("id")

    if not tenant_id:
        logger.warning(
            "usage_pack webhook: no tenant_id in metadata (session=%s)", stripe_session_id
        )
        return

    from backend.services.ai_usage_guard import current_period_month

    period = current_period_month()

    try:
        db.table("tenant_usage_packs").insert(
            {
                "tenant_id": tenant_id,
                "tokens": USAGE_PACK_TOKENS,
                "period": period,
                "stripe_session_id": stripe_session_id,
            }
        ).execute()
        logger.info(
            "Usage pack applied: tenant=%s tokens=%d period=%s session=%s",
            tenant_id,
            USAGE_PACK_TOKENS,
            period,
            stripe_session_id,
        )
    except Exception:
        # Attempt idempotent replay: if a row with this session_id already exists,
        # it's a duplicate webhook delivery — log and ignore.
        try:
            existing = (
                db.table("tenant_usage_packs")
                .select("id")
                .eq("stripe_session_id", stripe_session_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.info(
                    "usage_pack idempotent replay: session=%s already inserted", stripe_session_id
                )
                return
        except Exception:
            pass
        logger.exception(
            "usage_pack insert failed for tenant=%s session=%s", tenant_id, stripe_session_id
        )


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


async def _handle_payment_succeeded(db, invoice: dict) -> None:
    """Dunning recovery: a successful invoice payment un-pauses the tenant.

    Resets billing_dunning_attempt_count and restores plan_status to active —
    but ONLY when the tenant was paused BY dunning (attempt_count > 0). A
    fraud-flagged checkout also sets plan_status='paused' with a zero dunning
    count; that pause must survive payment events and clear only via manual
    review. Without this handler, a tenant whose card recovered after
    failures stayed paused forever (found by tests/test_billing_dunning_e2e.py).
    """
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    result = (
        db.table("tenants")
        .select("id, plan_status, billing_dunning_attempt_count")
        .eq("stripe_customer_id", customer_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return

    tenant = result.data[0]
    dunning_count = int(tenant.get("billing_dunning_attempt_count") or 0)
    if dunning_count <= 0:
        return  # not a dunning pause (or nothing to recover) — leave untouched

    update: dict[str, Any] = {"billing_dunning_attempt_count": 0}
    # Restore access from either dunning-locked status. invoice.payment_failed
    # writes "paused"; a near-simultaneous customer.subscription.updated can
    # overwrite that with "past_due". Both are pay-gated, so recovery must clear
    # either one deterministically — checking only "paused" left a recovered
    # tenant stuck in past_due when the subscription event landed last.
    if tenant.get("plan_status") in ("paused", "past_due"):
        update["plan_status"] = "active"
    db.table("tenants").update(update).eq("id", tenant["id"]).execute()
    logger.info(
        "Tenant %s payment recovered after %d dunning attempt(s); plan restored",
        tenant["id"],
        dunning_count,
    )


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
