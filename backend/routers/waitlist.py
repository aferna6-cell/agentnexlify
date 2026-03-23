"""Appointment waitlist — join when slots are full, get notified on cancellations."""

import logging
from datetime import date as date_type, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel, EmailStr

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.services.booking import generate_available_slots, get_business_hours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])

_JWT_ALGORITHM = "HS256"


# ── Pydantic models ────────────────────────────────────────────


class WaitlistJoinRequest(BaseModel):
    api_key: str
    customer_name: str
    customer_email: str | None = None
    customer_phone: str | None = None
    preferred_date: str  # YYYY-MM-DD
    preferred_time_start: str | None = None  # HH:MM
    preferred_time_end: str | None = None
    service_type_id: str | None = None
    notes: str | None = None


class WaitlistEntryResponse(BaseModel):
    id: str
    customer_name: str
    preferred_date: str
    status: str
    created_at: str


class WaitlistUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


# ── Auth helpers ────────────────────────────────────────────────


def _get_current_tenant(authorization: str = Header(...)) -> dict:
    """Extract tenant claims from Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    from jose import JWTError, jwt
    from backend.config import settings
    try:
        return jwt.decode(
            authorization.removeprefix("Bearer ").strip(),
            settings.api_secret_key,
            algorithms=[_JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _get_widget_config(api_key: str) -> dict:
    db = get_supabase()
    result = db.table("widget_configs").select("*").eq("api_key", api_key).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return result.data[0]


# ── Public endpoint: join waitlist (widget-facing) ──────────────


@router.post("/{tenant_id}/join")
@limiter.limit("10/minute")
async def join_waitlist(request: Request, tenant_id: str, req: WaitlistJoinRequest):
    """Add a visitor to the appointment waitlist. Public endpoint (API key auth)."""
    widget = _get_widget_config(req.api_key)
    if widget["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="API key mismatch")

    # Validate date
    try:
        preferred = date_type.fromisoformat(req.preferred_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if preferred < date_type.today():
        raise HTTPException(status_code=400, detail="Cannot join waitlist for a past date")

    db = get_supabase()

    # Check if there's already a waiting entry for this person + date
    if req.customer_email:
        existing = (
            db.table("waitlist_entries")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("customer_email", req.customer_email)
            .eq("preferred_date", req.preferred_date)
            .eq("status", "waiting")
            .limit(1)
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="Already on the waitlist for this date")

    # Try to link to existing lead
    lead_id = None
    if req.customer_email:
        lead_result = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("email", req.customer_email)
            .limit(1)
            .execute()
        )
        if lead_result.data:
            lead_id = lead_result.data[0]["id"]

    entry_data = {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "preferred_date": req.preferred_date,
        "preferred_time_start": req.preferred_time_start,
        "preferred_time_end": req.preferred_time_end,
        "service_type_id": req.service_type_id,
        "notes": req.notes,
        "status": "waiting",
    }
    # Remove None values
    entry_data = {k: v for k, v in entry_data.items() if v is not None}

    try:
        result = db.table("waitlist_entries").insert(entry_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to join waitlist")
        entry = result.data[0]
    except Exception as exc:
        logger.exception("Failed to add waitlist entry for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to join waitlist") from exc

    return {
        "id": entry["id"],
        "customer_name": entry["customer_name"],
        "preferred_date": entry["preferred_date"],
        "status": entry["status"],
        "message": "You've been added to the waitlist. We'll notify you if a slot opens up!",
    }


# ── Public endpoint: check waitlist status ──────────────────────


@router.get("/{tenant_id}/check")
@limiter.limit("30/minute")
async def check_waitlist_status(
    request: Request,
    tenant_id: str,
    api_key: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
):
    """Check if the waitlist is active for a given date (i.e., slots are full)."""
    widget = _get_widget_config(api_key)
    if widget["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="API key mismatch")

    try:
        target_date = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Check if any slots are available
    slots = generate_available_slots(tenant_id, target_date)
    slots_available = len(slots) > 0

    # Count current waitlist entries for this date
    db = get_supabase()
    waitlist_count_result = (
        db.table("waitlist_entries")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("preferred_date", date)
        .eq("status", "waiting")
        .limit(1)
        .execute()
    )
    waitlist_count = waitlist_count_result.count or 0

    return {
        "date": date,
        "slots_available": slots_available,
        "waitlist_active": not slots_available,
        "waitlist_count": waitlist_count,
    }


# ── Dashboard endpoints (JWT-protected) ─────────────────────────


@router.get("/{tenant_id}")
async def list_waitlist_entries(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    """List all waitlist entries for a tenant."""
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    query = (
        db.table("waitlist_entries")
        .select("*")
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
    return {"entries": result.data or [], "count": len(result.data or [])}


@router.get("/{tenant_id}/stats")
async def waitlist_stats(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get waitlist statistics."""
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Total waiting
    waiting = (
        db.table("waitlist_entries")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "waiting")
        .limit(1)
        .execute()
    )

    # Total notified (converted from waitlist)
    notified = (
        db.table("waitlist_entries")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "notified")
        .limit(1)
        .execute()
    )

    # Total booked from waitlist
    booked = (
        db.table("waitlist_entries")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "booked")
        .limit(1)
        .execute()
    )

    # Entries with upcoming dates
    today = date_type.today().isoformat()
    upcoming = (
        db.table("waitlist_entries")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "waiting")
        .gte("preferred_date", today)
        .limit(1)
        .execute()
    )

    return {
        "waiting": waiting.count or 0,
        "notified": notified.count or 0,
        "booked": booked.count or 0,
        "upcoming": upcoming.count or 0,
        "conversion_rate": round(
            (booked.count or 0) / max((booked.count or 0) + (notified.count or 0) + (waiting.count or 0), 1) * 100, 1
        ),
    }


