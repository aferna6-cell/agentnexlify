"""Appointment waitlist — join, notify, manage waitlisted customers."""

import logging
from datetime import date as date_type, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.email_sender import send_email
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])


# ── Models ──────────────────────────────────────────────────

class WaitlistJoinRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: str | None = None
    customer_phone: str | None = None
    preferred_date: str  # ISO date string YYYY-MM-DD
    preferred_time_start: str | None = None  # "09:00"
    preferred_time_end: str | None = None    # "12:00"
    service_type_id: str | None = None
    notes: str | None = None


class WaitlistUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    preferred_date: str | None = None
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None


class WaitlistNotifyRequest(BaseModel):
    message: str | None = None  # Custom message; defaults to a standard notification


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ── Public endpoint: join waitlist via widget ────────────────

@router.post("/public/{api_key}")
@limiter.limit("10/minute")
async def join_waitlist_public(
    request: Request,
    api_key: str,
    req: WaitlistJoinRequest,
):
    """Public endpoint: customer joins the waitlist via the chat widget or booking page."""
    db = get_service_supabase()

    # Resolve tenant from widget API key
    wc = db.table("widget_configs").select("tenant_id").eq("api_key", api_key).limit(1).execute()
    if not wc.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    tenant_id = wc.data[0]["tenant_id"]

    # Validate date
    try:
        date_type.fromisoformat(req.preferred_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    # Check if customer already waitlisted for same date
    existing = (
        db.table("waitlist_entries")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("preferred_date", req.preferred_date)
        .eq("status", "waiting")
    )
    if req.customer_email:
        existing = existing.eq("customer_email", req.customer_email)
    elif req.customer_phone:
        existing = existing.eq("customer_phone", req.customer_phone)
    else:
        existing = existing.eq("customer_name", req.customer_name)

    dup = existing.limit(1).execute()
    if dup.data:
        return {"message": "You are already on the waitlist for this date", "id": dup.data[0]["id"]}

    # Try to link to existing lead
    lead_id = None
    if req.customer_email:
        lead = db.table("leads").select("id").eq("client_id", tenant_id).eq("email", req.customer_email).limit(1).execute()
        if lead.data:
            lead_id = lead.data[0]["id"]
    elif req.customer_phone:
        lead = db.table("leads").select("id").eq("client_id", tenant_id).eq("phone", req.customer_phone).limit(1).execute()
        if lead.data:
            lead_id = lead.data[0]["id"]

    data = {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "customer_name": req.customer_name.strip(),
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "preferred_date": req.preferred_date,
        "preferred_time_start": req.preferred_time_start,
        "preferred_time_end": req.preferred_time_end,
        "service_type_id": req.service_type_id,
        "notes": req.notes,
        "status": "waiting",
    }
    result = db.table("waitlist_entries").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to join waitlist")

    return {"message": "Added to waitlist", "id": result.data[0]["id"]}


# ── Dashboard endpoints (JWT-protected) ──────────────────────

@router.get("/{tenant_id}")
async def list_waitlist(
    tenant_id: str,
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    claims: dict = Depends(_get_current_tenant),
):
    """List waitlist entries for a tenant, optionally filtered by status and date range."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    query = (
        db.table("waitlist_entries")
        .select("*, leads(name, email, phone)")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    if date_from:
        query = query.gte("preferred_date", date_from)
    if date_to:
        query = query.lte("preferred_date", date_to)

    result = query.limit(200).execute()
    return {"entries": result.data or [], "total": len(result.data or [])}


@router.get("/{tenant_id}/stats")
async def waitlist_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Waitlist summary stats."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    all_entries = (
        db.table("waitlist_entries")
        .select("status")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    entries = all_entries.data or []
    stats = {
        "total": len(entries),
        "waiting": sum(1 for e in entries if e["status"] == "waiting"),
        "notified": sum(1 for e in entries if e["status"] == "notified"),
        "booked": sum(1 for e in entries if e["status"] == "booked"),
        "expired": sum(1 for e in entries if e["status"] == "expired"),
        "cancelled": sum(1 for e in entries if e["status"] == "cancelled"),
    }
    return stats


@router.patch("/{tenant_id}/{entry_id}")
async def update_waitlist_entry(
    tenant_id: str,
    entry_id: str,
    req: WaitlistUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a waitlist entry (status, notes, dates)."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    update_data = {}
    if req.status is not None:
        valid = {"waiting", "notified", "booked", "expired", "cancelled"}
        if req.status not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")
        update_data["status"] = req.status
    if req.notes is not None:
        update_data["notes"] = req.notes
    if req.preferred_date is not None:
        update_data["preferred_date"] = req.preferred_date
    if req.preferred_time_start is not None:
        update_data["preferred_time_start"] = req.preferred_time_start
    if req.preferred_time_end is not None:
        update_data["preferred_time_end"] = req.preferred_time_end

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        db.table("waitlist_entries")
        .update(update_data)
        .eq("id", entry_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return result.data[0]


@router.delete("/{tenant_id}/{entry_id}")
async def delete_waitlist_entry(
    tenant_id: str,
    entry_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a waitlist entry."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    db.table("waitlist_entries").delete().eq("id", entry_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}


@router.post("/{tenant_id}/{entry_id}/notify")
async def notify_waitlisted_customer(
    tenant_id: str,
    entry_id: str,
    req: WaitlistNotifyRequest | None = None,
    claims: dict = Depends(_get_current_tenant),
):
    """Notify a waitlisted customer that a slot is available."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    entry = (
        db.table("waitlist_entries")
        .select("*")
        .eq("id", entry_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not entry.data:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    entry = entry.data[0]

    if entry["status"] not in ("waiting", "notified"):
        raise HTTPException(status_code=400, detail=f"Cannot notify entry with status '{entry['status']}'")

    # Get business info for notification
    tenant = db.table("tenants").select("business_name, owner_email").eq("id", tenant_id).limit(1).execute()
    business_name = tenant.data[0]["business_name"] if tenant.data else "Our business"

    message = (req.message if req and req.message else
               f"Great news! A slot has opened up at {business_name} on {entry['preferred_date']}. "
               f"Please contact us to book your appointment.")

    notified_via = []

    # Send email notification
    if entry.get("customer_email"):
        try:
            await send_email(
                to=entry["customer_email"],
                subject=f"Appointment Available - {business_name}",
                body_html=f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Good News, {entry['customer_name']}!</h2>
                    <p>{message}</p>
                    <p style="color: #6b7280; font-size: 14px;">
                        You were on our waitlist for {entry['preferred_date']}.
                        {f"Preferred time: {entry.get('preferred_time_start', '')} - {entry.get('preferred_time_end', '')}" if entry.get('preferred_time_start') else ""}
                    </p>
                    <p>Contact us to secure your spot!</p>
                    <p style="color: #9ca3af; font-size: 12px;">— {business_name}</p>
                </div>
                """,
                tenant_id=tenant_id,
            )
            notified_via.append("email")
        except Exception:
            logger.exception("Failed to send waitlist email notification to %s", entry["customer_email"])

    # Send SMS notification
    if entry.get("customer_phone"):
        try:
            await send_sms(
                to=entry["customer_phone"],
                body=message,
            )
            notified_via.append("sms")
        except Exception:
            logger.exception("Failed to send waitlist SMS notification to %s", entry["customer_phone"])

    if not notified_via:
        raise HTTPException(status_code=400, detail="No contact info available for notification")

    # Update entry status
    db.table("waitlist_entries").update({
        "status": "notified",
        "notified_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", entry_id).execute()

    return {"message": f"Customer notified via {', '.join(notified_via)}", "notified_via": notified_via}


@router.get("/{tenant_id}/check-date/{date}")
async def check_waitlist_for_date(
    tenant_id: str,
    date: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Check how many people are waiting for a specific date. Useful when cancellations happen."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()

    result = (
        db.table("waitlist_entries")
        .select("id, customer_name, customer_email, customer_phone, preferred_time_start, preferred_time_end, service_type_id, notes")
        .eq("tenant_id", tenant_id)
        .eq("preferred_date", date)
        .eq("status", "waiting")
        .order("created_at", desc=False)
        .execute()
    )
    return {"date": date, "waiting_count": len(result.data or []), "entries": result.data or []}
