"""Stripe client singleton and billing helpers."""


import logging

import stripe

from backend.config import settings

logger = logging.getLogger(__name__)

_initialized = False

PLAN_PRICES: dict[str, dict[str, str]] = {
    "growth": {"monthly": "price_growth_monthly"},
    "professional": {"monthly": "price_professional_monthly"},
    "autopilot": {"monthly": "price_autopilot_monthly"},
    "enterprise": {"monthly": "price_enterprise_monthly"},
}

PLAN_LIMITS: dict[str, int] = {
    # All plans now have unlimited conversations.
    # Kept as a reference map only — not enforced.
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
