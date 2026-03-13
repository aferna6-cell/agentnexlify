"""Menu management endpoints for restaurant tenants."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/menu", tags=["menu"])


# --- Models ---

class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: float = Field(..., ge=0, le=99999)
    category: str = Field("uncategorized", max_length=100)
    modifiers_json: list[dict] | None = None
    available: bool = True
    image_url: str | None = Field(None, max_length=500)
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, ge=0, le=99999)
    category: str | None = Field(None, max_length=100)
    modifiers_json: list[dict] | None = None
    available: bool | None = None
    image_url: str | None = Field(None, max_length=500)
    sort_order: int | None = None


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Endpoints ---

@router.get("/{tenant_id}")
async def list_menu_items(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    category: str | None = Query(None),
    available_only: bool = Query(False),
):
    """List all menu items for a tenant, optionally filtered by category."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("menu_items")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("category")
        .order("sort_order")
        .order("name")
    )

    if category:
        query = query.eq("category", category)
    if available_only:
        query = query.eq("available", True)

    result = query.execute()
    return {"items": result.data or [], "count": len(result.data or [])}


@router.get("/{tenant_id}/categories")
async def list_categories(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get unique categories for a tenant's menu."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("menu_items")
        .select("category")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    categories = sorted(set(item["category"] for item in (result.data or []) if item.get("category")))
    return {"categories": categories}


@router.post("/{tenant_id}")
async def create_menu_item(
    tenant_id: str,
    req: MenuItemCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new menu item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": req.name,
        "description": req.description,
        "price": req.price,
        "category": req.category,
        "modifiers_json": req.modifiers_json or [],
        "available": req.available,
        "image_url": req.image_url,
        "sort_order": req.sort_order,
    }
    result = db.table("menu_items").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create menu item")
    return result.data[0]


@router.put("/{tenant_id}/{item_id}")
async def update_menu_item(
    tenant_id: str,
    item_id: str,
    req: MenuItemUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update an existing menu item."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("menu_items")
        .update(updates)
        .eq("id", item_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return result.data[0]


@router.delete("/{tenant_id}/{item_id}")
async def delete_menu_item(
    tenant_id: str,
    item_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a menu item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("menu_items")
        .delete()
        .eq("id", item_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"deleted": True}


@router.put("/{tenant_id}/{item_id}/toggle")
async def toggle_availability(
    tenant_id: str,
    item_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Toggle menu item availability (in stock / out of stock)."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    # Fetch current state
    current = (
        db.table("menu_items")
        .select("available")
        .eq("id", item_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Menu item not found")

    new_available = not current.data[0]["available"]
    result = (
        db.table("menu_items")
        .update({"available": new_available})
        .eq("id", item_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    return result.data[0]
