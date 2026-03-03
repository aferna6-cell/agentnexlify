"""Client (real estate agent) management endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Header

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import CreateClientRequest

router = APIRouter(prefix="/api/clients", tags=["clients"])


def _verify_secret(x_api_secret: str = Header(...)):
    if x_api_secret != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API secret")


@router.post("")
async def create_client(req: CreateClientRequest, _=Depends(_verify_secret)):
    """Create a new client (real estate agent)."""
    db = get_supabase()
    widget_api_key = f"anx_{secrets.token_urlsafe(32)}"

    client_data = {
        "agent_name": req.agent_name,
        "agent_type": req.agent_type,
        "brokerage_name": req.brokerage_name,
        "service_area": req.service_area,
        "bot_name": req.bot_name,
        "calendly_link": req.calendly_link,
        "notification_email": req.notification_email,
        "notification_phone": req.notification_phone,
        "widget_api_key": widget_api_key,
        "custom_instructions": req.custom_instructions,
        "brand_color": req.brand_color,
    }

    result = db.table("clients").insert(client_data).execute()
    client = result.data[0]

    return {
        "client": client,
        "widget_api_key": widget_api_key,
        "embed_code": (
            f'<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" '
            f'data-api-key="{widget_api_key}"></script>'
        ),
    }


@router.get("")
async def list_clients(_=Depends(_verify_secret)):
    """List all clients."""
    db = get_supabase()
    result = db.table("clients").select("*").order("created_at", desc=True).execute()
    return {"clients": result.data or []}


@router.get("/{client_id}")
async def get_client(client_id: str, _=Depends(_verify_secret)):
    """Get a single client by ID."""
    db = get_supabase()
    result = db.table("clients").select("*").eq("id", client_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": result.data[0]}
