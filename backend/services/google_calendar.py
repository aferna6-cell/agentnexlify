"""Google Calendar integration — OAuth, token management, and calendar operations."""


import logging
import re
from datetime import datetime, timezone
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.integration_key_vault import (
    decrypt_integration_row,
    oauth_integration_payload_for_db,
)

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
    return decrypt_integration_row(result.data[0]) if result.data else None


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

    payload = oauth_integration_payload_for_db(payload)

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
    # Web-server OAuth with client_secret must not use PKCE unless the verifier
    # is round-tripped through state. gmail_connector disables PKCE the same way
    # (staging log: calendar callback 400 exchange after auth URL carried
    # code_challenge).
    flow.autogenerate_code_verifier = False
    flow.code_verifier = None
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
    import os

    # Calendar auth uses include_granted_scopes; Google may return scopes from
    # prior Gmail connects on the same OAuth client. Relax scope matching so
    # token exchange succeeds (staging log: exchange 400 after gmail.send grant).
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
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


def get_calendar_event(tenant_id: str, event_id: str) -> dict | None:
    """Fetch one Google Calendar event for independent verification.

    Returns a normalized dict on success:
      ``{id, status, summary, description, start, end, attendees}``
    Returns ``None`` when credentials/API fail or the event is missing —
    callers must treat that as verification failure / unknown, never invent.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return None
        event = (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )
        start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get(
            "date"
        )
        end = (event.get("end") or {}).get("dateTime") or (event.get("end") or {}).get("date")
        attendees = [
            {"email": a.get("email"), "displayName": a.get("displayName")}
            for a in (event.get("attendees") or [])
            if a.get("email")
        ]
        return {
            "id": event.get("id"),
            "status": event.get("status") or "confirmed",
            "summary": event.get("summary") or "",
            "description": event.get("description") or "",
            "start": start,
            "end": end,
            "attendees": attendees,
            "htmlLink": event.get("htmlLink"),
        }
    except HttpError as e:
        if e.resp.status == 404:
            return None
        logger.warning(
            "Google Calendar get event %s failed for tenant %s: %s",
            event_id,
            tenant_id,
            e,
        )
        return None
    except Exception:
        logger.warning(
            "Failed to get Google Calendar event %s for tenant %s",
            event_id,
            tenant_id,
            exc_info=True,
        )
        return None


def _normalize_calendar_event(event: dict) -> dict:
    start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get(
        "date"
    )
    end = (event.get("end") or {}).get("dateTime") or (event.get("end") or {}).get("date")
    attendees = [
        {"email": a.get("email"), "displayName": a.get("displayName")}
        for a in (event.get("attendees") or [])
        if a.get("email")
    ]
    return {
        "id": event.get("id"),
        "status": event.get("status") or "confirmed",
        "summary": event.get("summary") or "",
        "description": event.get("description") or "",
        "start": start,
        "end": end,
        "attendees": attendees,
        "htmlLink": event.get("htmlLink"),
    }


def lookup_calendar_event(tenant_id: str, event_id: str) -> dict:
    """Tri-state Google Calendar event lookup for verification callers.

    Returns one of:
      ``{"state": "found", "event": {...}}``
      ``{"state": "not_found"}`` — explicit provider 404
      ``{"state": "unknown", "reason": ...}`` — credentials/API failure
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return {"state": "unknown", "reason": "no_credentials"}
        event = (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )
        return {"state": "found", "event": _normalize_calendar_event(event)}
    except HttpError as e:
        if e.resp.status == 404:
            return {"state": "not_found"}
        return {"state": "unknown", "reason": f"http_{e.resp.status}"}
    except Exception as exc:
        logger.warning(
            "lookup_calendar_event failed tenant=%s event=%s",
            tenant_id,
            event_id,
            exc_info=True,
        )
        return {"state": "unknown", "reason": type(exc).__name__}


def deterministic_event_id(approval_id: str) -> str:
    """Stable Google event id for one approval.

    Google event ids are base32hex (``a-v`` and ``0-9``), 5–1024 characters.
    A UUID's hex is inside that alphabet, so the same approval always maps
    to the same id and a retry can look the event up before inserting.
    """
    compact = re.sub(r"[^a-v0-9]", "", str(approval_id).lower())
    if len(compact) < 5:
        compact = (compact + "calendar")[:8]
    return ("anx" + compact)[:1024]


