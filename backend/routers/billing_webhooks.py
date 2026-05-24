"""Billing webhook event handlers — plan resolution, subscription lifecycle, payment failures."""


import html as html_mod
import logging
from datetime import datetime, timezone
from typing import Any

from backend.config import settings
from backend.services.fraud_guard import guard_checkout_for_fraud
from backend.services.activity import log_activity

logger = logging.getLogger(__name__)


AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    89900: "enterprise",
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

    amount = session.get("amount_total")
    logger.info("_resolve_plan: amount_total=%s, known amounts=%s", amount, list(AMOUNT_TO_PLAN.keys()))
    if amount and amount in AMOUNT_TO_PLAN:
        return AMOUNT_TO_PLAN[amount]

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
            activity_type="fraud_alert",
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
