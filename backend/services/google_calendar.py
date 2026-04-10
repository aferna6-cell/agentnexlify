"""Google Calendar integration — OAuth, token management, and calendar operations."""


import logging
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------


def get_integration(tenant_id: str) -> dict | None:
    """Fetch the google_calendar integration row for a tenant."""
    db = get_service_supabase()
    result = (
        db.table("integrations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("provider", "google_calendar")
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
    """Upsert the google_calendar integration for a tenant.

    ``token_expiry`` should be an ISO-8601 datetime string.
    """
    db = get_service_supabase()
    payload: dict = {
        "tenant_id": tenant_id,
        "provider": "google_calendar",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
    }
    if metadata is not None:
        payload["metadata"] = metadata

    existing = get_integration(tenant_id)
    if existing:
        result = (
            db.table("integrations")
            .update(payload)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = db.table("integrations").insert(payload).execute()

    return result.data[0] if result.data else payload


def delete_integration(tenant_id: str) -> None:
    """Remove the google_calendar integration for a tenant."""
    db = get_service_supabase()
    db.table("integrations").delete().eq("tenant_id", tenant_id).eq(
        "provider", "google_calendar"
    ).execute()


def get_credentials(tenant_id: str) -> Credentials | None:
    """Build a ``Credentials`` object for *tenant_id*.

    If the stored access token is expired and a refresh token is available the
    credentials are silently refreshed and the new tokens are persisted back to
    the database.

    Returns ``None`` when no integration exists for the tenant.
    """
    integration = get_integration(tenant_id)
    if not integration:
        return None

    creds = Credentials(
        token=integration["access_token"],
        refresh_token=integration.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_integration(
                tenant_id=tenant_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_expiry=creds.expiry.isoformat() if creds.expiry else "",
            )
            logger.info("Refreshed Google credentials for tenant %s", tenant_id)
        except Exception:
            logger.warning(
                "Failed to refresh Google credentials for tenant %s",
                tenant_id,
                exc_info=True,
            )
            return None

    return creds


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------


def build_oauth_flow(redirect_uri: str) -> Flow:
    """Create a ``google_auth_oauthlib`` Flow using application credentials."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    return flow


def get_auth_url(redirect_uri: str, state: str) -> str:
    """Return the Google OAuth authorization URL."""
    flow = build_oauth_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code(code: str, redirect_uri: str) -> Credentials:
    """Exchange an authorization code for credentials."""
    flow = build_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)
    return flow.credentials


# ---------------------------------------------------------------------------
# Calendar operations
# ---------------------------------------------------------------------------


def _build_service(tenant_id: str):
    """Return a Calendar API service client, or ``None`` if credentials are unavailable."""
    creds = get_credentials(tenant_id)
    if not creds:
        logger.warning(
            "No Google Calendar credentials for tenant %s", tenant_id
        )
        return None
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    tenant_id: str,
    summary: str,
    start_utc: str | datetime,
    end_utc: str | datetime,
    attendee_email: str | None = None,
    description: str | None = None,
) -> str | None:
    """Create a Google Calendar event and return the event ID.

    ``start_utc`` and ``end_utc`` may be ISO-8601 strings or datetime objects.

    Returns ``None`` (instead of raising) when the API call fails so that the
    local booking flow is never interrupted.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return None

        start_iso = start_utc if isinstance(start_utc, str) else start_utc.isoformat()
        end_iso = end_utc if isinstance(end_utc, str) else end_utc.isoformat()

        event_body: dict = {
            "summary": summary,
            "start": {"dateTime": start_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
        }
        if attendee_email:
            event_body["attendees"] = [{"email": attendee_email}]
        if description:
            event_body["description"] = description

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        logger.info(
            "Created Google Calendar event %s for tenant %s",
            event.get("id"),
            tenant_id,
        )
        return event.get("id")
    except HttpError as e:
        if e.resp.status in (401, 403):
            logger.error(
                "Google Calendar auth error for tenant %s (HTTP %s) — token may need refresh",
                tenant_id, e.resp.status,
            )
        else:
            logger.warning(
                "Google Calendar API error for tenant %s: %s",
                tenant_id, e,
            )
        return None
    except Exception:
        logger.warning(
            "Failed to create Google Calendar event for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None


def update_calendar_event(
    tenant_id: str,
    event_id: str,
    **kwargs,
) -> str | None:
    """Update an existing Google Calendar event.

    Accepted keyword arguments mirror the Google Calendar event resource fields
    (e.g. ``summary``, ``description``, ``start``, ``end``).  For convenience,
    ``start`` and ``end`` may be passed as bare ``datetime`` objects and will be
    converted to the expected dict format automatically.

    Returns the event ID on success, or ``None`` on failure.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return None

        body: dict = {}
        for key, value in kwargs.items():
            if key in ("start_utc", "end_utc"):
                gcal_key = "start" if key == "start_utc" else "end"
                iso = value if isinstance(value, str) else value.isoformat()
                body[gcal_key] = {"dateTime": iso, "timeZone": "UTC"}
            elif key in ("start", "end") and isinstance(value, (datetime, str)):
                iso = value if isinstance(value, str) else value.isoformat()
                body[key] = {"dateTime": iso, "timeZone": "UTC"}
            else:
                body[key] = value

        event = (
            service.events()
            .patch(calendarId="primary", eventId=event_id, body=body)
            .execute()
        )
        logger.info(
            "Updated Google Calendar event %s for tenant %s",
            event_id,
            tenant_id,
        )
        return event.get("id")
    except Exception:
        logger.warning(
            "Failed to update Google Calendar event %s for tenant %s",
            event_id,
            tenant_id,
            exc_info=True,
        )
        return None


def delete_calendar_event(tenant_id: str, event_id: str) -> str | None:
    """Delete a Google Calendar event.

    Returns the event ID on success, or ``None`` on failure.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return None

        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(
            "Deleted Google Calendar event %s for tenant %s",
            event_id,
            tenant_id,
        )
        return event_id
    except Exception:
        logger.warning(
            "Failed to delete Google Calendar event %s for tenant %s",
            event_id,
            tenant_id,
            exc_info=True,
        )
        return None


def get_busy_times(
    tenant_id: str,
    time_min: datetime,
    time_max: datetime,
) -> list[tuple[datetime, datetime]]:
    """Query the Google Calendar freebusy API for busy periods.

    Returns a list of ``(start, end)`` datetime tuples in UTC.  On any failure
    an empty list is returned so that the local availability logic still works.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return []

        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "timeZone": "UTC",
            "items": [{"id": "primary"}],
        }

        result = service.freebusy().query(body=body).execute()

        busy_periods: list[tuple[datetime, datetime]] = []
        for period in result.get("calendars", {}).get("primary", {}).get("busy", []):
            start = datetime.fromisoformat(period["start"])
            end = datetime.fromisoformat(period["end"])
            # Normalise to UTC
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            busy_periods.append((start, end))

        return busy_periods
    except Exception:
        logger.warning(
            "Failed to fetch busy times from Google Calendar for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return []
