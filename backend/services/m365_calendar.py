"""Microsoft 365 / Azure AD calendar integration.

Parallel to ``backend.services.google_calendar`` but for tenants that picked
Outlook / Microsoft 365 instead of Google. Same shape — ``get_integration``,
``save_integration``, ``create_calendar_event`` — so the OS calendar action
handler can dispatch between providers at runtime based on the tenant's
connected integration row.

Scopes: ``Calendars.ReadWrite`` (event create/update/delete) plus
``Mail.Send`` (pre-positioned for Group B email send via Graph) and
``offline_access`` (refresh token). Per project choice (2026-05-27), tenant
pays the broader consent screen once and avoids reconnects later when
M365-backed email send ships.

OAuth tokens are stored in the same ``integrations`` table as Google, tagged
``provider='m365_calendar'``. Refresh logic mirrors google_calendar:
silently refresh when the access token is expired and persist the new
tokens back to the DB before returning.

Implementation note: uses raw ``httpx`` rather than ``msal`` because httpx
is already a runtime dependency and the OAuth code-grant flow is small
enough that the msal abstraction is not worth a new package on the Railway
build.
"""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

SCOPES = [
    "Calendars.ReadWrite",
    "Mail.Send",
    "offline_access",
]

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _authorize_url() -> str:
    return (
        f"https://login.microsoftonline.com/{settings.m365_tenant_id}"
        "/oauth2/v2.0/authorize"
    )


def _token_url() -> str:
    return (
        f"https://login.microsoftonline.com/{settings.m365_tenant_id}"
        "/oauth2/v2.0/token"
    )


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


def get_integration(tenant_id: str) -> dict | None:
    """Fetch the m365_calendar integration row for a tenant."""
    db = get_service_supabase()
    result = (
        db.table("integrations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("provider", "m365_calendar")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_integration(
    tenant_id: str,
    access_token: str,
    refresh_token: str,
    token_expiry: str,
    metadata: dict | None = None,
) -> dict:
    """Upsert the m365_calendar integration for a tenant."""
    db = get_service_supabase()
    payload: dict = {
        "tenant_id": tenant_id,
        "provider": "m365_calendar",
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
    """Remove the m365_calendar integration for a tenant."""
    db = get_service_supabase()
    db.table("integrations").delete().eq("tenant_id", tenant_id).eq(
        "provider", "m365_calendar"
    ).execute()


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------


def build_authorization_url(redirect_uri: str, state: str) -> str:
    """Return the Azure AD authorization URL for the OAuth code-grant flow."""
    params = {
        "client_id": settings.m365_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "prompt": "consent",
    }
    return f"{_authorize_url()}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for tokens.

    Returns the raw token response dict. The caller is expected to pass
    ``access_token``, ``refresh_token`` and an ISO expiry into
    ``save_integration``.
    """
    data = {
        "client_id": settings.m365_client_id,
        "client_secret": settings.m365_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _token_url(),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def _refresh_token(refresh_token: str) -> dict:
    """Refresh an Azure AD access token. Raises on HTTP error."""
    data = {
        "client_id": settings.m365_client_id,
        "client_secret": settings.m365_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES),
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _token_url(),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def get_access_token(tenant_id: str) -> str | None:
    """Return a valid access token for *tenant_id*, refreshing if expired.

    Returns ``None`` when no integration row exists OR when refresh fails.
    Never raises — calendar create path falls back to ``failed`` action run
    instead of crashing the worker.
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
            # avoid races where Graph rejects an "about to expire" token.
            expired = expiry_dt <= datetime.now(timezone.utc) + timedelta(seconds=60)
        except (ValueError, TypeError):
            expired = True

    if not expired and access_token:
        return access_token

    if not refresh:
        logger.warning(
            "m365_calendar: access token expired and no refresh token for tenant %s",
            tenant_id,
        )
        return None

    try:
        token_response = _refresh_token(refresh)
    except Exception:
        logger.warning(
            "m365_calendar: token refresh failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None

    new_access = token_response.get("access_token")
    if not new_access:
        return None

    new_refresh = token_response.get("refresh_token") or refresh
    expires_in = int(token_response.get("expires_in") or 3600)
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
            "m365_calendar: persisted refreshed token failed for tenant %s",
            tenant_id,
            exc_info=True,
        )

    return new_access


# ---------------------------------------------------------------------------
# Calendar operations
# ---------------------------------------------------------------------------


def _normalize_iso(value: str | datetime) -> str:
    """Microsoft Graph wants ISO without trailing Z, so normalize."""
    iso = value if isinstance(value, str) else value.isoformat()
    return iso.replace("Z", "+00:00")


def create_calendar_event(
    tenant_id: str,
    summary: str,
    start_utc: str | datetime,
    end_utc: str | datetime,
    attendee_email: str | None = None,
    description: str | None = None,
) -> str | None:
    """Create an Outlook calendar event via Microsoft Graph.

    Returns the event ID on success, or ``None`` on any failure so the local
    booking flow is never interrupted (mirrors google_calendar contract).
    """
    access_token = get_access_token(tenant_id)
    if not access_token:
        logger.warning(
            "m365_calendar: no access token for tenant %s — cannot create event",
            tenant_id,
        )
        return None

    event_body: dict = {
        "subject": summary,
        "start": {"dateTime": _normalize_iso(start_utc), "timeZone": "UTC"},
        "end": {"dateTime": _normalize_iso(end_utc), "timeZone": "UTC"},
    }
    if attendee_email:
        event_body["attendees"] = [
            {
                "emailAddress": {"address": attendee_email},
                "type": "required",
            }
        ]
    if description:
        event_body["body"] = {"contentType": "text", "content": description}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_GRAPH_BASE}/me/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=event_body,
            )
            if response.status_code in (401, 403):
                logger.error(
                    "m365_calendar: auth error for tenant %s (HTTP %s) — token may need re-consent",
                    tenant_id,
                    response.status_code,
                )
                return None
            response.raise_for_status()
            event = response.json()
            event_id = event.get("id")
            logger.info(
                "m365_calendar: created event %s for tenant %s",
                event_id,
                tenant_id,
            )
            return event_id
    except httpx.HTTPError:
        logger.warning(
            "m365_calendar: graph create event failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None
    except Exception:
        logger.warning(
            "m365_calendar: unexpected failure for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None
