"""Persistable tenants.business_type values.

Warehouse / Logistics free text maps to warehouse_logistics only when
WAREHOUSE_LOGISTICS_ENABLED is on. Until migration 203 is applied the flag
stays off and those strings save as other, which is already in the CHECK
allowlist.
"""

from __future__ import annotations

from backend.config import settings

WAREHOUSE_FREE_TEXT = frozenset(
    {
        "logistics",
        "freight",
        "fulfillment",
        "distribution",
        "3pl",
        "warehouse",
        "warehousing",
        "warehouse_logistics",
        "third_party_logistics",
    }
)


def warehouse_logistics_enabled() -> bool:
    return bool(settings.warehouse_logistics_enabled)


def normalize_business_type_token(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_warehouse_logistics_token(value: str | None) -> bool:
    return normalize_business_type_token(value) in WAREHOUSE_FREE_TEXT


def stored_business_type(value: str | None) -> str:
    """Value safe to write to tenants.business_type."""
    token = normalize_business_type_token(value)
    if not token:
        return "other"
    if is_warehouse_logistics_token(token):
        return "warehouse_logistics" if warehouse_logistics_enabled() else "other"
    return token


def business_type_for_wizard_write(raw: str | None) -> str:
    """Wizard free-text industry before the tenants update."""
    return stored_business_type(raw)


def business_type_for_settings_write(raw: str | None) -> str:
    """Settings business type before the tenants update."""
    return stored_business_type(raw)


def business_type_for_website_inference_write(raw: str | None) -> str:
    """Industry inferred from a crawled site before the tenants update."""
    return stored_business_type(raw)


def apply_website_inferred_business_type(db, tenant_id: str, inferred: str | None) -> str:
    """Write a website-inferred industry onto tenants.business_type."""
    saved = business_type_for_website_inference_write(inferred)
    db.table("tenants").update({"business_type": saved}).eq("id", tenant_id).execute()
    return saved
