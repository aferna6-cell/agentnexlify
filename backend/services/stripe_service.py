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
    "price_marketing_addon_monthly",
}


MARKETING_ADDON_PRICE_ID = ""  # set in _ensure_initialized below


# Stripe metadata key used to distinguish add-on subscriptions from primary
# plan subscriptions in webhook handlers.
STRIPE_ADDON_METADATA_KEY = "addon"
STRIPE_ADDON_MARKETING_VALUE = "marketing"


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


def get_marketing_addon_price_id() -> str:
    """Return configured Stripe price id for Marketing Suite add-on."""
    return _price_id(
        settings.stripe_price_marketing_addon_monthly, "price_marketing_addon_monthly"
    )


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
        if get_marketing_addon_price_id() in _PLACEHOLDER_PRICE_IDS:
            logger.warning(
                "Marketing add-on Stripe price uses placeholder. "
                "Set STRIPE_PRICE_MARKETING_ADDON_MONTHLY before enabling add-on checkout."
            )
        _warned_placeholder_prices = True


def create_marketing_addon_checkout_session(
    tenant_id: str,
    customer_id: str,
    success_url: str,
    cancel_url: str,
) -> stripe.checkout.Session:
    """Create a Stripe Checkout session for the Marketing Suite add-on.

    Creates a SEPARATE subscription from the primary plan (answer #4 = A).
    Subscription metadata[addon]=marketing so webhook can distinguish it.
    """
    _ensure_initialized()
    price_id = get_marketing_addon_price_id()
    if price_id in _PLACEHOLDER_PRICE_IDS:
        raise RuntimeError(
            "STRIPE_PRICE_MARKETING_ADDON_MONTHLY is not configured."
        )
    if not price_id.startswith("price_"):
        raise RuntimeError(
            "STRIPE_PRICE_MARKETING_ADDON_MONTHLY should look like price_..."
        )

    return stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "tenant_id": tenant_id,
            STRIPE_ADDON_METADATA_KEY: STRIPE_ADDON_MARKETING_VALUE,
        },
        subscription_data={
            "metadata": {
                "tenant_id": tenant_id,
                STRIPE_ADDON_METADATA_KEY: STRIPE_ADDON_MARKETING_VALUE,
            },
        },
    )


def cancel_marketing_addon_subscription(subscription_id: str) -> stripe.Subscription:
    """Cancel the add-on subscription at period end (no immediate revocation)."""
    _ensure_initialized()
    return stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)


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
