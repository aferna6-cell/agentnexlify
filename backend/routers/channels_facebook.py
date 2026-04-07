"""Facebook Messenger channel integration — webhook verification, inbound messages,
OAuth flow to connect a Facebook Page, and dashboard management endpoints.

Public endpoints (no JWT):
  GET  /api/v1/channels/facebook/webhook  — Facebook webhook verification
  POST /api/v1/channels/facebook/webhook  — Inbound messages from Facebook
  GET  /api/v1/channels/facebook/callback — OAuth callback (browser redirect)

Authenticated endpoints (JWT required):
  GET    /api/v1/channels/facebook/{tenant_id}/auth-url    — Generate OAuth URL
  GET    /api/v1/channels/facebook/{tenant_id}/status      — Connection status
  DELETE /api/v1/channels/facebook/{tenant_id}/disconnect  — Remove integration

IMPORTANT: Static routes (/webhook, /callback) MUST be declared before parameterized
routes (/{tenant_id}/...) to avoid FastAPI routing conflicts.

Critical rules:
  - PEP 563 deferred annotations are incompatible with FastAPI
  - Webhook POST must return 200 within 5 seconds or Facebook retries
  - All except blocks must log errors before handling
  - HMAC-SHA256 signature validation on every inbound webhook POST
"""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.channel_manager import ingest_channel_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/channels/facebook", tags=["channels"])

# Facebook Graph API version used for all API calls
_FB_API_VERSION = "v19.0"
_FB_GRAPH_BASE = f"https://graph.facebook.com/{_FB_API_VERSION}"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FacebookStatusResponse(BaseModel):
    connected: bool
    page_name: str | None = None
    page_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_JWT_ALGORITHM = "HS256"
_STATE_TOKEN_EXPIRY_MINUTES = 10


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _encode_oauth_state(tenant_id: str, nonce: str) -> str:
    """Create a short-lived signed JWT encoding the tenant_id for OAuth state."""
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "nonce": nonce,
        "provider": "facebook",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> tuple[str, str]:
    """Validate the OAuth state token and return (tenant_id, nonce)."""
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
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


