"""Add-on subscription checkout — voice receptionist (+$49.99/mo).

Separate concern from plan checkout (auth_billing.py) and one-time usage
packs (billing_usage.py): an add-on is a SECOND recurring subscription on
top of the tenant's plan, tagged metadata.addon='voice' so the plan webhook
handlers never touch it (same isolation mechanism as the retired marketing
add-on — see billing.py `_is_legacy_marketing_addon`).

Market: chatbot-plan tenants who want live AI phone answering without the
jump to agent_os ($99.99). agent_os and grandfathered plans already include
voice; the endpoint refuses to double-charge them.

Critical rules: no `from __future__ import annotations`; never log secrets.
"""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException

from backend.config import settings
from backend.dependencies import require_role, block_demo_role
from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.stripe_service import (
    VOICE_ADDON_PRICE_ID,
    ensure_stripe_configured,
    get_or_create_customer,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["billing"],
    dependencies=[Depends(block_demo_role)],
)

VOICE_ADDON_PRICE_USD = 49.99

# Plans whose contract already includes live AI voice (see
# voice_phone_routing._AI_VOICE_PLANS) — the add-on would double-charge them.
_VOICE_INCLUDED_PLANS = {"agent_os", "agent_os_managed", "professional", "enterprise"}
_PAID_STATUSES = {"active", "trialing"}


def get_service_supabase():
    """Module-level indirection so tests can patch billing_addons.get_service_supabase."""
    return _get_service_supabase()


@router.post("/billing/voice-addon/checkout")
async def voice_addon_checkout(claims: dict = Depends(require_role("owner"))):
    """Create a Stripe checkout for the voice add-on subscription."""
    tenant_id = claims["tenant_id"]

    if VOICE_ADDON_PRICE_ID == "price_voice_addon_monthly":
        raise HTTPException(
            status_code=503,
            detail="Voice add-on is not yet configured. Set STRIPE_PRICE_VOICE_ADDON_MONTHLY.",
        )
    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("id, owner_email, business_name, plan, plan_status, voice_addon_active")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = result.data[0]

    plan = tenant.get("plan") or "free"
    if plan == "free" or (tenant.get("plan_status") or "") not in _PAID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="An active paid plan is required before adding the voice add-on.",
        )
    if plan in _VOICE_INCLUDED_PLANS:
        raise HTTPException(
            status_code=400,
            detail="Your plan already includes live AI voice answering.",
        )
    if tenant.get("voice_addon_active"):
        raise HTTPException(status_code=400, detail="Voice add-on is already active.")

    customer = get_or_create_customer(
        email=tenant.get("owner_email") or "",
        tenant_id=tenant_id,
        business_name=tenant.get("business_name"),
    )

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer=customer.id,
        line_items=[{"price": VOICE_ADDON_PRICE_ID, "quantity": 1}],
        success_url=f"{settings.frontend_url}/dashboard?voice_addon_success=1&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/billing",
        metadata={"tenant_id": tenant_id, "addon": "voice"},
        subscription_data={
            "metadata": {"tenant_id": tenant_id, "addon": "voice"},
        },
    )
    logger.info(
        "Created voice add-on checkout session %s for tenant %s", session.id, tenant_id
    )
    return {"checkout_url": session.url}
