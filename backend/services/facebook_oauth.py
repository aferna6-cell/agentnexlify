"""Facebook OAuth state encoding + Graph API client.

State tokens are short-lived signed JWTs (10-min TTL) carrying tenant_id +
random nonce. Graph API calls are wrapped here so retry/error handling stays
consistent and the router can stay thin.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

from backend.config import settings

logger = logging.getLogger(__name__)

# Facebook Graph API version used for all API calls
_FB_API_VERSION = "v19.0"
FB_GRAPH_BASE = f"https://graph.facebook.com/{_FB_API_VERSION}"

_JWT_ALGORITHM = "HS256"
STATE_TOKEN_EXPIRY_MINUTES = 10


def jwt_secret() -> str:
    """Resolve the JWT signing secret with api_secret_key fallback."""
    jwt_secret_val = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret_val, str) and jwt_secret_val:
        return jwt_secret_val
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def encode_state(tenant_id: str, nonce: str) -> str:
    """Create a short-lived signed JWT encoding the tenant_id for OAuth state."""
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "nonce": nonce,
        "provider": "facebook",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=STATE_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=_JWT_ALGORITHM)


def decode_state(state: str) -> tuple[str, str]:
    """Validate the OAuth state token and return (tenant_id, nonce)."""
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(state, jwt_secret(), algorithms=[_JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        nonce = payload.get("nonce")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Invalid state: missing tenant_id")
        if not nonce:
            raise HTTPException(status_code=400, detail="Invalid state: missing nonce")
        if payload.get("provider") != "facebook":
            raise HTTPException(status_code=400, detail="Invalid state provider")
        return tenant_id, nonce
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter") from exc


def build_auth_url(app_id: str, redirect_uri: str, state: str) -> str:
    """Build the Facebook Login OAuth URL with required Messenger scopes."""
    scopes = "pages_messaging,pages_manage_metadata"
    return (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={scopes}"
        f"&response_type=code"
    )


async def exchange_code_for_user_token(
    app_id: str,
    app_secret: str,
    redirect_uri: str,
    code: str,
) -> str:
    """Exchange the OAuth code for a short-lived user access token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{FB_GRAPH_BASE}/oauth/access_token",
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def fetch_managed_pages(user_access_token: str) -> list[dict]:
    """Fetch Pages the user manages, including each Page's access token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{FB_GRAPH_BASE}/me/accounts",
            params={
                "access_token": user_access_token,
                "fields": "id,name,access_token",
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", []) or []


async def subscribe_page(page_id: str, page_access_token: str) -> tuple[int, str]:
    """Subscribe a Page to message + postback webhook events.

    Returns (status_code, response_text_snippet). Non-200 is non-fatal at
    callsite; the access token is stored regardless.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{FB_GRAPH_BASE}/{page_id}/subscribed_apps",
            params={
                "access_token": page_access_token,
                "subscribed_fields": "messages,messaging_postbacks",
            },
        )
        return resp.status_code, resp.text[:500]


async def unsubscribe_page(page_id: str, page_access_token: str) -> tuple[int, str]:
    """Unsubscribe a Page from webhook events (best-effort on disconnect)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{FB_GRAPH_BASE}/{page_id}/subscribed_apps",
            params={"access_token": page_access_token},
        )
        return resp.status_code, resp.text[:500]
