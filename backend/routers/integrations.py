"""Calendar OAuth integration endpoints — Google + Microsoft 365.

Both providers write to the same ``integrations`` table tagged with
``provider`` (``google_calendar`` / ``m365_calendar``). The booking action
handler at ``backend/services/os_actions/calendar.py`` dispatches at runtime
between the two based on which row is present.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from jose import JWTError, jwt

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.services import hubspot_tenant, m365_calendar
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
# 60m: Google test-user / 2FA consent often exceeds the old 10m window and
# surfaces as "Invalid or expired state parameter" on the staging callback.
_STATE_TOKEN_EXPIRY_MINUTES = 60


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


# ── Auth helpers ──────────────────────────────────────────────


def _encode_state(
    tenant_id: str,
    *,
    os_thread_id: str | None = None,
    return_to: str | None = None,
) -> str:
    """Create a short-lived signed JWT encoding the tenant_id for OAuth state.

    ``os_thread_id`` (optional) round-trips an Agent OS chat thread through
    the OAuth dance so the callback can redirect the owner back into the
    conversation that asked for the connection, instead of the generic
    integrations page. ``return_to`` (optional) is a relative dashboard
    path fallback used when there's no thread to return to.
    """
    payload = {
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES),
    }
    if os_thread_id:
        payload["os_thread_id"] = os_thread_id
    if return_to:
        payload["return_to"] = return_to
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_state(state: str) -> dict:
    """Validate the OAuth state token and return its claims.

    Always includes ``tenant_id``. ``os_thread_id`` / ``return_to`` are
    ``None`` when the auth URL was requested without them (the pre-deep-link
    behavior every existing caller still gets).
    """
    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=400, detail="Invalid state: missing tenant_id"
            )
        return {
            "tenant_id": tenant_id,
            "os_thread_id": payload.get("os_thread_id"),
            "return_to": payload.get("return_to"),
        }
    except JWTError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or expired state parameter"
        ) from exc


def _safe_return_to(return_to: str | None) -> str | None:
    """Only accept a relative dashboard path - never an absolute URL,
    which would turn ``return_to`` into an open redirect."""
    if return_to and return_to.startswith("/") and not return_to.startswith("//"):
        return return_to
    return None


def _oauth_success_response(
    *,
    provider_key: str,
    provider_label: str,
    os_thread_id: str | None,
    return_to: str | None,
    fallback_hash: str,
):
    """Redirect (or, with no frontend configured, a static HTML page) after
    a successful OAuth connect. When the request carried an
    ``os_thread_id`` the owner lands back in that Agent OS chat thread with
    ``?connected=<provider>`` so the UI can post a "connected, resuming"
    message; otherwise falls back to ``return_to`` or the provider's
    historical ``#integrations`` hash redirect.
    """
    if settings.frontend_url:
        if os_thread_id:
            url = (
                f"{settings.frontend_url}/dashboard/agent-os"
                f"?thread={os_thread_id}&connected={provider_key}"
            )
        else:
            safe_return_to = _safe_return_to(return_to)
            url = f"{settings.frontend_url}{safe_return_to or fallback_hash}"
        return RedirectResponse(url=url)

    return HTMLResponse(
        content=(
            "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
            f"<h2>Connected!</h2><p>{provider_label} has been linked. You can close this window.</p>"
            "</body></html>"
        ),
    )


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/google/auth")
async def google_auth(
    claims: dict = Depends(_get_current_tenant),
    os_thread_id: str | None = Query(
        None, description="Agent OS thread to return to after connect"
    ),
):
    """Generate Google OAuth authorization URL."""
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_calendar_not_configured",
                "message": "Google Calendar connection isn't set up on this platform yet.",
            },
        )
    tenant_id: str = claims["tenant_id"]
    state = _encode_state(tenant_id, os_thread_id=os_thread_id)
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
    state_claims = _decode_state(state)
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]
    redirect_uri = settings.google_redirect_uri

    try:
        creds = exchange_code(code, redirect_uri)
    except Exception as exc:
        logger.exception(
            "Failed to exchange Google OAuth code for tenant %s", tenant_id
        )
        raise HTTPException(
            status_code=400, detail="Failed to exchange authorization code"
        ) from exc

    # Fetch calendar email for display
    metadata = {}
    try:
        from googleapiclient.discovery import build as _build

        service = _build("calendar", "v3", credentials=creds)
        cal = service.calendars().get(calendarId="primary").execute()
        metadata["email"] = cal.get("id", "")
        metadata["calendar_name"] = cal.get("summary", "Primary")
    except Exception:
        logger.warning(
            "Could not fetch calendar info for tenant %s", tenant_id, exc_info=True
        )

    try:
        save_integration(
            tenant_id=tenant_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=creds.expiry.isoformat() if creds.expiry else "",
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception(
            "Failed to save Google Calendar integration for tenant %s", tenant_id
        )
        raise HTTPException(
            status_code=500, detail="Failed to save integration"
        ) from exc

    return _oauth_success_response(
        provider_key="google_calendar",
        provider_label="Google Calendar",
        os_thread_id=os_thread_id,
        return_to=return_to,
        fallback_hash="/#integrations",
    )


@router.get("/google/status")
async def google_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected Google Calendar integration."""
    tenant_id: str = claims["tenant_id"]
    platform_configured = bool(
        settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri
    )
    integration = get_integration(tenant_id)

    if not integration:
        return {
            "connected": False,
            "email": None,
            "calendar_name": None,
            "platform_configured": platform_configured,
        }

    meta = integration.get("metadata") or {}
    return {
        "connected": True,
        "email": meta.get("email"),
        "calendar_name": meta.get("calendar_name"),
        "platform_configured": platform_configured,
    }


