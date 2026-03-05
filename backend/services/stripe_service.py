"""Stripe client singleton and billing helpers."""


import logging

import stripe

from backend.config import settings

logger = logging.getLogger(__name__)

_initialized = False

PLAN_PRICES: dict[str, dict[str, str]] = {
    "foundation": {
        "setup": "price_foundation_setup",
        "monthly": "price_foundation_monthly",
    },
    "growth": {"monthly": "price_growth_monthly"},
    "operations": {"monthly": "price_operations_monthly"},
    "enterprise": {"monthly": "price_enterprise_monthly"},
}

PLAN_LIMITS: dict[str, int] = {
    "free": 50,
    "foundation": 500,
    "growth": 2000,
    "operations": 10000,
    "enterprise": 100000,
}


def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        stripe.api_key = settings.stripe_secret_key
        _initialized = True


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
