"""Per-tenant HubSpot CRM integration.

Sibling to ``backend.services.m365_calendar`` and ``twilio_tenant``:
each tenant connects their own HubSpot account via OAuth and Group B
``crm.contact_upsert`` actions push contacts to that account in addition
to the internal ``leads`` row.

OAuth tokens are stored in the same ``integrations`` table tagged
``provider='hubspot'``. Refresh tokens are rotated on every refresh
(HubSpot policy) — the new refresh token returned by the token endpoint
must be persisted, not the original one. Calling code that relies on
this should always read back the row, not cache the refresh token in
memory across requests.

Storage layout:

* ``provider``     = ``'hubspot'``
* ``access_token`` = HubSpot access token (bearer, ~30 min TTL)
* ``refresh_token``= HubSpot refresh token (rotated on each refresh)
* ``token_expiry`` = ISO timestamp of access_token expiry
* ``metadata``     = ``{"portal_id": int, "hub_domain": str, "user": str}``

Mirrors the dispatch shape of ``m365_mail.send_email_via_graph`` +
``twilio_tenant.send_sms_via_tenant``: ``upsert_contact`` returns
``{"success": bool, "detail": str, "contact_id": str}`` so the
``crm.contact_upsert`` action handler can branch on a single call.
Never raises — HTTP failures, missing credentials, and unexpected
exceptions all fold into ``{"success": False, "detail": ...}`` so the
worker records a clean ``failed`` row instead of crashing.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

SCOPES = [
    "crm.objects.contacts.read",
    "crm.objects.contacts.write",
    "oauth",
]

_AUTHORIZE_URL = "https://app.hubspot.com/oauth/authorize"
_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
_API_BASE = "https://api.hubapi.com"
_PROVIDER = "hubspot"


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


def get_integration(tenant_id: str) -> dict | None:
    """Fetch the hubspot integration row for a tenant."""
    db = get_service_supabase()
    result = (
        db.table("integrations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("provider", _PROVIDER)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return row if isinstance(row, dict) else None


def save_integration(
    tenant_id: str,
    access_token: str,
    refresh_token: str,
    token_expiry: str,
    metadata: dict | None = None,
) -> dict:
    """Upsert the hubspot integration for a tenant."""
    db = get_service_supabase()
    payload: dict = {
        "tenant_id": tenant_id,
        "provider": _PROVIDER,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
    }
    if metadata is not None:
        payload["metadata"] = metadata

    existing = get_integration(tenant_id)
    if existing:
        result = (
            db.table("integrations").update(payload).eq("id", existing["id"]).execute()
        )
    else:
        result = db.table("integrations").insert(payload).execute()

    return result.data[0] if result.data else payload


def delete_integration(tenant_id: str) -> None:
    """Remove the hubspot integration for a tenant."""
    db = get_service_supabase()
    db.table("integrations").delete().eq("tenant_id", tenant_id).eq(
        "provider", _PROVIDER
    ).execute()


def is_connected(tenant_id: str) -> bool:
    """Return True if the tenant has a usable hubspot integration row.

    A row with no access_token or refresh_token is unusable — treat as not
    connected so callers can fall back cleanly instead of attempting a 401.
    """
    try:
        row = get_integration(tenant_id)
    except Exception:
        logger.warning(
            "hubspot_tenant: integration lookup failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return False
    if not row:
        return False
    return bool(row.get("access_token") and row.get("refresh_token"))


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------


def build_authorization_url(redirect_uri: str, state: str) -> str:
    """Return the HubSpot authorization URL for the OAuth code-grant flow."""
    params = {
        "client_id": settings.hubspot_client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for tokens.

    Returns the raw token response dict. Caller extracts ``access_token``,
    ``refresh_token``, ``expires_in`` and persists via ``save_integration``.
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.hubspot_client_id,
        "client_secret": settings.hubspot_client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def _refresh(refresh_token: str) -> dict:
    """Refresh a HubSpot access token. Raises on HTTP error."""
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.hubspot_client_id,
        "client_secret": settings.hubspot_client_secret,
        "refresh_token": refresh_token,
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def get_access_token(tenant_id: str) -> str | None:
    """Return a valid access token for *tenant_id*, refreshing if expired.

    Returns ``None`` when no integration row exists OR refresh fails.
    Never raises — caller falls back to ``failed`` action run.
    """
    integration = get_integration(tenant_id)
    if not integration:
        return None

    access_token = integration.get("access_token") or ""
    refresh = integration.get("refresh_token") or ""
    expiry_raw = integration.get("token_expiry") or ""

    expired = True
    if expiry_raw:
        try:
            expiry_dt = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            # 60-second skew margin — refresh slightly before true expiry to
            # avoid races where HubSpot rejects an "about to expire" token.
            expired = expiry_dt <= datetime.now(timezone.utc) + timedelta(seconds=60)
        except (ValueError, TypeError):
            expired = True

    if not expired and access_token:
        return access_token

    if not refresh:
        logger.warning(
            "hubspot_tenant: access token expired and no refresh token for tenant %s",
            tenant_id,
        )
        return None

    try:
        token_response = _refresh(refresh)
    except Exception:
        logger.warning(
            "hubspot_tenant: token refresh failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None

    new_access = token_response.get("access_token")
    if not new_access:
        return None

    # HubSpot rotates refresh tokens on every refresh — persist the new one.
    new_refresh = token_response.get("refresh_token") or refresh
    expires_in = int(token_response.get("expires_in") or 1800)
    new_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    try:
        save_integration(
            tenant_id=tenant_id,
            access_token=new_access,
            refresh_token=new_refresh,
            token_expiry=new_expiry,
        )
    except Exception:
        logger.warning(
            "hubspot_tenant: persisting refreshed token failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    return new_access


def fetch_profile(access_token: str) -> dict:
    """Fetch portal id + hub domain for display metadata.

    Best-effort. Returns ``{}`` on failure rather than raising — connection
    still succeeds without it.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{_API_BASE}/integrations/v1/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "portal_id": data.get("portalId"),
                "hub_domain": data.get("hub_domain") or "",
                "user": data.get("user") or "",
            }
    except Exception:
        logger.warning("hubspot_tenant: profile fetch failed", exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# CRM operations
# ---------------------------------------------------------------------------


def _build_properties(payload: dict) -> dict:
    """Translate internal lead fields to HubSpot contact properties."""
    properties: dict[str, str] = {}
    email = (payload.get("email") or "").strip()
    if email:
        properties["email"] = email

    name = (payload.get("name") or "").strip()
    if name:
        # Split simple "First Last" — HubSpot stores firstname/lastname.
        # Single-word names go to firstname; everything past the first space
        # goes to lastname.
        parts = name.split(None, 1)
        properties["firstname"] = parts[0]
        if len(parts) > 1:
            properties["lastname"] = parts[1]

    phone = (payload.get("phone") or "").strip()
    if phone:
        properties["phone"] = phone

    notes = (payload.get("notes") or "").strip()
    if notes:
        # HubSpot doesn't have a notes property on contacts by default; map
        # to the standard `hs_lead_status` adjacent field via the `message`
        # property used by chat-flow forms. Truncate to 4000 chars.
        properties["message"] = notes[:4000]

    interests = payload.get("areas_of_interest") or []
    if isinstance(interests, list) and interests:
        properties["hs_content_membership_notes"] = ", ".join(
            str(item) for item in interests if item
        )[:255]

    return properties


async def upsert_contact(
    *,
    tenant_id: str,
    payload: dict,
) -> dict[str, Any]:
    """Upsert a contact in the tenant's HubSpot account.

    Returns ``{"success": True, "detail": "upserted", "contact_id": <id>,
    "operation": "created"|"updated"}`` on HTTP 200/201/204. Returns
    ``{"success": False, "detail": <error>}`` on any failure — never raises
    so the action handler can record a clean ``failed`` row.
    """
    access_token = get_access_token(tenant_id)
    if not access_token:
        return {
            "success": False,
            "detail": "no hubspot access token (integration missing, incomplete, or refresh failed)",
        }

    properties = _build_properties(payload)
    if not properties.get("email"):
        # HubSpot identifies contacts primarily by email; no email = no upsert.
        return {
            "success": False,
            "detail": "no email in payload (hubspot requires email as primary identifier)",
        }

    email = properties["email"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Look up existing contact by email (idProperty=email).
            lookup = await client.get(
                f"{_API_BASE}/crm/v3/objects/contacts/{email}",
                params={"idProperty": "email"},
                headers=headers,
            )
            if lookup.status_code == 200:
                existing_id = (lookup.json() or {}).get("id", "")
                patch_resp = await client.patch(
                    f"{_API_BASE}/crm/v3/objects/contacts/{existing_id}",
                    headers=headers,
                    json={"properties": properties},
                )
                if patch_resp.status_code in (200, 204):
                    return {
                        "success": True,
                        "detail": "updated",
                        "contact_id": existing_id,
                        "operation": "updated",
                    }
                return {
                    "success": False,
                    "detail": (
                        f"hubspot PATCH HTTP {patch_resp.status_code}: "
                        f"{(patch_resp.text or '')[:300]}"
                    ),
                }

            if lookup.status_code == 404:
                create_resp = await client.post(
                    f"{_API_BASE}/crm/v3/objects/contacts",
                    headers=headers,
                    json={"properties": properties},
                )
                if create_resp.status_code in (200, 201):
                    new_id = (create_resp.json() or {}).get("id", "")
                    return {
                        "success": True,
                        "detail": "created",
                        "contact_id": new_id,
                        "operation": "created",
                    }
                return {
                    "success": False,
                    "detail": (
                        f"hubspot POST HTTP {create_resp.status_code}: "
                        f"{(create_resp.text or '')[:300]}"
                    ),
                }

            if lookup.status_code in (401, 403):
                logger.error(
                    "hubspot_tenant: auth error for tenant %s (HTTP %s) — token may need re-consent",
                    tenant_id,
                    lookup.status_code,
                )
                return {
                    "success": False,
                    "detail": (
                        f"auth error (HTTP {lookup.status_code}) — reconnect HubSpot"
                    ),
                }

            return {
                "success": False,
                "detail": (
                    f"hubspot lookup HTTP {lookup.status_code}: "
                    f"{(lookup.text or '')[:300]}"
                ),
            }
    except httpx.HTTPError as e:
        logger.warning(
            "hubspot_tenant: transport error for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"transport error: {str(e)[:200]}"}
    except Exception as e:
        logger.warning(
            "hubspot_tenant: unexpected failure for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"unexpected: {str(e)[:200]}"}