@router.delete("/google")
async def google_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the Google Calendar integration for the tenant."""
    tenant_id: str = claims["tenant_id"]

    try:
        delete_integration(tenant_id)
    except Exception as exc:
        logger.exception(
            "Failed to delete Google Calendar integration for tenant %s", tenant_id
        )
        raise HTTPException(
            status_code=500, detail="Failed to disconnect integration"
        ) from exc

    return {"status": "disconnected"}


# ── Microsoft 365 / Outlook ──────────────────────────────────


def _fetch_m365_profile(access_token: str) -> dict:
    """Fetch user email + display name from Microsoft Graph for display metadata.

    Best-effort. Returns ``{}`` on failure rather than raising — connection
    still succeeds without it.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "email": data.get("mail") or data.get("userPrincipalName") or "",
                "calendar_name": data.get("displayName") or "Primary",
            }
    except Exception:
        logger.warning("m365: profile fetch failed", exc_info=True)
        return {}


@router.get("/m365/auth")
async def m365_auth(
    claims: dict = Depends(_get_current_tenant),
    os_thread_id: str | None = Query(
        None, description="Agent OS thread to return to after connect"
    ),
):
    """Generate Microsoft 365 OAuth authorization URL."""
    if not (settings.m365_client_id and settings.m365_client_secret and settings.m365_redirect_uri):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "m365_not_configured",
                "message": "Microsoft 365 connection isn't set up on this platform yet.",
            },
        )
    tenant_id: str = claims["tenant_id"]
    state = _encode_state(tenant_id, os_thread_id=os_thread_id)
    redirect_uri = settings.m365_redirect_uri
    auth_url = m365_calendar.build_authorization_url(redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/m365/callback")
async def m365_callback(
    code: str = Query(..., description="Authorization code from Microsoft"),
    state: str = Query(..., description="Signed state token encoding tenant_id"),
):
    """Handle Microsoft 365 OAuth callback.

    Public route — browser arrives via redirect from Azure AD, not from the SPA.
    Tenant identity is recovered from the signed ``state`` token, not from a
    session cookie or Authorization header.
    """
    state_claims = _decode_state(state)
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]
    redirect_uri = settings.m365_redirect_uri

    try:
        tokens = m365_calendar.exchange_code(code, redirect_uri)
    except Exception as exc:
        logger.exception("m365: code exchange failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=400, detail="Failed to exchange authorization code"
        ) from exc

    access_token = tokens.get("access_token") or ""
    refresh_token = tokens.get("refresh_token") or ""
    if not access_token or not refresh_token:
        # Without a refresh token we cannot keep the integration alive past
        # the access-token TTL (~1 hour) — refuse to persist a half-broken row.
        raise HTTPException(
            status_code=400,
            detail="Authorization missing tokens — re-consent with offline_access scope",
        )

    expires_in = int(tokens.get("expires_in") or 3600)
    token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    metadata = _fetch_m365_profile(access_token)

    try:
        m365_calendar.save_integration(
            tenant_id=tenant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception("m365: save integration failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=500, detail="Failed to save integration"
        ) from exc

    return _oauth_success_response(
        provider_key="m365_calendar",
        provider_label="Microsoft 365",
        os_thread_id=os_thread_id,
        return_to=return_to,
        fallback_hash="/#integrations",
    )


@router.get("/m365/status")
async def m365_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected Microsoft 365 integration."""
    tenant_id: str = claims["tenant_id"]
    platform_configured = bool(
        settings.m365_client_id and settings.m365_client_secret and settings.m365_redirect_uri
    )
    integration = m365_calendar.get_integration(tenant_id)

    if not integration:
        return {
            "connected": False,
            "email": None,
            "calendar_name": None,
            "platform_configured": platform_configured,
        }

    meta = integration.get("metadata") or {}
    return {
        "connected": True,
        "email": meta.get("email"),
        "calendar_name": meta.get("calendar_name"),
        "platform_configured": platform_configured,
    }


@router.delete("/m365")
async def m365_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the Microsoft 365 integration for the tenant."""
    tenant_id: str = claims["tenant_id"]

    try:
        m365_calendar.delete_integration(tenant_id)
    except Exception as exc:
        logger.exception("m365: disconnect failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=500, detail="Failed to disconnect integration"
        ) from exc

    return {"status": "disconnected"}


# ── HubSpot CRM ──────────────────────────────────────────────


@router.get("/hubspot/auth")
async def hubspot_auth(
    claims: dict = Depends(_get_current_tenant),
    os_thread_id: str | None = Query(
        None, description="Agent OS thread to return to after connect"
    ),
):
    """Generate HubSpot OAuth authorization URL."""
    tenant_id: str = claims["tenant_id"]
    if not (
        settings.hubspot_client_id
        and settings.hubspot_client_secret
        and settings.hubspot_redirect_uri
    ):
        raise HTTPException(
            status_code=503,
            detail="HubSpot OAuth not configured on this deployment",
        )
    state = _encode_state(tenant_id, os_thread_id=os_thread_id)
    redirect_uri = settings.hubspot_redirect_uri
    auth_url = hubspot_tenant.build_authorization_url(redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/hubspot/callback")
async def hubspot_callback(
    code: str = Query(..., description="Authorization code from HubSpot"),
    state: str = Query(..., description="Signed state token encoding tenant_id"),
):
    """Handle HubSpot OAuth callback.

    Public route — browser arrives via redirect from HubSpot, not from the SPA.
    Tenant identity is recovered from the signed ``state`` token.
    """
    state_claims = _decode_state(state)
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]
    redirect_uri = settings.hubspot_redirect_uri

    try:
        tokens = hubspot_tenant.exchange_code(code, redirect_uri)
    except Exception as exc:
        logger.exception("hubspot: code exchange failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=400, detail="Failed to exchange authorization code"
        ) from exc

    access_token = tokens.get("access_token") or ""
    refresh_token = tokens.get("refresh_token") or ""
    if not access_token or not refresh_token:
        # HubSpot OAuth always returns both — missing refresh_token means we
        # cannot keep the integration alive past the ~30 min access TTL.
        raise HTTPException(
            status_code=400,
            detail="Authorization missing tokens — retry the connect flow",
        )

    expires_in = int(tokens.get("expires_in") or 1800)
    token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    metadata = hubspot_tenant.fetch_profile(access_token)

    try:
        hubspot_tenant.save_integration(
            tenant_id=tenant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception("hubspot: save integration failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=500, detail="Failed to save integration"
        ) from exc

    return _oauth_success_response(
        provider_key="hubspot",
        provider_label="HubSpot",
        os_thread_id=os_thread_id,
        return_to=return_to,
        fallback_hash="/?hubspot=connected#integrations",
    )


@router.get("/hubspot/status")
async def hubspot_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected HubSpot integration."""
    tenant_id: str = claims["tenant_id"]
    platform_configured = bool(
        settings.hubspot_client_id and settings.hubspot_client_secret and settings.hubspot_redirect_uri
    )
    integration = hubspot_tenant.get_integration(tenant_id)

    if not integration:
        return {
            "connected": False,
            "portal_id": None,
            "hub_domain": None,
            "user": None,
            "platform_configured": platform_configured,
        }

    meta = integration.get("metadata") or {}
    return {
        "connected": True,
        "portal_id": meta.get("portal_id"),
        "hub_domain": meta.get("hub_domain"),
        "user": meta.get("user"),
        "platform_configured": platform_configured,
    }


@router.delete("/hubspot")
async def hubspot_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the HubSpot integration for the tenant."""
    tenant_id: str = claims["tenant_id"]

    try:
        hubspot_tenant.delete_integration(tenant_id)
    except Exception as exc:
        logger.exception("hubspot: disconnect failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=500, detail="Failed to disconnect integration"
        ) from exc

    return {"status": "disconnected"}