def _verify_fb_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Validate X-Hub-Signature-256 HMAC to confirm the request came from Facebook.

    Returns True when the signature matches, False otherwise.
    An absent or malformed header is treated as invalid.
    """
    app_secret = getattr(settings, "facebook_app_secret", "")
    if not app_secret:
        # Cannot validate without the secret — fail closed.
        logger.warning("facebook_app_secret not configured; rejecting inbound webhook")
        return False

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


async def _process_fb_webhook_event(payload: dict) -> None:
    """Parse messaging events and store via channel_manager.

    Facebook sends a list of 'entry' objects; each entry can contain multiple
    'messaging' events. We only handle 'message' events (not echoes, postbacks,
    read receipts) for now.

    Runs as a BackgroundTasks callback so the HTTP response returns 200
    immediately — Facebook will retry if it receives any non-200.
    """
    entries = payload.get("entry", [])
    for entry in entries:
        page_id: str = str(entry.get("id", ""))
        for event in entry.get("messaging", []):
            message_obj = event.get("message", {})

            # Skip echoes (messages sent by the page itself)
            if message_obj.get("is_echo"):
                continue

            sender_psid: str = str(event.get("sender", {}).get("id", ""))
            text: str = message_obj.get("text", "")
            timestamp_ms: int | None = event.get("timestamp")

            if not sender_psid or not text:
                # Non-text message (sticker, attachment, etc.) — skip for now
                continue

            try:
                result = ingest_channel_message(
                    provider="facebook",
                    page_id=page_id,
                    sender_id=sender_psid,
                    sender_name=None,  # Name requires a separate Graph API call
                    text=text,
                    timestamp_ms=timestamp_ms,
                )
            except Exception:
                logger.exception(
                    "channel_manager.ingest_channel_message failed for page=%s sender=%s",
                    page_id,
                    sender_psid,
                )
                continue

            if result:
                logger.info(
                    "Facebook message ingested: tenant=%s conversation=%s",
                    result.get("tenant_id"),
                    result.get("conversation_id"),
                )


# ---------------------------------------------------------------------------
# Static public endpoints — declared BEFORE parameterized routes
# ---------------------------------------------------------------------------


@router.get("/webhook", response_class=PlainTextResponse)
async def facebook_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Facebook webhook verification handshake.

    Facebook sends GET with hub.mode=subscribe, hub.verify_token (configured
    in the Facebook App dashboard), and hub.challenge. We must echo back
    hub.challenge as plain text when the verify token matches.
    """
    expected_token = getattr(settings, "facebook_verify_token", "")
    if not expected_token:
        logger.error("facebook_verify_token is not configured in settings")
        raise HTTPException(status_code=503, detail="Facebook integration not configured")

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Facebook webhook verification succeeded")
        return hub_challenge or ""

    logger.warning(
        "Facebook webhook verification failed: mode=%s token_match=%s",
        hub_mode,
        hub_verify_token == expected_token,
    )
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook", status_code=200)
async def facebook_webhook_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive inbound messages from Facebook Messenger.

    Facebook expects a 200 response within 5 seconds. We validate the
    HMAC-SHA256 signature, then hand off processing to a background task
    and return 200 immediately.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not _verify_fb_signature(raw_body, signature):
        logger.warning(
            "Facebook webhook: invalid or missing X-Hub-Signature-256 — rejecting request"
        )
        # Return 403 to signal rejection. Facebook treats non-200 as failure and
        # may retry or disable the webhook if persistent. This is intentional —
        # unsigned requests should never be processed.
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.exception("Facebook webhook: failed to parse JSON body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Return 200 immediately; process events in the background
    background_tasks.add_task(_process_fb_webhook_event, payload)
    return {"ok": True}


@router.get("/callback")
async def facebook_oauth_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
):
    """Handle Facebook OAuth callback.

    Steps:
      1. Exchange short-lived user access code for a user access token.
      2. Fetch the list of pages the user manages.
      3. Store the first page's long-lived page access token in the
         integrations table (provider='facebook').
      4. Subscribe the page to webhook events.
      5. Redirect to the frontend integrations page.

    The 'state' parameter carries the tenant_id (set in get_facebook_auth_url).
    """
    if error:
        logger.warning(
            "Facebook OAuth: user denied access — error=%s description=%s",
            error,
            error_description,
        )
        return RedirectResponse(url=f"{settings.frontend_url}/?facebook_error={error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    tenant_id, nonce = _decode_oauth_state(state)
    db = get_supabase()
    try:
        state_row = (
            db.table("oauth_states")
            .select("nonce")
            .eq("provider", "facebook")
            .eq("tenant_id", tenant_id)
            .eq("nonce", nonce)
            .is_("consumed_at", "null")
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .limit(1)
            .execute()
        )
        if not state_row.data:
            raise HTTPException(status_code=400, detail="Invalid or already used state parameter")
        db.table("oauth_states").update({
            "consumed_at": datetime.now(timezone.utc).isoformat()
        }).eq("provider", "facebook").eq("nonce", nonce).execute()
    except HTTPException:
        raise
    except Exception:
        logger.exception("Facebook OAuth: state validation failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to validate OAuth state")

    app_id = getattr(settings, "facebook_app_id", "")
    app_secret = getattr(settings, "facebook_app_secret", "")
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="Facebook integration not configured",
        )

    redirect_uri = f"{settings.api_url}/api/v1/channels/facebook/callback"

    # Step 1: Exchange code for a short-lived user access token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.get(
                f"{_FB_GRAPH_BASE}/oauth/access_token",
                params={
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            user_access_token: str = token_data["access_token"]
    except Exception:
        logger.exception(
            "Facebook OAuth: token exchange failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=502, detail="Failed to exchange authorization code")

    # Step 2: Fetch the pages the user manages to get page access tokens
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            pages_resp = await client.get(
                f"{_FB_GRAPH_BASE}/me/accounts",
                params={"access_token": user_access_token, "fields": "id,name,access_token"},
            )
            pages_resp.raise_for_status()
            pages_data = pages_resp.json()
    except Exception:
        logger.exception(
            "Facebook OAuth: failed to fetch pages for tenant %s", tenant_id
        )
        raise HTTPException(status_code=502, detail="Failed to fetch Facebook Pages")

    pages = pages_data.get("data", [])
    if not pages:
        logger.warning("Facebook OAuth: tenant %s has no managed pages", tenant_id)
        raise HTTPException(
            status_code=400,
            detail=(
                "No Facebook Pages found. "
                "Ensure you have admin access to at least one Facebook Page."
            ),
        )

    # Use the first page (future: let user pick from a list in the frontend)
    page = pages[0]
    page_id: str = page["id"]
    page_name: str = page.get("name", "")
    page_access_token: str = page["access_token"]

    # Step 3: Store in integrations table (upsert pattern from gbp.py)
    try:
        existing = (
            db.table("integrations")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("provider", "facebook")
            .limit(1)
            .execute()
        )
        integration_data = {
            "tenant_id": tenant_id,
            "provider": "facebook",
            "access_token": page_access_token,
            "refresh_token": None,  # Facebook page tokens are long-lived, no refresh token
            "metadata": {
                "page_id": page_id,
                "page_name": page_name,
                "all_pages": [
                    {"id": p["id"], "name": p.get("name", "")} for p in pages
                ],
            },
        }
        if existing.data:
            db.table("integrations").update(integration_data).eq("id", existing.data[0]["id"]).execute()
        else:
            db.table("integrations").insert(integration_data).execute()
    except Exception:
        logger.exception(
            "Facebook OAuth: failed to save integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to save Facebook integration")

    # Step 4: Subscribe the page to webhook events (best-effort — token is saved regardless)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            sub_resp = await client.post(
                f"{_FB_GRAPH_BASE}/{page_id}/subscribed_apps",
                params={
                    "access_token": page_access_token,
                    "subscribed_fields": "messages,messaging_postbacks",
                },
            )
            if sub_resp.status_code != 200:
                logger.warning(
                    "Facebook OAuth: page webhook subscription returned %s for tenant %s: %s",
                    sub_resp.status_code,
                    tenant_id,
                    sub_resp.text[:500],
                )
            else:
                logger.info(
                    "Facebook OAuth: page %s subscribed to webhooks for tenant %s",
                    page_id,
                    tenant_id,
                )
    except Exception:
        # Non-fatal: the token is saved; the operator can retry subscription
        logger.warning(
            "Facebook OAuth: webhook subscription failed for tenant %s page %s",
            tenant_id,
            page_id,
            exc_info=True,
        )

    # Step 5: Redirect to frontend integrations page
    return RedirectResponse(url=f"{settings.frontend_url}/?facebook_connected=true")


# ---------------------------------------------------------------------------
# Parameterized authenticated endpoints — declared AFTER static routes
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/auth-url")
async def get_facebook_auth_url(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Generate the Facebook Login OAuth URL for connecting a Facebook Page.

    Required permissions:
      - pages_messaging        — send/receive Messenger messages
      - pages_manage_metadata  — subscribe to page webhook events
    """
    verify_tenant(claims, tenant_id)

    app_id = getattr(settings, "facebook_app_id", "")
    if not app_id:
        raise HTTPException(
            status_code=503,
            detail="Facebook integration not configured — missing FACEBOOK_APP_ID",
        )

    redirect_uri = f"{settings.api_url}/api/v1/channels/facebook/callback"
    scopes = "pages_messaging,pages_manage_metadata"
    nonce = secrets.token_urlsafe(32)
    state = _encode_oauth_state(tenant_id, nonce)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRY_MINUTES)
    db = get_supabase()
    try:
        db.table("oauth_states").insert({
            "provider": "facebook",
            "tenant_id": tenant_id,
            "nonce": nonce,
            "expires_at": expires_at.isoformat(),
        }).execute()
    except Exception:
        logger.exception("Facebook OAuth: failed to persist state for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to initialize Facebook OAuth")

    auth_url = (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={scopes}"
        f"&response_type=code"
    )
    return {"auth_url": auth_url}


@router.get("/{tenant_id}/status", response_model=FacebookStatusResponse)
async def facebook_connection_status(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Check whether this tenant has a connected Facebook Page."""
    verify_tenant(claims, tenant_id)

    db = get_supabase()
    try:
        result = (
            db.table("integrations")
            .select("id, metadata")
            .eq("tenant_id", tenant_id)
            .eq("provider", "facebook")
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "Facebook status check failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return FacebookStatusResponse(connected=False)

    if not result.data:
        return FacebookStatusResponse(connected=False)

    meta = result.data[0].get("metadata") or {}
    return FacebookStatusResponse(
        connected=True,
        page_name=meta.get("page_name"),
        page_id=meta.get("page_id"),
    )


@router.delete("/{tenant_id}/disconnect")
async def facebook_disconnect(
    tenant_id: str,
    claims: dict = Depends(require_role("owner")),
):
    """Remove the Facebook integration and unsubscribe the page from webhooks."""
    verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch the current integration to get page_id and page_access_token
    try:
        result = (
            db.table("integrations")
            .select("id, access_token, metadata")
            .eq("tenant_id", tenant_id)
            .eq("provider", "facebook")
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "Facebook disconnect: failed to fetch integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to fetch integration")

    if not result.data:
        raise HTTPException(status_code=404, detail="No Facebook integration found")

    row = result.data[0]
    page_access_token: str = row.get("access_token") or ""
    meta = row.get("metadata") or {}
    page_id: str = meta.get("page_id", "")

    # Attempt to unsubscribe the page from webhook events (best-effort)
    if page_id and page_access_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                unsub_resp = await client.delete(
                    f"{_FB_GRAPH_BASE}/{page_id}/subscribed_apps",
                    params={"access_token": page_access_token},
                )
                if unsub_resp.status_code != 200:
                    logger.warning(
                        "Facebook disconnect: unsubscribe returned %s for tenant %s: %s",
                        unsub_resp.status_code,
                        tenant_id,
                        unsub_resp.text[:500],
                    )
                else:
                    logger.info(
                        "Facebook disconnect: page %s unsubscribed for tenant %s",
                        page_id,
                        tenant_id,
                    )
        except Exception:
            # Non-fatal: delete the DB row regardless of unsubscription failure
            logger.warning(
                "Facebook disconnect: webhook unsubscription failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

    # Delete the integration record
    try:
        db.table("integrations").delete().eq("id", row["id"]).execute()
    except Exception:
        logger.exception(
            "Facebook disconnect: failed to delete integration for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to remove integration")

    logger.info("Facebook integration removed for tenant %s", tenant_id)
    return {"success": True, "message": "Facebook integration disconnected"}
