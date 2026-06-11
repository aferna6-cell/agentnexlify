"""Instagram Business connect flow.

OAuth runs through Facebook Login (same Meta app as channels_facebook.py).
After user grants access we discover the Instagram Business Account linked
to the managed Facebook Page and store a provider='instagram' row in the
integrations table — the shape that social_instagram.py reads.

Public endpoints (no JWT):
  GET  /api/v1/channels/instagram/callback — OAuth callback (browser redirect)

Authenticated endpoints (JWT required):
  GET    /api/v1/channels/instagram/auth               — Start OAuth
  GET    /api/v1/channels/instagram/{tenant_id}/status — Connection status
  DELETE /api/v1/channels/instagram/{tenant_id}/disconnect

Static routes (/callback) declared BEFORE parameterized routes.

Critical rules:
  - No from __future__ import annotations in FastAPI router files
  - Never log token values — mask in all log messages
  - State is signed with the same facebook_oauth helpers as channels_facebook.py
  - provider='instagram' row shape must match what social_instagram.py reads:
      access_token = long-lived page token
      metadata = {ig_user_id, instagram_business_account_id, page_id, page_name}
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant, require_role, verify_tenant
from backend.models.database import get_service_supabase
from backend.services import facebook_oauth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/channels/instagram", tags=["channels"])

_INSTAGRAM_SCOPES = (
    "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
)
_PROVIDER = "instagram"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class InstagramStatusResponse(BaseModel):
    connected: bool
    instagram_username: str | None = None
    instagram_business_account_id: str | None = None
    page_name: str | None = None
    platform_configured: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _platform_configured() -> bool:
    return bool(
        getattr(settings, "facebook_app_id", "")
        and getattr(settings, "facebook_app_secret", "")
    )


def _require_platform() -> None:
    if not _platform_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "instagram_not_configured",
                "message": "Instagram connection isn't set up on this platform yet.",
            },
        )


# ---------------------------------------------------------------------------
# Static public endpoint — declared BEFORE parameterized routes
# ---------------------------------------------------------------------------


@router.get("/callback")
async def instagram_oauth_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
):
    """Handle Instagram/Facebook OAuth callback.

    Steps:
      1. Validate signed state + nonce from oauth_states table.
      2. Exchange code for short-lived user access token.
      3. Exchange for long-lived token (60 days).
      4. Fetch managed pages including instagram_business_account field.
      5. Upsert integrations row with provider='instagram'.
      6. Redirect to frontend with success/error params.
    """
    frontend_base = settings.frontend_url or "http://localhost:5173"

    if error:
        logger.warning(
            "Instagram OAuth: user denied — error=%s", error
        )
        return RedirectResponse(
            url=f"{frontend_base}/?instagram_error={error}#integrations"
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Validate state JWT
    try:
        tenant_id, nonce = facebook_oauth.decode_state(state)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Instagram OAuth: state decode failed", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Invalid or expired state parameter"
        ) from exc

    db = get_service_supabase()

    # Validate + consume nonce from oauth_states
    try:
        state_row = (
            db.table("oauth_states")
            .select("nonce")
            .eq("provider", _PROVIDER)
            .eq("tenant_id", tenant_id)
            .eq("nonce", nonce)
            .is_("consumed_at", "null")
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .limit(1)
            .execute()
        )
        if not state_row.data:
            raise HTTPException(
                status_code=400, detail="Invalid or already used state parameter"
            )
        db.table("oauth_states").update(
            {"consumed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("provider", _PROVIDER).eq("nonce", nonce).execute()
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Instagram OAuth: state validation failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to validate OAuth state")

    app_id = getattr(settings, "facebook_app_id", "")
    app_secret = getattr(settings, "facebook_app_secret", "")
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "instagram_not_configured",
                "message": "Instagram connection isn't set up on this platform yet.",
            },
        )

    redirect_uri = f"{settings.api_url}/api/v1/channels/instagram/callback"

    # Step 1: exchange code for short-lived user token
    try:
        user_access_token = await facebook_oauth.exchange_code_for_user_token(
            app_id, app_secret, redirect_uri, code
        )
    except Exception:
        logger.exception(
            "Instagram OAuth: token exchange failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=502, detail="Failed to exchange authorization code")

    # Step 2: exchange for long-lived user token (60-day)
    import httpx as _httpx

    try:
        async with _httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{facebook_oauth.FB_GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": user_access_token,
                },
            )
            resp.raise_for_status()
            long_lived_user_token = resp.json()["access_token"]
    except Exception:
        logger.exception(
            "Instagram OAuth: long-lived token exchange failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=502, detail="Failed to obtain long-lived token")

    # Step 3: fetch managed pages with instagram_business_account field
    try:
        async with _httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{facebook_oauth.FB_GRAPH_BASE}/me/accounts",
                params={
                    "access_token": long_lived_user_token,
                    "fields": "id,name,access_token,instagram_business_account",
                },
            )
            resp.raise_for_status()
            pages = resp.json().get("data", []) or []
    except Exception:
        logger.exception(
            "Instagram OAuth: failed to fetch pages for tenant %s", tenant_id
        )
        raise HTTPException(status_code=502, detail="Failed to fetch Facebook Pages")

    # Find the first page with an instagram_business_account
    ig_page = None
    for page in pages:
        if page.get("instagram_business_account"):
            ig_page = page
            break

    if not ig_page:
        logger.warning(
            "Instagram OAuth: no page with Instagram Business Account for tenant %s",
            tenant_id,
        )
        return RedirectResponse(
            url=(
                f"{frontend_base}/?instagram_error=no_instagram_business_account"
                "#integrations"
            )
        )

    page_id: str = ig_page["id"]
    page_name: str = ig_page.get("name", "")
    page_access_token: str = ig_page["access_token"]
    ig_account_id: str = ig_page["instagram_business_account"]["id"]

    # Step 4: fetch IG username for display
    ig_username: str = ""
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{facebook_oauth.FB_GRAPH_BASE}/{ig_account_id}",
                params={
                    "fields": "username",
                    "access_token": page_access_token,
                },
            )
            if resp.status_code == 200:
                ig_username = resp.json().get("username", "")
    except Exception:
        logger.warning(
            "Instagram OAuth: could not fetch IG username for tenant %s",
            tenant_id,
            exc_info=True,
        )

    # Step 5: upsert integrations row — shape social_instagram.py reads
    try:
        existing = (
            db.table("integrations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("provider", _PROVIDER)
            .limit(1)
            .execute()
        )
        integration_data = {
            "tenant_id": tenant_id,
            "provider": _PROVIDER,
            "access_token": page_access_token,
            "refresh_token": None,
            "metadata": {
                "ig_user_id": ig_account_id,
                "instagram_business_account_id": ig_account_id,
                "page_id": page_id,
                "page_name": page_name,
                "instagram_username": ig_username,
            },
        }
        if existing.data:
            db.table("integrations").update(integration_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            db.table("integrations").insert(integration_data).execute()
    except Exception:
        logger.exception(
            "Instagram OAuth: failed to save integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to save Instagram integration")

    logger.info(
        "Instagram OAuth: connected ig_account=%s page=%s tenant=%s",
        ig_account_id,
        page_id,
        tenant_id,
    )
    return RedirectResponse(
        url=f"{frontend_base}/?instagram_connected=true#integrations"
    )


# ---------------------------------------------------------------------------
# Parameterized authenticated endpoints — declared AFTER static route
# ---------------------------------------------------------------------------


@router.get("/auth")
async def instagram_auth(claims: dict = Depends(require_role("owner", "admin"))):
    """Start Meta OAuth flow for Instagram Business connect."""
    _require_platform()
    tenant_id: str = claims["tenant_id"]

    app_id = getattr(settings, "facebook_app_id", "")
    redirect_uri = f"{settings.api_url}/api/v1/channels/instagram/callback"

    nonce = secrets.token_urlsafe(32)
    # encode_state uses provider='facebook' in the JWT body; we store provider='instagram'
    # in oauth_states so callback can validate against the right table row.
    state = facebook_oauth.encode_state(tenant_id, nonce)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=facebook_oauth.STATE_TOKEN_EXPIRY_MINUTES
    )
    db = get_service_supabase()
    try:
        db.table("oauth_states").insert(
            {
                "provider": _PROVIDER,
                "tenant_id": tenant_id,
                "nonce": nonce,
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
    except Exception:
        logger.exception(
            "Instagram OAuth: failed to persist state for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to initialize Instagram OAuth")

    # Build auth URL with Instagram scopes
    auth_url = (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={_INSTAGRAM_SCOPES}"
        f"&response_type=code"
    )
    return {"auth_url": auth_url}


@router.get("/{tenant_id}/status", response_model=InstagramStatusResponse)
async def instagram_status(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Check whether this tenant has a connected Instagram Business account."""
    verify_tenant(claims, tenant_id)

    platform_ok = _platform_configured()
    db = get_service_supabase()
    try:
        result = (
            db.table("integrations")
            .select("id, metadata")
            .eq("tenant_id", tenant_id)
            .eq("provider", _PROVIDER)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "Instagram status check failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return InstagramStatusResponse(connected=False, platform_configured=platform_ok)

    if not result.data:
        return InstagramStatusResponse(connected=False, platform_configured=platform_ok)

    meta = result.data[0].get("metadata") or {}
    return InstagramStatusResponse(
        connected=True,
        instagram_username=meta.get("instagram_username"),
        instagram_business_account_id=meta.get("instagram_business_account_id"),
        page_name=meta.get("page_name"),
        platform_configured=platform_ok,
    )


@router.delete("/{tenant_id}/disconnect")
async def instagram_disconnect(
    tenant_id: str,
    claims: dict = Depends(require_role("owner")),
):
    """Remove the Instagram integration for this tenant."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("integrations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("provider", _PROVIDER)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "Instagram disconnect: failed to fetch integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to fetch integration")

    if not result.data:
        raise HTTPException(status_code=404, detail="No Instagram integration found")

    try:
        db.table("integrations").delete().eq(
            "id", result.data[0]["id"]
        ).execute()
    except Exception:
        logger.exception(
            "Instagram disconnect: failed to delete integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to remove integration")

    logger.info("Instagram integration removed for tenant %s", tenant_id)
    return {"success": True, "message": "Instagram integration disconnected"}
