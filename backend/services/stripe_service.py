"""Stripe client singleton and billing helpers."""


import logging

import stripe

from backend.config import settings

logger = logging.getLogger(__name__)

_initialized = False
_warned_placeholder_prices = False

_PLACEHOLDER_PRICE_IDS = {
    "price_chatbot_monthly",
    "price_agent_os_monthly",
    "price_usage_pack",
}


def _price_id(env_value: str, fallback: str) -> str:
    value = (env_value or "").strip()
    return value or fallback


# Price IDs are env-backed so production can use real Stripe prices without
# hardcoding live identifiers in the repo. Fallback placeholders are kept for
# local/test environments and are warned on at runtime.
#
# Two purchasable plans (2026-06-15 repricing):
#   chatbot   — $19.99/mo  (widget/chatbot features only)
#   agent_os  — $99.99/mo  (full platform)
# "free" is the internal lapsed/no-active-subscription state only; never sold.
PLAN_PRICES: dict[str, dict[str, str]] = {
    "chatbot": {"monthly": _price_id(settings.stripe_price_chatbot_monthly, "price_chatbot_monthly")},
    "agent_os": {"monthly": _price_id(settings.stripe_price_agent_os_monthly, "price_agent_os_monthly")},
}

# One-time usage-pack price (overage top-up)
USAGE_PACK_PRICE_ID: str = _price_id(settings.stripe_price_usage_pack, "price_usage_pack")


def ensure_plan_prices_configured(plan: str) -> dict[str, str]:
    """Return Stripe price IDs for a plan, or raise if placeholders remain."""
    prices = PLAN_PRICES[plan]
    placeholder_kinds = [
        kind for kind, price in prices.items() if price in _PLACEHOLDER_PRICE_IDS
    ]
    if placeholder_kinds:
        raise RuntimeError(
            f"Stripe price IDs for {plan} are not configured: "
            + ", ".join(placeholder_kinds)
        )

    malformed_kinds = [
        kind for kind, price in prices.items() if not price.startswith("price_")
    ]
    if malformed_kinds:
        raise RuntimeError(
            f"Stripe price IDs for {plan} should look like price_...: "
            + ", ".join(malformed_kinds)
        )

    return prices


def ensure_stripe_configured() -> None:
    """Initialize Stripe or raise a deploy-time actionable error."""
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
    _ensure_initialized()


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
    ensure_stripe_configured()

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
