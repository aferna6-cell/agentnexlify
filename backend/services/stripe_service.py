"""Stripe client singleton and billing helpers."""


import logging

import stripe

from backend.config import settings

logger = logging.getLogger(__name__)

_initialized = False
_warned_placeholder_prices = False

_PLACEHOLDER_PRICE_IDS = {
    "price_growth_monthly",
    "price_professional_monthly",
    "price_autopilot_monthly",
    "price_enterprise_monthly",
}


def _price_id(env_value: str, fallback: str) -> str:
    value = (env_value or "").strip()
    return value or fallback


# Price IDs are env-backed so production can use real Stripe prices without
# hardcoding live identifiers in the repo. Fallback placeholders are kept for
# local/test environments and are warned on at runtime.
PLAN_PRICES: dict[str, dict[str, str]] = {
    "growth": {"monthly": _price_id(settings.stripe_price_growth_monthly, "price_growth_monthly")},
    "professional": {"monthly": _price_id(settings.stripe_price_professional_monthly, "price_professional_monthly")},
    "autopilot": {"monthly": _price_id(settings.stripe_price_autopilot_monthly, "price_autopilot_monthly")},
    "enterprise": {"monthly": _price_id(settings.stripe_price_enterprise_monthly, "price_enterprise_monthly")},
}

PLAN_LIMITS: dict[str, int] = {
    # All plans now have unlimited conversations.
    # Kept as a reference map only — not enforced.
}


def _ensure_initialized() -> None:
    global _initialized, _warned_placeholder_prices
    if not _initialized:
        stripe.api_key = settings.stripe_secret_key
        _initialized = True
    if not _warned_placeholder_prices:
        placeholder_plans = sorted(
            plan
            for plan, prices in PLAN_PRICES.items()
            if prices.get("monthly") in _PLACEHOLDER_PRICE_IDS
        )
        if placeholder_plans:
            logger.warning(
                "Stripe price IDs are using placeholder values for plans: %s. "
                "Set STRIPE_PRICE_* env vars before enabling live checkout.",
                ", ".join(placeholder_plans),
            )
        _warned_placeholder_prices = True


def get_or_create_customer(
    email: str, tenant_id: str, business_name: str | None = None
) -> stripe.Customer:
    """Find existing Stripe customer by tenant metadata, or create one."""
    _ensure_initialized()

    # Search for existing customer with this tenant_id
    existing = stripe.Customer.search(
        query=f'metadata["tenant_id"]:"{tenant_id}"'
    )
    if existing.data:
        return existing.data[0]

    params: dict = {
        "email": email,
        "metadata": {"tenant_id": tenant_id},
    }
    if business_name:
        params["name"] = business_name

    customer = stripe.Customer.create(**params)
    logger.info("Created Stripe customer %s for tenant %s", customer.id, tenant_id)
    return customer
