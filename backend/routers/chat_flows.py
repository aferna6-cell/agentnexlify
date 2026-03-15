"""Chat flows — visual conversation flow builder CRUD + preset templates."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat-flows", tags=["chat-flows"])

# --- Preset Flow Templates ---

PRESET_TEMPLATES = [
    {
        "name": "General Business",
        "description": "Greeting → FAQ → Appointment or transfer to human",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Hi! How can I help you today?"}, "position": {"x": 250, "y": 0}},
                {"id": "faq", "type": "ai_response", "data": {"label": "Answer FAQ"}, "position": {"x": 250, "y": 150}},
                {"id": "check_intent", "type": "condition", "data": {"label": "Wants appointment?", "condition": "appointment|schedule|book"}, "position": {"x": 250, "y": 300}},
                {"id": "book", "type": "action", "data": {"action": "show_booking", "label": "Show Booking Form"}, "position": {"x": 100, "y": 450}},
                {"id": "handoff", "type": "handoff", "data": {"label": "Transfer to Team"}, "position": {"x": 400, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "faq"},
                {"source": "faq", "target": "check_intent"},
                {"source": "check_intent", "target": "book", "label": "Yes"},
                {"source": "check_intent", "target": "handoff", "label": "No"},
            ],
        },
    },
    {
        "name": "Restaurant",
        "description": "Greeting → Menu → Order → Confirmation",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Welcome! Would you like to see our menu or place an order?"}, "position": {"x": 250, "y": 0}},
                {"id": "menu", "type": "action", "data": {"action": "show_menu", "label": "Show Menu"}, "position": {"x": 100, "y": 150}},
                {"id": "order", "type": "action", "data": {"action": "take_order", "label": "Take Order"}, "position": {"x": 400, "y": 150}},
                {"id": "confirm", "type": "action", "data": {"action": "confirm_order", "label": "Confirm Order"}, "position": {"x": 250, "y": 300}},
                {"id": "hours", "type": "ai_response", "data": {"label": "Answer Hours/Location"}, "position": {"x": 250, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "menu", "label": "Menu"},
                {"source": "greeting", "target": "order", "label": "Order"},
                {"source": "menu", "target": "order"},
                {"source": "order", "target": "confirm"},
                {"source": "greeting", "target": "hours", "label": "Other"},
            ],
        },
    },
    {
        "name": "Contractor / Service",
        "description": "Greeting → Service Type → Quote Request → Book Estimate",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Hi! What service can we help you with?"}, "position": {"x": 250, "y": 0}},
                {"id": "service", "type": "question", "data": {"label": "What service?", "question": "What type of service do you need?"}, "position": {"x": 250, "y": 150}},
                {"id": "quote", "type": "action", "data": {"action": "collect_info", "label": "Collect Quote Details"}, "position": {"x": 100, "y": 300}},
                {"id": "book", "type": "action", "data": {"action": "show_booking", "label": "Book Free Estimate"}, "position": {"x": 400, "y": 300}},
                {"id": "faq", "type": "ai_response", "data": {"label": "Answer Questions"}, "position": {"x": 250, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "service"},
                {"source": "service", "target": "quote", "label": "Needs quote"},
                {"source": "service", "target": "book", "label": "Wants estimate"},
                {"source": "service", "target": "faq", "label": "Has questions"},
                {"source": "quote", "target": "book"},
            ],
        },
    },
]


class FlowCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=500)
    flow_json: dict = Field(default_factory=lambda: {"nodes": [], "edges": []})


class FlowUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    flow_json: dict | None = None
    is_active: bool | None = None


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}")
async def list_flows(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all chat flows for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("chat_flows")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"flows": result.data or []}


@router.get("/{tenant_id}/templates")
async def list_templates(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List preset flow templates."""
    _verify_tenant(claims, tenant_id)
    return {"templates": PRESET_TEMPLATES}


@router.post("/{tenant_id}")
async def create_flow(
    tenant_id: str,
    req: FlowCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new chat flow."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": req.name.strip(),
        "flow_json": req.flow_json,
    }
    if req.description:
        data["description"] = req.description.strip()

    result = db.table("chat_flows").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create flow")
    return result.data[0]


@router.post("/{tenant_id}/from-template/{template_index}")
async def create_from_template(
    tenant_id: str,
    template_index: int,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a flow from a preset template."""
    _verify_tenant(claims, tenant_id)

    if template_index < 0 or template_index >= len(PRESET_TEMPLATES):
        raise HTTPException(status_code=400, detail="Invalid template index")

    template = PRESET_TEMPLATES[template_index]
    db = get_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": template["name"],
        "description": template["description"],
        "flow_json": template["flow_json"],
    }
    result = db.table("chat_flows").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create flow from template")
    return result.data[0]


@router.put("/{tenant_id}/{flow_id}")
async def update_flow(
    tenant_id: str,
    flow_id: str,
    req: FlowUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a chat flow."""
    _verify_tenant(claims, tenant_id)

    updates = {}
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.description is not None:
        updates["description"] = req.description.strip()
    if req.flow_json is not None:
        updates["flow_json"] = req.flow_json
    if req.is_active is not None:
        # Deactivate all other flows first if activating this one
        if req.is_active:
            db = get_supabase()
            db.table("chat_flows").update({"is_active": False}).eq("tenant_id", tenant_id).eq("is_active", True).execute()
        updates["is_active"] = req.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("chat_flows")
        .update(updates)
        .eq("id", flow_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Flow not found")
    return result.data[0]


@router.delete("/{tenant_id}/{flow_id}")
async def delete_flow(
    tenant_id: str,
    flow_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a chat flow."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    db.table("chat_flows").delete().eq("id", flow_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}
