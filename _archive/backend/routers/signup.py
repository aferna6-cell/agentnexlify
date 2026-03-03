"""Public signup endpoints — no auth required."""

from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, HTTPException, Header

from backend.models.database import get_supabase
from backend.models.schemas import SignupRequest, SignupResponse, WidgetConfigUpdate

router = APIRouter(prefix="/api/signup", tags=["signup"])


@router.post("", response_model=SignupResponse)
async def signup(req: SignupRequest):
    """Create a new client via public signup (free tier)."""
    db = get_supabase()
    widget_api_key = f"anx_{secrets.token_urlsafe(32)}"

    client_data = {
        "agent_name": req.business_name,
        "agent_type": req.industry,
        "brokerage_name": req.owner_name,
        "service_area": req.city,
        "notification_email": req.email,
        "widget_api_key": widget_api_key,
        "bot_name": "NexLiFy AI",
        "brand_color": "#00BFFF",
    }

    result = db.table("clients").insert(client_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create client")

    client = result.data[0]
    client_id = client["id"]

    embed_code = (
        f'<script src="https://cdn.agentnexlify.com/widget.js"\n'
        f'        data-key="{widget_api_key}"\n'
        f'        data-color="#00BFFF"\n'
        f'        data-name="NexLiFy AI"\n'
        f'        data-greeting="Hi there! How can I help you today?"\n'
        f'        data-position="bottom-right">\n'
        f"</script>"
    )

    return SignupResponse(
        client_id=client_id,
        widget_api_key=widget_api_key,
        embed_code=embed_code,
    )


@router.patch("/{client_id}/widget")
async def update_widget_config(
    client_id: str,
    req: WidgetConfigUpdate,
    x_widget_key: str = Header(...),
):
    """Update widget configuration for a client. Auth via X-Widget-Key header."""
    db = get_supabase()

    # Verify the widget key matches this client
    client_result = (
        db.table("clients")
        .select("id, widget_api_key, custom_instructions")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    client = client_result.data[0]
    if client["widget_api_key"] != x_widget_key:
        raise HTTPException(status_code=403, detail="Invalid widget key")

    # Build widget config, merging with any existing custom_instructions
    existing = {}
    if client.get("custom_instructions"):
        try:
            existing = json.loads(client["custom_instructions"])
        except (json.JSONDecodeError, TypeError):
            existing = {}

    widget_config = {**existing}
    update_data = req.model_dump(exclude_none=True)
    if update_data:
        widget_config.update(update_data)

    # Store as JSON in custom_instructions
    db.table("clients").update({
        "custom_instructions": json.dumps(widget_config),
        "bot_name": req.bot_name or client.get("bot_name", "NexLiFy AI"),
        "brand_color": req.brand_color or client.get("brand_color", "#00BFFF"),
    }).eq("id", client_id).execute()

    return {"status": "ok", "config": widget_config}
