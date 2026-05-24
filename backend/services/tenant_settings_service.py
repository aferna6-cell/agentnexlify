"""Tenant settings + MCP key handler bodies extracted from auth.py.

Four service functions:
- `generate_mcp_key(tenant_id, claims)` — issue new MCP API key.
- `revoke_mcp_key(tenant_id, claims)` — clear MCP API key.
- `update_settings(tenant_id, request, claims)` — update tenant business fields.
- `get_tenant(tenant_id, claims)` — read tenant settings snapshot.

All four use `from backend.routers import auth as _auth` lazy lookup so test
patches on `backend.routers.auth.get_service_supabase` continue to intercept.
"""

import logging
import secrets

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

_ALLOWED_SETTINGS_FIELDS = {
    "business_name",
    "business_type",
    "city",
    "owner_name",
    "notification_phone",
    "sms_notifications_enabled",
    "google_review_link",
    "review_request_config",
    "website_url",
    "textback_enabled",
    "textback_message",
    "textback_quiet_start",
    "textback_quiet_end",
    "daily_briefing_enabled",
    "noshow_recovery_enabled",
}

_TENANT_SETTINGS_COLUMNS = (
    "id, business_name, business_type, city, owner_email, owner_name, plan, "
    "plan_status, notification_phone, sms_notifications_enabled, "
    "google_review_link, review_request_config, website_url, business_slug, "
    "business_page_enabled, textback_enabled, textback_message, "
    "textback_quiet_start, textback_quiet_end, client_login_enabled, "
    "daily_briefing_enabled, noshow_recovery_enabled"
)


async def generate_mcp_key(*, tenant_id: str, claims: dict) -> dict:
    from backend.routers import auth as _auth

    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    mcp_key = f"mcp_{secrets.token_urlsafe(32)}"

    db = _auth.get_service_supabase()
    result = (
        db.table("tenants")
        .update({"mcp_api_key": mcp_key, "mcp_enabled": True})
        .eq("id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {"mcp_api_key": mcp_key}


async def revoke_mcp_key(*, tenant_id: str, claims: dict) -> dict:
    from backend.routers import auth as _auth

    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = _auth.get_service_supabase()
    db.table("tenants").update({"mcp_api_key": None, "mcp_enabled": False}).eq(
        "id", tenant_id
    ).execute()
    return {"success": True}


async def update_settings(
    *, tenant_id: str, request: Request, claims: dict
) -> dict:
    from backend.routers import auth as _auth

    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    body = await request.json()
    updates = {
        k: v for k, v in body.items() if k in _ALLOWED_SETTINGS_FIELDS and v is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    db = _auth.get_service_supabase()
    logger.info("update_settings tenant_id=%s fields=%s", tenant_id, sorted(updates))
    try:
        result = db.table("tenants").update(updates).eq("id", tenant_id).execute()
    except Exception:
        logger.exception("update_settings failed for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update settings")
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]


async def get_tenant(*, tenant_id: str, claims: dict) -> dict:
    from backend.routers import auth as _auth

    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = _auth.get_service_supabase()
    result = (
        db.table("tenants")
        .select(_TENANT_SETTINGS_COLUMNS)
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data[0]
