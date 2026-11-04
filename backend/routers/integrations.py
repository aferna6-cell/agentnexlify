"""Calendar OAuth integration endpoints — Google + Microsoft 365.

Both providers write to the same ``integrations`` table tagged with
``provider`` (``google_calendar`` / ``m365_calendar``). The booking action
handler at ``backend/services/os_actions/calendar.py`` dispatches at runtime
between the two based on which row is present.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from jose import JWTError, jwt

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.services import hubspot_tenant, m365_calendar
from backend.services.google_calendar import (
    build_redirect_uri,
    delete_integration,
    exchange_code,
    get_auth_url,
    get_integration,
    save_integration,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

_JWT_ALGORITHM = "HS256"

# OAuth state TTL. Must cover 2FA + Google "unverified app" delays; the
# authorization code is issued only after consent, so a short state TTL
# (10m) caused repeated staging 400s: "Invalid or expired state parameter".
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
        # jose raises ExpiredSignatureError (a JWTError) when exp has passed.
        detail = (
            "OAuth state expired — click Connect again and finish Google consent "
            f"within {_STATE_TOKEN_EXPIRY_MINUTES} minutes"
            if type(exc).__name__ == "ExpiredSignatureError"
            or "expired" in str(exc).lower()
            else "Invalid or expired state parameter"
        )
        raise HTTPException(status_code=400, detail=detail) from exc


_THREAD_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_ALLOWED_RETURN_PREFIXES = ("/dashboard/", "/settings/")


def _safe_return_to(return_to: str | None) -> str | None:
    """Relative dashboard path only. Absolute and protocol-relative values
    would turn ``return_to`` into an open redirect."""
    if not return_to or not return_to.startswith("/") or return_to.startswith(("//", "/\\")):
        return None
    if any(token in return_to for token in ("\\", "://", "@")):
        return None
    lowered = return_to.lower()
    if lowered.startswith("/%2f") or "%5c" in lowered or "%00" in lowered:
        return None
    path = return_to.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith(_ALLOWED_RETURN_PREFIXES):
        return None
    return return_to


def _safe_thread_id(os_thread_id: str | None) -> str | None:
    if os_thread_id and _THREAD_ID.fullmatch(os_thread_id):
        return os_thread_id
    return None


# Query keys the integrations page already reads for its result toast.
_OAUTH_STATUS_PARAMS = {
    "google_calendar": "google",
    "m365_calendar": "m365",
    "hubspot": "hubspot",
}


def _frontend_origin() -> str | None:
    """Scheme + host of ``FRONTEND_URL``. Userinfo, paths, and other schemes
    are rejected so a callback cannot be aimed at an arbitrary host."""
    raw = (settings.frontend_url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not host:
        return None
    if parsed.username or parsed.password:
        return None
    if any(char in host for char in "\\ \t\r\n"):
        return None
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port}"


def _frontend_redirect(path: str) -> str | None:
    """Build a redirect on the frontend origin, or None if the result would
    leave that host."""
    origin = _frontend_origin()
    if origin is None:
        return None
    if not path.startswith("/") or path.startswith(("//", "/\\")):
        return None
    url = f"{origin}{path}"
    target = urlparse(url)
    allowed = urlparse(origin)
    if target.scheme != allowed.scheme or target.hostname != allowed.hostname:
        return None
    if target.port != allowed.port:
        return None
    return url


def _dashboard_integrations_path(provider_key: str, outcome: str) -> str:
    """Dashboard path after an OAuth callback.

    ``/#integrations`` is the marketing home page (``/`` plus a hash). The
    integrations screen is ``/dashboard/integrations``, which reads
    ``google|m365|hubspot=connected|error``.
    """
    param = _OAUTH_STATUS_PARAMS[provider_key]
    return f"/dashboard/integrations?{param}={outcome}"


def _post_callback_path(
    provider_key: str,
    *,
    outcome: str,
    os_thread_id: str | None = None,
    return_to: str | None = None,
) -> str:
    if outcome == "connected":
        thread_id = _safe_thread_id(os_thread_id)
        if thread_id:
            query = urlencode({"thread": thread_id, "connected": provider_key})
            return f"/dashboard/agent-os?{query}"
        safe_return_to = _safe_return_to(return_to)
        if safe_return_to:
            return safe_return_to
    return _dashboard_integrations_path(provider_key, outcome)


def _oauth_error_response(
    provider_key: str,
    *,
    status_code: int,
    detail: str,
):
    """Send the browser to Integrations with an error indicator.

    With no allowlisted frontend origin, keep the JSON error for non-browser callers.
    """
    url = _frontend_redirect(
        _post_callback_path(provider_key, outcome="error")
    )
    if url:
        return RedirectResponse(url=url)
    raise HTTPException(status_code=status_code, detail=detail)


def _oauth_success_response(
    *,
    provider_key: str,
    provider_label: str,
    os_thread_id: str | None,
    return_to: str | None,
):
    """Redirect (or, with no frontend configured, a static HTML page) after
    a successful OAuth connect. When the request carried an
    ``os_thread_id`` the owner lands back in that Agent OS chat thread with
    ``?connected=<provider>`` so the UI can post a "connected, resuming"
    message; otherwise falls back to ``return_to`` or the integrations page
    with a connected indicator. The host is always the frontend origin.
    """
    url = _frontend_redirect(
        _post_callback_path(
            provider_key,
            outcome="connected",
            os_thread_id=os_thread_id,
            return_to=return_to,
        )
    )
    if url:
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
    redirect_uri = build_redirect_uri()
    if not (settings.google_client_id and settings.google_client_secret and redirect_uri):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "google_calendar_not_configured",
                "message": "Google Calendar connection isn't set up on this platform yet.",
            },
        )
    tenant_id: str = claims["tenant_id"]
    state = _encode_state(tenant_id, os_thread_id=os_thread_id)
    auth_url = get_auth_url(redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str = Query(..., description="Signed state token encoding tenant_id"),
    error: str | None = None,
):
    """Handle Google OAuth callback.

    Google redirects here after the user authorizes access.  This endpoint
    is public (no JWT) because the browser arrives via a redirect from
    Google, not from the SPA.
    """
    try:
        state_claims = _decode_state(state)
    except HTTPException as exc:
        return _oauth_error_response(
            "google_calendar",
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]

    if error or not code:
        return _oauth_error_response(
            "google_calendar",
            status_code=400,
            detail="Google authorization was not completed",
        )

    redirect_uri = build_redirect_uri()

    try:
        creds = exchange_code(code, redirect_uri)
    except Exception:
        logger.exception(
            "Failed to exchange Google OAuth code for tenant %s", tenant_id
        )
        return _oauth_error_response(
            "google_calendar",
            status_code=400,
            detail="Failed to exchange authorization code",
        )

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
    except Exception:
        logger.exception(
            "Failed to save Google Calendar integration for tenant %s", tenant_id
        )
        return _oauth_error_response(
            "google_calendar",
            status_code=500,
            detail="Failed to save integration",
        )

    return _oauth_success_response(
        provider_key="google_calendar",
        provider_label="Google Calendar",
        os_thread_id=os_thread_id,
        return_to=return_to,
    )


@router.get("/google/status")
async def google_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected Google Calendar integration."""
    tenant_id: str = claims["tenant_id"]
    platform_configured = bool(
        settings.google_client_id and settings.google_client_secret and build_redirect_uri()
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
    """Remove the Google Calendar integration for the tenant.

    Pending calendar approval cards are rejected first, so a disconnect
    cannot be followed by events.insert for a card that was still waiting.
    """
    tenant_id: str = claims["tenant_id"]

    try:
        from backend.models.database import get_service_supabase
        from backend.services.m8_action_flags import calendar_chat_enabled
        from backend.services.os_calendar_chat import cancel_pending_calendar_approvals

        if calendar_chat_enabled(tenant_id):
            cancel_pending_calendar_approvals(get_service_supabase(), tenant_id)
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
    code: str | None = None,
    state: str = Query(..., description="Signed state token encoding tenant_id"),
    error: str | None = None,
):
    """Handle Microsoft 365 OAuth callback.

    Public route — browser arrives via redirect from Azure AD, not from the SPA.
    Tenant identity is recovered from the signed ``state`` token, not from a
    session cookie or Authorization header.
    """
    try:
        state_claims = _decode_state(state)
    except HTTPException as exc:
        return _oauth_error_response(
            "m365_calendar",
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]

    if error or not code:
        return _oauth_error_response(
            "m365_calendar",
            status_code=400,
            detail="Microsoft authorization was not completed",
        )

    redirect_uri = settings.m365_redirect_uri

    try:
        tokens = m365_calendar.exchange_code(code, redirect_uri)
    except Exception:
        logger.exception("m365: code exchange failed for tenant %s", tenant_id)
        return _oauth_error_response(
            "m365_calendar",
            status_code=400,
            detail="Failed to exchange authorization code",
        )

    access_token = tokens.get("access_token") or ""
    refresh_token = tokens.get("refresh_token") or ""
    if not access_token or not refresh_token:
        # Without a refresh token we cannot keep the integration alive past
        # the access-token TTL (~1 hour) — refuse to persist a half-broken row.
        return _oauth_error_response(
            "m365_calendar",
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
    except Exception:
        logger.exception("m365: save integration failed for tenant %s", tenant_id)
        return _oauth_error_response(
            "m365_calendar",
            status_code=500,
            detail="Failed to save integration",
        )

    return _oauth_success_response(
        provider_key="m365_calendar",
        provider_label="Microsoft 365",
        os_thread_id=os_thread_id,
        return_to=return_to,
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
    code: str | None = None,
    state: str = Query(..., description="Signed state token encoding tenant_id"),
    error: str | None = None,
):
    """Handle HubSpot OAuth callback.

    Public route — browser arrives via redirect from HubSpot, not from the SPA.
    Tenant identity is recovered from the signed ``state`` token.
    """
    try:
        state_claims = _decode_state(state)
    except HTTPException as exc:
        return _oauth_error_response(
            "hubspot",
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
    tenant_id = state_claims["tenant_id"]
    os_thread_id = state_claims["os_thread_id"]
    return_to = state_claims["return_to"]

    if error or not code:
        return _oauth_error_response(
            "hubspot",
            status_code=400,
            detail="HubSpot authorization was not completed",
        )

    redirect_uri = settings.hubspot_redirect_uri

    try:
        tokens = hubspot_tenant.exchange_code(code, redirect_uri)
    except Exception:
        logger.exception("hubspot: code exchange failed for tenant %s", tenant_id)
        return _oauth_error_response(
            "hubspot",
            status_code=400,
            detail="Failed to exchange authorization code",
        )

    access_token = tokens.get("access_token") or ""
    refresh_token = tokens.get("refresh_token") or ""
    if not access_token or not refresh_token:
        # HubSpot OAuth always returns both — missing refresh_token means we
        # cannot keep the integration alive past the ~30 min access TTL.
        return _oauth_error_response(
            "hubspot",
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
    except Exception:
        logger.exception("hubspot: save integration failed for tenant %s", tenant_id)
        return _oauth_error_response(
            "hubspot",
            status_code=500,
            detail="Failed to save integration",
        )

    return _oauth_success_response(
        provider_key="hubspot",
        provider_label="HubSpot",
        os_thread_id=os_thread_id,
        return_to=return_to,
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
