"""Automation management — CRUD + Twilio signature verification.

Twilio missed-call and SMS-reply webhooks live in twilio_webhooks.py.
Do NOT re-add them here — it causes duplicate route registration.
"""

import base64
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant, require_role
from backend.services.activity import get_activity_events, get_activity_totals


class AutomationConfigUpdate(BaseModel):
    config: dict


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["automations"])


# ------------------------------------------------------------------
# Twilio Signature Validation
# ------------------------------------------------------------------

def _compute_twilio_signature(auth_token: str, url: str, params: dict[str, str]) -> str:
    """Compute the expected Twilio request signature.

    Algorithm (from Twilio docs):
    1. Take the full URL of the webhook endpoint.
    2. Sort the POST parameters alphabetically by key.
    3. Append each key-value pair to the URL (no separators).
    4. HMAC-SHA1 the result using the auth token as the key.
    5. Base64-encode the hash.
    """
    # Build the data string: URL + sorted key-value pairs concatenated
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]

    # HMAC-SHA1
    mac = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    )
    return base64.b64encode(mac.digest()).decode("utf-8")


async def verify_twilio_request(request: Request) -> None:
    """FastAPI dependency that validates the X-Twilio-Signature header.

    Raises HTTPException(403) if the signature is invalid. If Twilio is not
    configured (no auth token), validation is skipped to allow local
    development without Twilio credentials.
    """
    auth_token = settings.twilio_auth_token
    if not auth_token:
        logger.warning(
            "Twilio auth token not configured — skipping webhook signature "
            "validation (acceptable for local dev only)"
        )
        return

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        logger.warning(
            "Twilio webhook request missing X-Twilio-Signature header "
            "(path=%s, client=%s)",
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=403, detail="Missing Twilio signature")

    # Reconstruct the full URL that Twilio used to compute the signature.
    # Behind a reverse proxy (Railway/ngrok), the request URL may use http
    # while Twilio sent to https.  We use the X-Forwarded-Proto and Host
    # headers to rebuild the original URL Twilio signed against.
    forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get("Host", request.url.netloc)
    url = f"{forwarded_proto}://{host}{request.url.path}"

    # Parse the form body — Twilio sends application/x-www-form-urlencoded
    form_data = await request.form()
    params = {key: str(form_data[key]) for key in form_data}

    expected = _compute_twilio_signature(auth_token, url, params)

    if not hmac.compare_digest(expected, signature):
        logger.warning(
            "Twilio webhook signature mismatch (path=%s, client=%s, "
            "url_used=%s)",
            request.url.path,
            request.client.host if request.client else "unknown",
            url,
        )
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    logger.debug("Twilio webhook signature validated (path=%s)", request.url.path)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_automation(tenant_id: str, automation_type: str) -> dict | None:
    """Fetch a single automation by tenant + type."""
    db = get_service_supabase()
    result = (
        db.table("automations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("type", automation_type)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ------------------------------------------------------------------
# Activity Feed
# ------------------------------------------------------------------

@router.get("/automations/{tenant_id}/activity")
async def get_automation_activity(
    tenant_id: str,
    limit: int = Query(default=5, ge=1, le=100),
    type: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    claims: dict = Depends(_get_current_tenant),
):
    """Return recent automation activity events for a tenant.

    Query params:
        limit: max events returned (default 5, max 100)
        type: filter by activity_type (e.g. 'missed_call_textback')
        since: ISO8601 datetime — only return events after this time
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format. Use ISO8601.")

    events = get_activity_events(
        tenant_id=tenant_id,
        since=since_dt,
        type_filter=type,
        limit=limit,
    )
    totals = get_activity_totals(tenant_id=tenant_id, since=since_dt)

    return {"events": events, "totals": totals}


# ------------------------------------------------------------------
# Automation CRUD
# ------------------------------------------------------------------

@router.get("/automations/{tenant_id}")
async def list_automations(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """List all automations for a tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    db = get_service_supabase()
    result = (
        db.table("automations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return {"automations": result.data or []}


@router.post("/automations/{tenant_id}/{automation_id}/toggle")
async def toggle_automation(tenant_id: str, automation_id: str, claims: dict = Depends(require_role("owner", "admin"))):
    """Enable or disable an automation."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    db = get_service_supabase()
    result = (
        db.table("automations")
        .select("id, is_enabled")
        .eq("id", automation_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Automation not found")

    current = result.data[0]
    new_state = not current["is_enabled"]

    db.table("automations").update({
        "is_enabled": new_state,
    }).eq("id", automation_id).execute()

    return {"id": automation_id, "is_enabled": new_state}


@router.put("/automations/{tenant_id}/{automation_id}/config")
async def update_automation_config(tenant_id: str, automation_id: str, body: AutomationConfigUpdate, claims: dict = Depends(require_role("owner", "admin"))):
    """Update an automation's config JSON."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    db = get_service_supabase()

    # Verify ownership
    result = (
        db.table("automations")
        .select("id")
        .eq("id", automation_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Automation not found")

    db.table("automations").update({
        "config": body.config,
    }).eq("id", automation_id).execute()

    return {"id": automation_id, "config": body.config}
