"""Widget config update service."""

from typing import Any

from fastapi import HTTPException

from backend.models.database import get_service_supabase as _get_service_supabase


def _get_db():
    return _get_service_supabase()


def update_widget_config_service(
    tenant_id: str,
    req: Any,  # WidgetConfigUpdateRequest — avoid circular import
) -> dict:
    """Update widget_configs row and return the updated row dict."""
    from backend.services.branding_helpers import (
        _filter_branding_for_plan,
        _sanitize_css,
    )

    db = _get_db()

    tenant_result = (
        db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    )
    plan = tenant_result.data[0].get("plan") or "free" if tenant_result.data else "free"

    updates = {
        k: v for k, v in req.model_dump(exclude={"branding"}).items() if v is not None
    }

    if req.branding is not None:
        branding_dict = req.branding.model_dump(exclude_none=True)
        if "custom_css" in branding_dict:
            branding_dict["custom_css"] = _sanitize_css(branding_dict["custom_css"])
        branding_dict = _filter_branding_for_plan(branding_dict, plan)
        existing = (
            db.table("widget_configs")
            .select("branding")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        existing_branding = (
            (existing.data[0].get("branding") or {}) if existing.data else {}
        )
        existing_branding.update(branding_dict)
        updates["branding"] = existing_branding

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        db.table("widget_configs").update(updates).eq("tenant_id", tenant_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget config not found")

    return result.data[0]
