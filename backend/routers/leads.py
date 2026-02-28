"""Lead management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header

from backend.config import settings
from backend.models.database import get_supabase

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _verify_secret(x_api_secret: str = Header(...)):
    """Verify the internal API secret for protected endpoints."""
    if x_api_secret != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API secret")


@router.get("/{client_id}")
async def get_leads(client_id: str, _=Depends(_verify_secret)):
    """Get all leads for a client, ordered by score descending."""
    db = get_supabase()
    result = (
        db.table("leads")
        .select("*")
        .eq("client_id", client_id)
        .order("lead_score", desc=True)
        .execute()
    )
    return {"leads": result.data or []}


@router.get("/{client_id}/hot")
async def get_hot_leads(client_id: str, _=Depends(_verify_secret)):
    """Get only hot leads for a client."""
    db = get_supabase()
    result = (
        db.table("leads")
        .select("*")
        .eq("client_id", client_id)
        .eq("lead_temperature", "hot")
        .order("created_at", desc=True)
        .execute()
    )
    return {"leads": result.data or []}


@router.get("/{client_id}/summary")
async def get_lead_summary(client_id: str, _=Depends(_verify_secret)):
    """Get a summary of lead counts by temperature."""
    db = get_supabase()
    all_leads = (
        db.table("leads")
        .select("lead_temperature, status")
        .eq("client_id", client_id)
        .execute()
    )
    leads = all_leads.data or []
    return {
        "total": len(leads),
        "hot": sum(1 for l in leads if l.get("lead_temperature") == "hot"),
        "warm": sum(1 for l in leads if l.get("lead_temperature") == "warm"),
        "cold": sum(1 for l in leads if l.get("lead_temperature") == "cold"),
        "appointment_booked": sum(1 for l in leads if l.get("status") == "appointment_booked"),
    }
