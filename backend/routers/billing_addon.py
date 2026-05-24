"""Marketing Suite add-on webhook handlers — detection + lifecycle."""


import logging
from datetime import datetime, timezone

from backend.services.stripe_service import (
    STRIPE_ADDON_MARKETING_VALUE,
    STRIPE_ADDON_METADATA_KEY,
)

from backend.routers.billing_webhooks import (
    _resolve_tenant_from_subscription,
    _resolve_tenant_id,
)

logger = logging.getLogger(__name__)


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