@router.patch("/{tenant_id}/{entry_id}")
async def update_waitlist_entry(
    tenant_id: str,
    entry_id: str,
    req: WaitlistUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a waitlist entry (e.g., mark as notified, booked, cancelled)."""
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate status
    valid_statuses = {"waiting", "notified", "booked", "expired", "cancelled"}
    if "status" in data and data["status"] not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    if data.get("status") == "notified":
        data["notified_at"] = datetime.utcnow().isoformat()

    result = (
        db.table("waitlist_entries")
        .update(data)
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
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a waitlist entry."""
    _verify_tenant(claims, tenant_id)
    db = get_supabase()

    result = (
        db.table("waitlist_entries")
        .delete()
        .eq("id", entry_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    return {"status": "deleted", "id": entry_id}


# ── Notification helper (called from automation_engine) ──────────


def notify_waitlist_for_cancellation(tenant_id: str, cancelled_date: str, cancelled_start: str, cancelled_end: str):
    """
    When an appointment is cancelled, find matching waitlist entries and notify them.
    Called from the appointments cancel endpoint or automation engine.
    """
    db = get_supabase()

    try:
        # Find waiting entries for the same date
        entries = (
            db.table("waitlist_entries")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("preferred_date", cancelled_date)
            .eq("status", "waiting")
            .order("created_at", desc=False)  # First come, first served
            .limit(5)
            .execute()
        )

        if not entries.data:
            return 0

        notified_count = 0
        for entry in entries.data:
            # Check if the cancelled slot matches preferred time range
            if entry.get("preferred_time_start") and cancelled_start:
                try:
                    pref_start = entry["preferred_time_start"]
                    pref_end = entry.get("preferred_time_end") or "23:59"
                    cancel_time = cancelled_start.split("T")[1][:5] if "T" in cancelled_start else cancelled_start[:5]
                    if not (pref_start <= cancel_time <= pref_end):
                        continue
                except (ValueError, IndexError):
                    pass  # If time parsing fails, notify anyway

            # Mark as notified
            db.table("waitlist_entries").update({
                "status": "notified",
                "notified_at": datetime.utcnow().isoformat(),
            }).eq("id", entry["id"]).execute()

            # Send notifications
            _send_waitlist_notification(tenant_id, entry, cancelled_start, cancelled_end)
            notified_count += 1

        logger.info(
            "Notified %d waitlist entries for cancelled slot on %s, tenant %s",
            notified_count, cancelled_date, tenant_id,
        )
        return notified_count

    except Exception:
        logger.exception("Failed to process waitlist notifications for tenant %s", tenant_id)
        return 0


def _send_waitlist_notification(tenant_id: str, entry: dict, slot_start: str, slot_end: str):
    """Send email and/or SMS to a waitlisted customer about an available slot."""
    db = get_supabase()

    # Get tenant info for branding
    tenant = db.table("tenants").select("business_name, owner_email").eq("id", tenant_id).limit(1).execute()
    business_name = "the business"
    if tenant.data:
        business_name = tenant.data[0].get("business_name") or "the business"

    customer_name = entry.get("customer_name", "there")
    preferred_date = entry.get("preferred_date", "")

    # Format time for display
    slot_display = preferred_date
    if slot_start and "T" in slot_start:
        try:
            dt = datetime.fromisoformat(slot_start.replace("Z", "+00:00"))
            slot_display = dt.strftime("%B %d at %I:%M %p")
        except (ValueError, AttributeError):
            pass

    # Send email notification
    if entry.get("customer_email"):
        try:
            import resend
            from backend.config import settings
            if settings.resend_api_key:
                resend.api_key = settings.resend_api_key
                resend.Emails.send({
                    "from": f"{business_name} <noreply@agentnexlify.com>",
                    "to": [entry["customer_email"]],
                    "subject": f"Good news! A slot opened up at {business_name}",
                    "html": (
                        f"<p>Hi {customer_name},</p>"
                        f"<p>Great news! An appointment slot has opened up at <strong>{business_name}</strong> "
                        f"on <strong>{slot_display}</strong>.</p>"
                        f"<p>This slot is available on a first-come, first-served basis, so book soon!</p>"
                        f"<p>Best regards,<br>{business_name}</p>"
                    ),
                })
        except Exception:
            logger.warning("Failed to send waitlist email to %s", entry.get("customer_email"), exc_info=True)

    # Send SMS notification
    if entry.get("customer_phone"):
        try:
            from backend.config import settings
            if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_phone_number:
                from twilio.rest import Client as TwilioClient
                client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
                client.messages.create(
                    body=(
                        f"Hi {customer_name}! A slot opened up at {business_name} "
                        f"on {slot_display}. Book now before it's taken! "
                        f"Reply STOP to opt out."
                    ),
                    from_=settings.twilio_phone_number,
                    to=entry["customer_phone"],
                )
        except Exception:
            logger.warning("Failed to send waitlist SMS to %s", entry.get("customer_phone"), exc_info=True)

    # Log activity
    try:
        db.table("activity_log").insert({
            "tenant_id": tenant_id,
            "lead_id": entry.get("lead_id"),
            "activity_type": "waitlist_notified",
            "description": f"Notified {customer_name} about available slot on {slot_display}",
        }).execute()
    except Exception:
        logger.warning("Failed to log waitlist notification activity", exc_info=True)
