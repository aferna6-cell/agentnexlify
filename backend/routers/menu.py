"""Menu management endpoints for restaurant tenants."""

import json
import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
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


@router.post("/{tenant_id}/import-from-website")
async def import_menu_from_website(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Extract menu items from crawled website content using Claude AI."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Get crawled website content
    crawl_result = (
        db.table("website_content")
        .select("extracted_text")
        .eq("tenant_id", tenant_id)
        .eq("crawl_status", "completed")
        .order("crawled_at", desc=True)
        .limit(1)
        .execute()
    )
    if not crawl_result.data or not crawl_result.data[0].get("extracted_text"):
        raise HTTPException(
            status_code=400,
            detail="No website content available. Scan your website first in Settings.",
        )

    website_text = crawl_result.data[0]["extracted_text"]
    # Truncate to keep within token limits
    if len(website_text) > 15000:
        website_text = website_text[:15000]

    # Use Claude to extract menu items
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"""Extract menu items from this restaurant website content. Return ONLY a JSON array of menu items. Each item should have: name (string), description (string or null), price (number), category (string like "Appetizers", "Entrees", "Desserts", "Drinks", etc.).

If you cannot find any menu items, return an empty array [].

Website content:
{website_text}

Return ONLY valid JSON, no markdown, no explanation. Example:
[{{"name": "Margherita Pizza", "description": "Fresh mozzarella, basil, tomato sauce", "price": 14.99, "category": "Pizza"}}]""",
            }],
        )

        # Parse the response
        text = response.content[0].text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        items = json.loads(text)
        if not isinstance(items, list):
            raise ValueError("Expected JSON array")

    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.warning("Menu extraction parse failed: %s", e)
        raise HTTPException(
            status_code=422,
            detail="Could not extract menu items from the website. Try adding items manually.",
        )
    except anthropic.APIError as e:
        logger.warning("Claude API error during menu extraction: %s", e)
        raise HTTPException(
            status_code=502,
            detail="AI service temporarily unavailable. Please try again.",
        )

    if not items:
        return {"imported": 0, "items": [], "message": "No menu items found on the website."}

    # Insert extracted items
    inserted = []
    for idx, item in enumerate(items[:100]):  # max 100 items
        if not item.get("name") or not isinstance(item.get("price"), (int, float)):
            continue
        data = {
            "tenant_id": tenant_id,
            "name": str(item["name"])[:200],
            "description": str(item.get("description") or "")[:1000] or None,
            "price": round(float(item["price"]), 2),
            "category": str(item.get("category") or "uncategorized")[:100],
            "modifiers_json": [],
            "available": True,
            "sort_order": idx,
        }
        try:
            result = db.table("menu_items").insert(data).execute()
            if result.data:
                inserted.append(result.data[0])
        except Exception:
            logger.warning("Failed to insert menu item: %s", item.get("name"))

    return {
        "imported": len(inserted),
        "items": inserted,
        "message": f"Imported {len(inserted)} menu items from your website.",
    }
