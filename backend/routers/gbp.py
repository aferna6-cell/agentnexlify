"""Google Business Profile integration — OAuth + profile data.

Enables tenants to connect their GBP account for:
- Pulling reviews directly (instead of manual entry)
- Posting updates from Content Studio
- Profile completeness scoring with real data

Requires Google Business Profile API credentials configured in settings.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

_JWT_ALGORITHM = "HS256"
_STATE_TOKEN_EXPIRY_MINUTES = 10


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _encode_oauth_state(tenant_id: str) -> str:
    """Create a short-lived signed JWT encoding the tenant_id for OAuth state."""
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> str:
    """Validate the OAuth state token and return the tenant_id."""
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Invalid state: missing tenant_id")
        return tenant_id
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter") from exc

router = APIRouter(prefix="/api/v1/gbp", tags=["google-business-profile"])


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- OAuth Flow ---


@router.get("/{tenant_id}/auth-url")
async def get_gbp_auth_url(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Get the Google Business Profile OAuth authorization URL."""
    _verify_tenant(claims, tenant_id)

    client_id = getattr(settings, "google_client_id", None)
    if not client_id:
        raise HTTPException(status_code=503, detail="Google Business Profile integration not configured")

    redirect_uri = f"{settings.api_url}/api/v1/gbp/callback"
    scopes = "https://www.googleapis.com/auth/business.manage"
    state = _encode_oauth_state(tenant_id)

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return {"auth_url": auth_url}


@router.get("/callback")
async def gbp_oauth_callback(code: str = Query(...), state: str = Query(...)):
    """Handle Google OAuth callback — exchange code for tokens."""
    tenant_id = _decode_oauth_state(state)

    client_id = getattr(settings, "google_client_id", None)
    client_secret = getattr(settings, "google_client_secret", None)
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google integration not configured")

    redirect_uri = f"{settings.api_url}/api/v1/gbp/callback"

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()
    except Exception:
        logger.exception("GBP OAuth token exchange failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="Failed to exchange authorization code")

    # Store tokens in integrations table
    db = get_service_supabase()
    try:
        existing = (
            db.table("integrations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("provider", "google_business_profile")
            .limit(1)
            .execute()
        )
        integration_data = {
            "tenant_id": tenant_id,
            "provider": "google_business_profile",
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "metadata": {"scope": tokens.get("scope"), "token_type": tokens.get("token_type")},
        }
        if existing.data:
            db.table("integrations").update(integration_data).eq("id", existing.data[0]["id"]).execute()
        else:
            db.table("integrations").insert(integration_data).execute()
    except Exception:
        logger.exception("Failed to save GBP tokens for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to save integration")

    return RedirectResponse(url=f"{settings.frontend_url}?gbp_connected=true")


# --- Connection Status ---


@router.get("/{tenant_id}/status")
async def gbp_connection_status(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Check if GBP is connected for this tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("integrations")
            .select("id, metadata")
            .eq("tenant_id", tenant_id)
            .eq("provider", "google_business_profile")
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("GBP status check failed for %s", tenant_id, exc_info=True)
        return {"connected": False}

    return {"connected": bool(result.data)}


@router.delete("/{tenant_id}/disconnect")
async def disconnect_gbp(
    tenant_id: str,
    claims: dict = Depends(require_role("owner")),
):
    """Disconnect Google Business Profile."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    db.table("integrations").delete().eq("tenant_id", tenant_id).eq("provider", "google_business_profile").execute()
    return {"success": True}


# --- Profile Data (requires connected GBP) ---


@router.get("/{tenant_id}/profile")
async def get_gbp_profile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Fetch the tenant's GBP profile data (requires connected account)."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    integration = (
        db.table("integrations")
        .select("access_token, refresh_token")
        .eq("tenant_id", tenant_id)
        .eq("provider", "google_business_profile")
        .limit(1)
        .execute()
    )
    if not integration.data:
        raise HTTPException(status_code=404, detail="GBP not connected. Connect via Settings > Integrations.")

    access_token = integration.data[0]["access_token"]

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://mybusinessbusinessinformation.googleapis.com/v1/accounts",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0,
            )
            if resp.status_code == 401:
                return {"error": "token_expired", "message": "Please reconnect your Google Business Profile"}
            resp.raise_for_status()
            return resp.json()
    except Exception:
        logger.exception("GBP profile fetch failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="Failed to fetch GBP profile")


@router.post("/{tenant_id}/post")
async def post_to_gbp(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Post an update to GBP (placeholder — requires location ID discovery first)."""
    _verify_tenant(claims, tenant_id)
    return {"status": "not_implemented", "message": "GBP posting requires location ID setup. Coming in a future update."}
