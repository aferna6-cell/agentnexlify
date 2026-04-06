"""Google Calendar OAuth integration endpoints."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from jose import JWTError, jwt

from backend.config import settings
from backend.routers.auth import _get_current_tenant
from backend.services.google_calendar import (
    delete_integration,
    exchange_code,
    get_auth_url,
    get_integration,
    save_integration,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

_JWT_ALGORITHM = "HS256"

# Short-lived expiry for the OAuth state token (10 minutes).
_STATE_TOKEN_EXPIRY_MINUTES = 10


# ── Auth helpers ──────────────────────────────────────────────


def _encode_state(tenant_id: str) -> str:
    """Create a short-lived signed JWT encoding the tenant_id for OAuth state."""
    payload = {
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm=_JWT_ALGORITHM)


def _decode_state(state: str) -> str:
    """Validate the OAuth state token and return the tenant_id."""
    try:
        payload = jwt.decode(state, settings.api_secret_key, algorithms=[_JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Invalid state: missing tenant_id")
        return tenant_id
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter") from exc


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/google/auth")
async def google_auth(claims: dict = Depends(_get_current_tenant)):
    """Generate Google OAuth authorization URL."""
    tenant_id: str = claims["tenant_id"]
    state = _encode_state(tenant_id)
    redirect_uri = settings.google_redirect_uri
    auth_url = get_auth_url(redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="Signed state token encoding tenant_id"),
):
    """Handle Google OAuth callback.

    Google redirects here after the user authorizes access.  This endpoint
    is public (no JWT) because the browser arrives via a redirect from
    Google, not from the SPA.
    """
    tenant_id = _decode_state(state)
    redirect_uri = settings.google_redirect_uri

    try:
        creds = exchange_code(code, redirect_uri)
    except Exception as exc:
        logger.exception("Failed to exchange Google OAuth code for tenant %s", tenant_id)
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code") from exc

    # Fetch calendar email for display
    metadata = {}
    try:
        from googleapiclient.discovery import build as _build

        service = _build("calendar", "v3", credentials=creds)
        cal = service.calendars().get(calendarId="primary").execute()
        metadata["email"] = cal.get("id", "")
        metadata["calendar_name"] = cal.get("summary", "Primary")
    except Exception:
        logger.warning("Could not fetch calendar info for tenant %s", tenant_id, exc_info=True)

    try:
        save_integration(
            tenant_id=tenant_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=creds.expiry.isoformat() if creds.expiry else "",
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception("Failed to save Google Calendar integration for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to save integration") from exc

    # Redirect to frontend integrations page
    if settings.frontend_url:
        return RedirectResponse(url=f"{settings.frontend_url}/#integrations")

    return HTMLResponse(
        content=(
            "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
            "<h2>Connected!</h2><p>Google Calendar has been linked. You can close this window.</p>"
            "</body></html>"
        ),
    )


@router.get("/google/status")
async def google_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected Google Calendar integration."""
    tenant_id: str = claims["tenant_id"]
    integration = get_integration(tenant_id)

    if not integration:
        return {"connected": False, "email": None, "calendar_name": None}

    meta = integration.get("metadata") or {}
    return {
        "connected": True,
        "email": meta.get("email"),
        "calendar_name": meta.get("calendar_name"),
    }


@router.delete("/google")
async def google_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the Google Calendar integration for the tenant."""
    tenant_id: str = claims["tenant_id"]

    try:
        delete_integration(tenant_id)
    except Exception as exc:
        logger.exception("Failed to delete Google Calendar integration for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to disconnect integration") from exc

    return {"status": "disconnected"}
