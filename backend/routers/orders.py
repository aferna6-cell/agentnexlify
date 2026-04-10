"""Order management endpoints for restaurant tenants."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


# --- Models ---

class OrderCreate(BaseModel):
    customer_name: str | None = Field(None, max_length=200)
    customer_phone: str | None = Field(None, max_length=30)
    customer_email: str | None = Field(None, max_length=200)
    items_json: list[dict] = Field(...)
    subtotal: float = Field(..., ge=0)
    tax: float = Field(0, ge=0)
    total: float = Field(..., ge=0)
    order_type: str = Field("pickup", pattern="^(pickup|delivery)$")
    delivery_address: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=1000)
    session_id: str | None = None
    lead_id: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(new|confirmed|preparing|ready|delivered|cancelled)$")


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Endpoints ---

@router.get("/{tenant_id}")
async def list_orders(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List orders for a tenant, newest first."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    query = (
        db.table("orders")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"orders": result.data or [], "count": len(result.data or [])}


@router.get("/{tenant_id}/stats")
async def order_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get order stats for dashboard cards."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("orders")
        .select("status, total")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    orders = result.data or []

    stats = {
        "total_orders": len(orders),
        "new_orders": sum(1 for o in orders if o["status"] == "new"),
        "active_orders": sum(1 for o in orders if o["status"] in ("confirmed", "preparing")),
        "total_revenue": sum(float(o["total"]) for o in orders if o["status"] not in ("cancelled",)),
    }
    return stats


@router.post("/{tenant_id}")
async def create_order(
    tenant_id: str,
    req: OrderCreate,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Create a new order (usually from the chat widget flow)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    data = {
        "tenant_id": tenant_id,
        "customer_name": req.customer_name,
        "customer_phone": req.customer_phone,
        "customer_email": req.customer_email,
        "items_json": req.items_json,
        "subtotal": req.subtotal,
        "tax": req.tax,
        "total": req.total,
        "order_type": req.order_type,
        "delivery_address": req.delivery_address,
        "notes": req.notes,
        "session_id": req.session_id,
        "lead_id": req.lead_id,
        "status": "new",
    }
    result = db.table("orders").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create order")
    return result.data[0]


@router.put("/{tenant_id}/{order_id}/status")
async def update_order_status(
    tenant_id: str,
    order_id: str,
    req: OrderStatusUpdate,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Update order status (new -> confirmed -> preparing -> ready -> delivered)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("orders")
        .update({"status": req.status})
        .eq("id", order_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    return result.data[0]


@router.get("/{tenant_id}/{order_id}")
async def get_order(
    tenant_id: str,
    order_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single order by ID."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("orders")
        .select("*")
        .eq("id", order_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    return result.data[0]