def _http_status(exc: HttpError) -> int | None:
    try:
        return int(exc.resp.status)
    except (AttributeError, TypeError, ValueError):
        return None


def _get_google_event(service, event_id: str) -> dict | None:
    """Return the event, None on 404, or raise HttpError for other statuses."""
    try:
        return (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )
    except HttpError as exc:
        if _http_status(exc) == 404:
            return None
        raise


def _store_google_event_id(db, tenant_id: str, run: dict, event_id: str) -> None:
    """Remember the provider id on the approval row so a later approve is a no-op."""
    from backend.services.tenant_scope import tenant_table

    deliverable = dict(run.get("deliverable") or {})
    if deliverable.get("google_event_id") == event_id:
        return
    deliverable["google_event_id"] = event_id
    tenant_table(db, "os_agent_runs", tenant_id).update(
        {"deliverable": deliverable, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", run["id"]).execute()
    run["deliverable"] = deliverable


def insert_approved_calendar_event(db, tenant_id: str, approval_id: str) -> dict:
    """Insert one Google event for an approved calendar card, or refuse.

    Refuses unless this tenant's ``os_agent_runs`` row is ``approved`` and
    ``calendar.event.create``. A second call, or a retry after a lost
    response, returns the event already stored under the deterministic id
    and does not call ``events.insert`` again.

    The returned ``message`` is safe to show to the owner: it never includes
    token material or the provider error body.
    """
    from backend.services.tenant_scope import tenant_table

    rows = (
        tenant_table(db, "os_agent_runs", tenant_id)
        .select("*")
        .eq("id", approval_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {
            "ok": False,
            "code": "not_found",
            "event_id": None,
            "message": "That approval is not on this account. No event was created.",
        }
    run = rows[0]
    if run.get("deliverable_status") != "approved" or run.get("action_type") != (
        "calendar.event.create"
    ):
        return {
            "ok": False,
            "code": "not_approved",
            "event_id": None,
            "message": (
                "This booking is not approved, so nothing was added to Google Calendar."
            ),
        }

    deliverable = run.get("deliverable") or {}
    event = deliverable.get("calendar_event") or {}
    card_body = str(event.get("card_body") or "")
    if card_body and str(deliverable.get("body") or "").strip() != card_body.strip():
        return {
            "ok": False,
            "code": "body_mismatch",
            "event_id": None,
            "message": (
                "The approval card was edited and no longer matches the drafted "
                "booking. No event was created. Ask again to draft a new card."
            ),
        }
    summary = str(event.get("summary") or "").strip()
    start_utc = event.get("start_utc")
    end_utc = event.get("end_utc")
    if not summary or not start_utc or not end_utc:
        return {
            "ok": False,
            "code": "invalid_card",
            "event_id": None,
            "message": "This approval card is missing a time. No event was created.",
        }

    service = _build_service(tenant_id)
    if not service:
        return {
            "ok": False,
            "code": "token_unavailable",
            "event_id": None,
            "message": (
                "Google Calendar access expired or was revoked. Reconnect it on "
                "the Integrations page. No event was created."
            ),
        }

    event_id = deliverable.get("google_event_id") or deterministic_event_id(approval_id)
    try:
        existing = _get_google_event(service, event_id)
    except HttpError as exc:
        return _insert_http_failure(exc)
    if existing and existing.get("id"):
        _store_google_event_id(db, tenant_id, run, existing["id"])
        return {
            "ok": True,
            "code": "exists",
            "event_id": existing["id"],
            "deduplicated": True,
            "message": "That booking is already on Google Calendar.",
        }

    event_body = {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start_utc, "timeZone": "UTC"},
        "end": {"dateTime": end_utc, "timeZone": "UTC"},
    }
    if event.get("description"):
        event_body["description"] = event.get("description")
    # Attendees stay on the event, but Google must not email them. Invites
    # are a separate send and this path does not open that gate.
    if event.get("attendee_email"):
        event_body["attendees"] = [{"email": event["attendee_email"]}]

    try:
        created = (
            service.events()
            .insert(calendarId="primary", body=event_body, sendUpdates="none")
            .execute()
        )
    except TimeoutError:
        try:
            recovered = _get_google_event(service, event_id)
        except HttpError as exc:
            return _insert_http_failure(exc)
        if recovered and recovered.get("id"):
            _store_google_event_id(db, tenant_id, run, recovered["id"])
            return {
                "ok": True,
                "code": "exists",
                "event_id": recovered["id"],
                "deduplicated": True,
                "message": "That booking is already on Google Calendar.",
            }
        return {
            "ok": False,
            "code": "timeout",
            "event_id": None,
            "message": (
                "Google Calendar didn't confirm the event in time. Retry the "
                "approval and it will not create a duplicate."
            ),
        }
    except HttpError as exc:
        if _http_status(exc) == 409:
            try:
                recovered = _get_google_event(service, event_id)
            except HttpError as nested:
                return _insert_http_failure(nested)
            if recovered and recovered.get("id"):
                _store_google_event_id(db, tenant_id, run, recovered["id"])
                return {
                    "ok": True,
                    "code": "exists",
                    "event_id": recovered["id"],
                    "deduplicated": True,
                    "message": "That booking is already on Google Calendar.",
                }
        return _insert_http_failure(exc)
    except Exception:
        logger.warning(
            "insert_approved_calendar_event failed tenant=%s approval=%s",
            tenant_id,
            approval_id,
            exc_info=True,
        )
        return {
            "ok": False,
            "code": "provider_error",
            "event_id": None,
            "message": "Google Calendar couldn't create the event. No event was created.",
        }

    created_id = (created or {}).get("id") or event_id
    _store_google_event_id(db, tenant_id, run, created_id)
    return {
        "ok": True,
        "code": "created",
        "event_id": created_id,
        "deduplicated": False,
        "message": "Added to Google Calendar.",
    }


def _insert_http_failure(exc: HttpError) -> dict:
    status = _http_status(exc)
    logger.warning("Google Calendar insert refused status=%s", status)
    if status in (401, 403):
        return {
            "ok": False,
            "code": f"http_{status}",
            "event_id": None,
            "message": (
                "Google Calendar refused to create the event (access denied). "
                "Reconnect Google Calendar. No event was created."
            ),
        }
    return {
        "ok": False,
        "code": "http_error",
        "event_id": None,
        "message": "Google Calendar couldn't create the event. No event was created.",
    }


def list_calendar_events_in_window(
    tenant_id: str,
    time_min: datetime,
    time_max: datetime,
    *,
    summary_contains: str | None = None,
) -> dict:
    """List provider events in a time window (tri-state).

    Returns ``{"state": "ok", "events": [...]}`` on success or
    ``{"state": "unknown", "reason": ..., "events": []}`` when the query could
    not be verified.
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return {"state": "unknown", "reason": "no_credentials", "events": []}
        params: dict[str, Any] = {
            "calendarId": "primary",
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,
            "maxResults": 50,
        }
        if summary_contains:
            params["q"] = summary_contains
        result = service.events().list(**params).execute()
        items = result.get("items") or []
        return {
            "state": "ok",
            "events": [_normalize_calendar_event(ev) for ev in items],
        }
    except HttpError as exc:
        status = _http_status(exc)
        # Status only. The provider body can echo a bearer token.
        logger.warning(
            "list_calendar_events_in_window http status=%s tenant=%s",
            status,
            tenant_id,
        )
        if status in (401, 403):
            return {"state": "unknown", "reason": f"http_{status}", "events": []}
        return {"state": "unknown", "reason": "http_error", "events": []}
    except Exception:
        logger.warning(
            "list_calendar_events_in_window failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        return {"state": "unknown", "reason": "provider_error", "events": []}


def get_busy_times(
    tenant_id: str,
    time_min: datetime,
    time_max: datetime,
) -> list[tuple[datetime, datetime]] | None:
    """Query the Google Calendar freebusy API for busy periods.

    Returns a list of ``(start, end)`` UTC tuples on success (possibly empty when
    the calendar is genuinely free). Returns ``None`` when the calendar could NOT
    be verified — no service/token or an API error — so callers can distinguish
    "verified free" from "unknown" and avoid offering slots that may already be
    booked in the tenant's Google Calendar (external double-booking, audit C5).
    """
    try:
        service = _build_service(tenant_id)
        if not service:
            return None

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
        # Could-not-verify — signal None so callers fail closed instead of
        # treating an API error as "calendar is free" (audit C5).
        return None
