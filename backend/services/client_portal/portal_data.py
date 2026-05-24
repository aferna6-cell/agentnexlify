"""Pure async DB fetchers used by the public portal and client-me endpoints.

Each helper takes the Supabase client and returns a dict (single row) or list
(multiple rows). Helpers raise the caller's HTTPException semantics through
the boolean ``critical`` flag: critical=True raises HTTP 500 on DB error,
critical=False logs a warning and returns the fallback. Keeps the router
thin and lets tests target the data layer separately.
"""

import logging
from typing import Any

from fastapi import HTTPException

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

__all__ = [
    "fetch_business",
    "fetch_customer",
    "fetch_service_records",
    "fetch_appointments",
    "fetch_invoices",
    "fetch_documents",
    "fetch_widget_config",
    "fetch_client_login_enabled",
    "fetch_tenant_business_info_with_slug",
]


def fetch_business(db: Any, tenant_id: str, with_slug: bool = False) -> dict:
    """Fetch business info (id, business_name, owner_email, city). Raises HTTP 500 on DB error."""
    select_cols = "id, business_name, owner_email, city, business_slug" if with_slug else "id, business_name, owner_email, city"
    try:
        result = (
            tenant_table(db, "tenants", tenant_id)
            .select(select_cols)
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch tenant %s for portal", tenant_id)
        raise HTTPException(status_code=500, detail="Internal error")
    return result.data[0] if result.data else {}


def fetch_customer(db: Any, tenant_id: str, lead_id: str) -> dict:
    """Fetch lead (id, name, email, phone). Uses client_id filter. Raises HTTP 500 on DB error."""
    try:
        result = (
            tenant_table(db, "leads", tenant_id)
            .select("id, name, email, phone")
            .eq("id", lead_id)
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch lead %s for portal", lead_id)
        raise HTTPException(status_code=500, detail="Internal error")
    return result.data[0] if result.data else {}


def fetch_service_records(db: Any, tenant_id: str, lead_id: str) -> list[dict]:
    """Fetch service records for a lead. Raises HTTP 500 on DB error."""
    try:
        result = (
            tenant_table(db, "service_records", tenant_id)
            .select("id, title, description, service_date, photos_json, documents_json, invoice_amount, created_at")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("service_date", desc=True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch service records for portal, lead %s", lead_id)
        raise HTTPException(status_code=500, detail="Internal error")
    return result.data or []


def fetch_appointments(db: Any, tenant_id: str, lead_id: str) -> list[dict]:
    """Fetch up to 20 most recent appointments for a lead. Logs and returns [] on error."""
    try:
        result = (
            tenant_table(db, "appointments", tenant_id)
            .select("id, customer_name, start_time, end_time, status, notes")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("start_time", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch appointments for client %s", lead_id)
        return []
    return result.data or []


def fetch_invoices(db: Any, tenant_id: str, lead_id: str) -> list[dict]:
    """Fetch up to 20 most recent invoices for a lead. Logs and returns [] on error."""
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("id, invoice_number, items_json, subtotal, tax, total, status, created_at, due_date")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch invoices for client %s", lead_id)
        return []
    return result.data or []


def fetch_documents(db: Any, tenant_id: str, lead_id: str) -> list[dict]:
    """Fetch up to 20 most recent documents for a lead. Logs and returns [] on error."""
    try:
        result = (
            tenant_table(db, "documents", tenant_id)
            .select("id, title, status, created_at, signed_at")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch documents for client %s", lead_id)
        return []
    return result.data or []


def fetch_widget_config(db: Any, tenant_id: str) -> tuple[bool, str | None]:
    """Return (rebook_enabled, widget_api_key). Logs and returns (False, None) on error."""
    try:
        result = (
            tenant_table(db, "widget_configs", tenant_id)
            .select("booking_enabled, api_key")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return (
                bool(result.data[0].get("booking_enabled")),
                result.data[0].get("api_key"),
            )
    except Exception:
        logger.warning("Failed to check widget config for tenant %s", tenant_id)
    return False, None


def fetch_client_login_enabled(db: Any, tenant_id: str) -> bool:
    """Return whether client login is enabled. Logs and returns False on error."""
    try:
        result = (
            tenant_table(db, "tenants", tenant_id)
            .select("client_login_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return bool(result.data[0].get("client_login_enabled"))
    except Exception:
        logger.warning("Failed to check client_login_enabled for tenant %s", tenant_id)
    return False


def fetch_tenant_business_info_with_slug(db: Any, tenant_id: str) -> dict:
    """Convenience wrapper matching client_me's select shape (includes business_slug)."""
    return fetch_business(db, tenant_id, with_slug=True)
