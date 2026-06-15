"""Buy-more-usage endpoint — overage top-up via Stripe one-time checkout.

Separated from billing.py (already >600 lines) per Rule 12 (new concerns
into new files) and Rule 9 (do not extend god classes).
"""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.stripe_service import USAGE_PACK_PRICE_ID, ensure_stripe_configured
from backend.services.ai_usage_guard import current_period_month

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/billing",
    tags=["billing"],
)

# Tokens credited per one-time usage pack purchase.
# Operator sets STRIPE_PRICE_USAGE_PACK on Railway; this constant controls
# how many tokens that price entitles the tenant to.
USAGE_PACK_TOKENS = 1_000_000  # 1 million tokens per pack


@router.post("/buy-usage")
async def buy_usage(claims: dict = Depends(_get_current_tenant)):
    """Create a Stripe Checkout session (one-time payment) for a usage pack.

    Returns {checkout_url} for the frontend to redirect to.
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")

    if USAGE_PACK_PRICE_ID == "price_usage_pack":
        raise HTTPException(
            status_code=503,
            detail="Usage packs are not yet configured. Set STRIPE_PRICE_USAGE_PACK.",
        )

    try:
        ensure_stripe_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db = get_service_supabase()
    tenant_result = (
        db.table("tenants")
        .select("id, owner_email, stripe_customer_id, business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = tenant_result.data[0]

    session_params: dict = {
        "mode": "payment",
        "line_items": [{"price": USAGE_PACK_PRICE_ID, "quantity": 1}],
        "success_url": (
            f"{settings.frontend_url}/billing?usage_pack_success=1"
            "&session_id={CHECKOUT_SESSION_ID}"
        ),
        "cancel_url": f"{settings.frontend_url}/billing",
        "metadata": {
            "tenant_id": tenant_id,
            "kind": "usage_pack",
        },
    }

    # Attach existing Stripe customer if available
    stripe_customer_id = tenant.get("stripe_customer_id")
    if stripe_customer_id:
        session_params["customer"] = stripe_customer_id
    else:
        owner_email = tenant.get("owner_email")
        if owner_email:
            session_params["customer_email"] = owner_email

    session = stripe.checkout.Session.create(**session_params)
    logger.info(
        "Created usage-pack checkout session %s for tenant %s",
        session.id,
        tenant_id,
    )
    return {"checkout_url": session.url}
