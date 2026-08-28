"""Gmail integration — OAuth, token management, inbox polling, reply send.

Token/OAuth shape mirrors ``backend/services/google_calendar.py`` (same
``integrations`` table keyed by ``tenant_id`` + ``provider``, same
google-auth-oauthlib Flow, same Credentials refresh dance) but for Gmail:
a distinct row (``provider='gmail'``), distinct scopes, and a distinct
redirect URI (Google requires an exact match per registered URI even under
the same OAuth client — see ``settings.gmail_redirect_uri``).

Gmail Data API calls (list/get/send) go through the small ``_api_get`` /
``_api_post`` seam so tests can monkeypatch two functions instead of faking
a googleapiclient discovery-service call chain.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import base64
import logging
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.inbound_email_parser import ParsedEmail
from backend.services.integration_key_vault import (
    decrypt_integration_row,
    encrypt_oauth_tokens,
)

logger = logging.getLogger(__name__)

PROVIDER = "gmail"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

_GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Sentinel returned by list_history when Gmail 404s the cursor (history
# expired — Gmail retains ~7 days of history entries). Callers reseed via a
# fresh get_profile + list_recent_message_ids pass.
HISTORY_EXPIRED = "history_expired"


class GmailApiError(Exception):
    """A non-2xx response from the Gmail Data API."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        super().__init__(f"gmail api error {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Token management (mirrors google_calendar.py)
# ---------------------------------------------------------------------------


def get_integration(tenant_id: str) -> dict | None:
    """Fetch the gmail integration row for a tenant."""
    db = get_service_supabase()
    result = (
        db.table("integrations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("provider", PROVIDER)
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
    """Upsert the gmail integration for a tenant.

    ``token_expiry`` should be an ISO-8601 datetime string. When ``metadata``
    is omitted on an update (e.g. a token-refresh save), the existing
    metadata (email_address/history_id/last_poll_at/watch_expiry) is left
    untouched rather than clobbered.
    """
    db = get_service_supabase()
    payload: dict = {
        "tenant_id": tenant_id,
        "provider": PROVIDER,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
    }
    if metadata is not None:
        payload["metadata"] = metadata

    payload = encrypt_oauth_tokens(payload)

    existing = get_integration(tenant_id)
    if existing:
        result = db.table("integrations").update(payload).eq("id", existing["id"]).execute()
    else:
        result = db.table("integrations").insert(payload).execute()
    return result.data[0] if result.data else payload


def update_metadata(tenant_id: str, updates: dict[str, Any]) -> dict | None:
    """Merge-update the metadata JSONB (history_id/last_poll_at/watch_expiry/
    email_address). Returns the updated row, or ``None`` if no integration
    exists for this tenant. Best-effort: logs and returns ``None`` on any
    DB failure rather than raising, so a poll-loop cursor-write failure
    never crashes the whole poll pass.
    """
    try:
        existing = get_integration(tenant_id)
        if not existing:
            return None
        merged = dict(existing.get("metadata") or {})
        merged.update(updates)
        db = get_service_supabase()
        result = (
            db.table("integrations")
            .update({"metadata": merged})
            .eq("id", existing["id"])
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "gmail_connector: update_metadata failed tenant=%s", tenant_id, exc_info=True
        )
        return None


def delete_integration(tenant_id: str) -> None:
    """Remove the gmail integration for a tenant."""
    db = get_service_supabase()
    db.table("integrations").delete().eq("tenant_id", tenant_id).eq(
        "provider", PROVIDER
    ).execute()


def is_connected(tenant_id: str) -> bool:
    """True if the tenant has a gmail integration row."""
    try:
        return get_integration(tenant_id) is not None
    except Exception:
        logger.warning(
            "gmail_connector: integration lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return False


def get_credentials(tenant_id: str) -> Credentials | None:
    """Build a ``Credentials`` object for *tenant_id*, refreshing + persisting
    a new access token when the stored one is expired. Returns ``None`` when
    no integration exists, or refresh fails.
    """
    integration = get_integration(tenant_id)
    if not integration:
        return None

    creds = Credentials(
        token=integration.get("access_token"),
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
            logger.info("gmail_connector: refreshed credentials tenant=%s", tenant_id)
        except Exception:
            logger.warning(
                "gmail_connector: refresh failed tenant=%s", tenant_id, exc_info=True
            )
            return None

    return creds


# ---------------------------------------------------------------------------
# OAuth flow helpers (mirrors google_calendar.py)
# ---------------------------------------------------------------------------


def build_oauth_flow(redirect_uri: str) -> Flow:
    """Create a ``google_auth_oauthlib`` Flow using the platform's Google app."""
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
    """Return the Gmail OAuth authorization URL."""
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
# Gmail Data API — isolated behind _api_get / _api_post for testability
# ---------------------------------------------------------------------------


def _api_get(tenant_id: str, path: str, params: dict | None = None) -> dict | None:
    """GET against the Gmail Data API for this tenant.

    Returns ``None`` when there are no usable credentials. Raises
    ``GmailApiError`` on a non-2xx response so callers that care about the
    status code (e.g. 404 = expired history cursor) can branch on it;
    transport-level failures log and return ``None``.
    """
    creds = get_credentials(tenant_id)
    if not creds:
        return None
    try:
        resp = httpx.get(
            f"{_GMAIL_API_BASE}{path}",
            headers={"Authorization": f"Bearer {creds.token}"},
            params=params or {},
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise GmailApiError(e.response.status_code, e.response.text[:200]) from e
    except Exception:
        logger.warning(
            "gmail_connector: GET %s failed tenant=%s", path, tenant_id, exc_info=True
        )
        return None


def _api_post(tenant_id: str, path: str, json_body: dict) -> dict | None:
    """POST against the Gmail Data API for this tenant. Same contract as
    ``_api_get`` (raises ``GmailApiError`` on non-2xx, ``None`` on missing
    credentials or transport failure)."""
    creds = get_credentials(tenant_id)
    if not creds:
        return None
    try:
        resp = httpx.post(
            f"{_GMAIL_API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
            json=json_body,
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise GmailApiError(e.response.status_code, e.response.text[:200]) from e
    except Exception:
        logger.warning(
            "gmail_connector: POST %s failed tenant=%s", path, tenant_id, exc_info=True
        )
        return None


def get_profile(tenant_id: str) -> dict:
    """Fetch ``{emailAddress, historyId}`` — used to seed the sync cursor.

    Returns ``{}`` on any failure (missing credentials, transport error,
    non-2xx) rather than raising.
    """
    try:
        return _api_get(tenant_id, "/profile") or {}
    except GmailApiError:
        logger.warning("gmail_connector: get_profile failed tenant=%s", tenant_id, exc_info=True)
        return {}


def list_recent_message_ids(tenant_id: str, max_results: int = 20) -> list[str]:
    """Initial poll: most recent INBOX message ids (no history cursor yet)."""
    try:
        data = _api_get(
            tenant_id, "/messages", params={"maxResults": max_results, "labelIds": "INBOX"}
        )
    except GmailApiError:
        logger.warning(
            "gmail_connector: list_recent_message_ids failed tenant=%s", tenant_id, exc_info=True
        )
        return []
    if not data:
        return []
    return [m["id"] for m in (data.get("messages") or []) if m.get("id")]


def list_history(tenant_id: str, since_history_id: str) -> tuple[list[str], str | None]:
    """New INBOX message ids since ``since_history_id`` + the latest historyId.

    Returns ``([], HISTORY_EXPIRED)`` when Gmail 404s the cursor so the
    caller can fall back to a fresh ``list_recent_message_ids`` +
    ``get_profile`` reseed. Returns ``([], None)`` on any other failure
    (no credentials, transport error) — the caller should skip this poll
    and retry next cycle without losing the old cursor.
    """
    if not since_history_id:
        return [], None

    message_ids: list[str] = []
    latest_history_id: str | None = None
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {
            "startHistoryId": since_history_id,
            "historyTypes": "messageAdded",
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            data = _api_get(tenant_id, "/history", params=params)
        except GmailApiError as e:
            if e.status_code == 404:
                logger.warning(
                    "gmail_connector: history cursor expired tenant=%s", tenant_id
                )
                return [], HISTORY_EXPIRED
            logger.warning(
                "gmail_connector: list_history failed tenant=%s status=%s",
                tenant_id,
                e.status_code,
            )
            return [], None
        if data is None:
            return [], None

        for entry in data.get("history") or []:
            for added in entry.get("messagesAdded") or []:
                msg = added.get("message") or {}
                if msg.get("id") and "INBOX" in (msg.get("labelIds") or []):
                    message_ids.append(msg["id"])
        if data.get("historyId"):
            latest_history_id = data["historyId"]
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    seen: set[str] = set()
    deduped = [m for m in message_ids if not (m in seen or seen.add(m))]
    return deduped, latest_history_id


def _header_map(payload: dict) -> dict[str, str]:
    headers = (payload or {}).get("headers") or []
    return {str(h.get("name", "")).lower(): str(h.get("value", "")) for h in headers}


def _decode_base64url(data: str) -> str:
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        logger.warning("gmail_connector: base64url decode failed", exc_info=True)
        return ""


def _extract_body_text(payload: dict) -> str:
    """Depth-first walk of MIME parts, preferring text/plain."""
    if not payload:
        return ""
    mime_type = payload.get("mimeType", "")
    body = payload.get("body") or {}
    data = body.get("data")
    if mime_type == "text/plain" and data:
        return _decode_base64url(data)

    parts = payload.get("parts") or []
    for part in parts:
        if part.get("mimeType") == "text/plain":
            part_data = (part.get("body") or {}).get("data")
            if part_data:
                return _decode_base64url(part_data)
    for part in parts:
        text = _extract_body_text(part)
        if text:
            return text

    if mime_type == "text/html" and data:
        return _decode_base64url(data)
    return ""


def _parse_sender(raw: str) -> tuple[str, str]:
    """'"Jane Doe" <jane@x.com>' -> ('jane@x.com', 'Jane Doe')."""
    name, address = parseaddr(raw or "")
    return address.strip(), name.strip()


def _normalize_message(raw: dict) -> ParsedEmail:
    payload = raw.get("payload") or {}
    headers = _header_map(payload)
    sender_email, sender_name = _parse_sender(headers.get("from", ""))
    message_id = raw.get("id") or headers.get("message-id", "")
    return ParsedEmail(
        provider_message_id=message_id,
        thread_id=raw.get("threadId") or message_id,
        sender_email=sender_email,
        sender_name=sender_name,
        recipient=headers.get("to", ""),
        subject=headers.get("subject", ""),
        body_text=_extract_body_text(payload),
        headers=headers,
    )


def get_message(tenant_id: str, message_id: str) -> ParsedEmail | None:
    """Fetch + normalize one Gmail message. ``None`` on any failure."""
    try:
        data = _api_get(tenant_id, f"/messages/{message_id}", params={"format": "full"})
    except GmailApiError:
        logger.warning(
            "gmail_connector: get_message failed tenant=%s message_id=%s",
            tenant_id,
            message_id,
            exc_info=True,
        )
        return None
    if not data:
        return None
    return _normalize_message(data)


def find_message_id_by_rfc822_msgid(tenant_id: str, rfc822_msgid: str) -> str | None:
    """Find a message in this mailbox by its RFC 5322 ``Message-ID`` header.

    This is the pre-send duplicate check that makes an approved send safe to
    re-drive: we stamp every outgoing message with a Message-ID derived from
    its execution id, so asking Gmail "does a message with this id already
    exist?" answers "did this exact send already happen?" without depending on
    our own record of it.

    Gmail's ``rfc822msgid:`` search operator matches the header exactly.
    Returns the Gmail message id, or ``None`` when there is no match, no
    credentials, or the search fails — callers must treat ``None`` as
    "unknown", never as "definitely not sent".
    """
    if not rfc822_msgid:
        return None
    bare = rfc822_msgid.strip().strip("<>")
    try:
        data = _api_get(
            tenant_id,
            "/messages",
            params={"q": f"rfc822msgid:{bare}", "maxResults": 1},
        )
    except GmailApiError:
        logger.warning(
            "gmail_connector: rfc822msgid lookup failed tenant=%s", tenant_id, exc_info=True
        )
        return None
    if not data:
        return None
    messages = data.get("messages") or []
    return messages[0].get("id") if messages else None


def send_message(
    db: Any,
    tenant_id: str,
    *,
    to: str,
    subject: str,
    body_html: str,
    rfc822_msgid: str | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict[str, Any]:
    """Send a NEW message through the tenant's Gmail mailbox.

    Sibling of ``send_reply`` (which requires an existing thread) for the
    action layer's ``send_email`` tool, sharing the same credentials, the same
    ``_api_post`` transport and the same return contract. ``db`` is accepted
    for signature parity with the other outbound senders.

    ``rfc822_msgid`` sets an explicit RFC 5322 ``Message-ID`` header. Callers
    derive it from the action's execution id so the sent message carries a
    stable, unique fingerprint: ``find_message_id_by_rfc822_msgid`` can then
    tell whether a send already happened before retrying one whose outcome is
    unknown. Gmail assigns its own Message-ID when this is omitted, which
    makes that check impossible — so the tool always passes one.

    Returns ``{"success": bool, "detail": str, "message_id": str,
    "thread_id": str}`` — never raises.
    """
    message = MIMEText(body_html, "html")
    message["to"] = to
    message["subject"] = subject
    if rfc822_msgid:
        message["Message-ID"] = (
            rfc822_msgid if rfc822_msgid.startswith("<") else f"<{rfc822_msgid}>"
        )
    if in_reply_to:
        ref_header = in_reply_to if in_reply_to.startswith("<") else f"<{in_reply_to}>"
        message["In-Reply-To"] = ref_header
        message["References"] = references or ref_header

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    body: dict[str, Any] = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    try:
        data = _api_post(tenant_id, "/messages/send", body)
    except GmailApiError as e:
        return {
            "success": False,
            "detail": f"gmail api error {e.status_code}",
            "status_code": e.status_code,
        }

    if not data:
        # No credentials, or a transport failure _api_post swallowed. The
        # outcome of a transport failure is genuinely unknown — the caller
        # resolves it with find_message_id_by_rfc822_msgid, never by resending
        # blindly.
        return {"success": False, "detail": "no gmail credentials or send failed"}

    logger.info(
        "gmail_connector: message sent tenant=%s message_id=%s", tenant_id, data.get("id")
    )
    return {
        "success": True,
        "detail": "sent",
        "message_id": data.get("id", ""),
        "thread_id": data.get("threadId", ""),
    }


def send_reply(
    db: Any,
    tenant_id: str,
    *,
    thread_id: str,
    to: str,
    subject: str,
    body_html: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict[str, Any]:
    """Send a threaded reply through the tenant's Gmail mailbox.

    ``db`` is accepted (unused directly — Gmail access goes through
    ``get_credentials``) to match the sibling outbound senders' signature
    shape (``email_sender.send_email``, ``m365_mail.send_email_via_graph``)
    so callers can dispatch on a uniform contract. ``in_reply_to`` /
    ``references`` (RFC 5322) set the threading headers on the raw MIME
    message so the customer's mail client groups the reply correctly;
    ``thread_id`` (Gmail's own threadId) additionally keeps it in the same
    Gmail conversation view even if headers are absent.

    Returns ``{"success": bool, "detail": str, "message_id": str,
    "thread_id": str}`` — never raises.
    """
    message = MIMEText(body_html, "html")
    message["to"] = to
    message["subject"] = subject
    if in_reply_to:
        ref_header = in_reply_to if in_reply_to.startswith("<") else f"<{in_reply_to}>"
        message["In-Reply-To"] = ref_header
        message["References"] = references or ref_header

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    body: dict[str, Any] = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    try:
        data = _api_post(tenant_id, "/messages/send", body)
    except GmailApiError as e:
        return {"success": False, "detail": f"gmail api error {e.status_code}"}

    if not data:
        return {"success": False, "detail": "no gmail credentials or send failed"}

    logger.info("gmail_connector: reply sent tenant=%s message_id=%s", tenant_id, data.get("id"))
    return {
        "success": True,
        "detail": "sent",
        "message_id": data.get("id", ""),
        "thread_id": data.get("threadId", ""),
    }
