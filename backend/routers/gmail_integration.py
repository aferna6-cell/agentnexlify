"""Gmail OAuth integration endpoints — connect / callback / status / disconnect.

Mirrors the Google Calendar OAuth flow in ``backend/routers/integrations.py``
(same signed-JWT ``state`` pattern via ``_encode_state``/``_decode_state``,
same public callback route). Kept as its own router (not merged into
``integrations.py``) because Gmail is a distinct provider row + distinct
scopes + its own registered redirect URI.

Registered in ``backend/main.py`` alongside the inbox-monitor automation
tier (``run_inbox_poll`` on the 5-min tick).
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import JWTError, jwt

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.services import gmail_connector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations/gmail", tags=["integrations"])

_JWT_ALGORITHM = "HS256"
# Match Calendar OAuth: allow Google 2FA / test-user consent without state expiry.
_STATE_TOKEN_EXPIRY_MINUTES = 60


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _encode_state(tenant_id: str, os_thread_id: str | None = None) -> str:
    """Signed, short-lived OAuth state token encoding tenant_id + an optional
    os_thread_id so the post-connect redirect can deep-link back to the
    Agent OS thread that prompted the connect (e.g. a connector-awareness
    nudge)."""
    payload: dict = {
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES),
    }
    if os_thread_id:
        payload["os_thread_id"] = os_thread_id
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_state(state: str) -> tuple[str, str | None]:
    """Validate the OAuth state token; returns (tenant_id, os_thread_id)."""
    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Invalid state: missing tenant_id")
        return tenant_id, payload.get("os_thread_id")
    except JWTError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or expired state parameter"
        ) from exc


def _platform_configured() -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.gmail_redirect_uri
    )


@router.get("/connect")
async def gmail_connect(
    os_thread_id: str | None = Query(
        default=None,
        description="Optional Agent OS thread to deep-link back to after connect",
    ),
    claims: dict = Depends(_get_current_tenant),
):
    """Generate the Gmail OAuth authorization URL."""
    if not _platform_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "gmail_not_configured",
                "message": "Gmail connection isn't set up on this platform yet.",
            },
        )
    tenant_id: str = claims["tenant_id"]
    state = _encode_state(tenant_id, os_thread_id)
    auth_url = gmail_connector.get_auth_url(settings.gmail_redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="Signed state token encoding tenant_id"),
):
    """Handle the Gmail OAuth callback.

    Public route — the browser arrives here via a redirect from Google, not
    from the SPA, so tenant identity comes from the signed ``state`` token.
    """
    tenant_id, os_thread_id = _decode_state(state)
    redirect_uri = settings.gmail_redirect_uri

    try:
        creds = gmail_connector.exchange_code(code, redirect_uri)
    except Exception as exc:
        # Surface Google error class/message (no secrets) for staging diagnosis.
        logger.exception(
            "gmail: code exchange failed for tenant %s err_type=%s err=%s",
            tenant_id,
            type(exc).__name__,
            str(exc)[:300],
        )
        raise HTTPException(
            status_code=400, detail="Failed to exchange authorization code"
        ) from exc

    try:
        gmail_connector.save_integration(
            tenant_id=tenant_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=creds.expiry.isoformat() if creds.expiry else "",
        )
    except Exception as exc:
        logger.exception("gmail: failed to save integration for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to save integration") from exc

    # Seed the sync cursor + display email — best-effort, connect still
    # succeeds without it (inbox_monitor reseeds on first poll if missing).
    profile = {}
    try:
        profile = gmail_connector.get_profile(tenant_id)
    except Exception:
        logger.warning("gmail: profile fetch failed for tenant %s", tenant_id, exc_info=True)
    if profile:
        gmail_connector.update_metadata(
            tenant_id,
            {
                "email_address": profile.get("emailAddress", ""),
                "history_id": profile.get("historyId"),
                "last_poll_at": None,
                "watch_expiry": None,
            },
        )

    if settings.frontend_url:
        base = settings.frontend_url.rstrip("/")
        target = f"{base}/#agent-os/threads/{os_thread_id}" if os_thread_id else f"{base}/#integrations"
        return RedirectResponse(url=target)

    return HTMLResponse(
        content=(
            "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
            "<h2>Connected!</h2><p>Gmail has been linked. You can close this window.</p>"
            "</body></html>"
        ),
    )


@router.get("/status")
async def gmail_status(claims: dict = Depends(_get_current_tenant)):
    """Check whether the tenant has a connected Gmail integration."""
    tenant_id: str = claims["tenant_id"]
    integration = gmail_connector.get_integration(tenant_id)

    if not integration:
        return {
            "connected": False,
            "email": None,
            "platform_configured": _platform_configured(),
        }

    meta = integration.get("metadata") or {}
    return {
        "connected": True,
        "email": meta.get("email_address"),
        "history_id": meta.get("history_id"),
        "last_poll_at": meta.get("last_poll_at"),
        "platform_configured": _platform_configured(),
    }


@router.post("/disconnect")
async def gmail_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the Gmail integration for the tenant."""
    tenant_id: str = claims["tenant_id"]
    try:
        gmail_connector.delete_integration(tenant_id)
    except Exception as exc:
        logger.exception("gmail: disconnect failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to disconnect integration") from exc

    return {"status": "disconnected"}
