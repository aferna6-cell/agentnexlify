"""Facebook Messenger Send API — outbound replies to inbound DMs.

Used by the Agent OS outbound mirror (Group C Phase 2) to thread OS
assistant replies back to the customer who DM'd the tenant's Page.

Send API contract: POST ``/me/messages`` with ``messaging_type=RESPONSE``
(the 24h standard messaging window — reserved for replies to a
customer-initiated message). The recipient identifier is the sender PSID
captured during inbound ingestion and stored on the os_thread's
``source_metadata.sender_id``.

Tokens: the Page access token lives in ``integrations`` rows where
``provider='facebook'``; ``access_token`` is the page token and
``metadata.page_id`` identifies the Page. Same schema as
``os_actions/social_facebook.py``.

Failure semantics: NEVER raise — the caller (mirror) returns
``error:facebook_send:<detail>`` to the OS runner, which logs and
continues. The orchestrator reply is already persisted in
``os_messages``.
"""

import logging
from typing import Any

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_FB_API_VERSION = getattr(settings, "facebook_api_version", "v21.0") or "v21.0"
_FB_GRAPH_BASE = f"https://graph.facebook.com/{_FB_API_VERSION}"


def _load_page_token(client_id: str) -> dict | None:
    """Return ``{'page_id', 'page_access_token'}`` or None when not connected."""
    db = get_service_supabase()
    row = (
        db.table("integrations")
        .select("access_token, metadata")
        .eq("tenant_id", client_id)
        .eq("provider", "facebook")
        .limit(1)
        .execute()
    )
    if not getattr(row, "data", None):
        return None
    record = row.data[0]
    metadata = record.get("metadata") or {}
    page_id = metadata.get("page_id") if isinstance(metadata, dict) else None
    page_access_token = record.get("access_token")
    if not page_id or not page_access_token:
        return None
    return {"page_id": page_id, "page_access_token": page_access_token}


async def send_messenger_reply(
    *,
    tenant_id: str,
    recipient_psid: str,
    content: str,
) -> dict[str, Any]:
    """Send a Messenger reply to ``recipient_psid`` for the tenant's Page.

    Returns a dict with:
      - ``success``: bool
      - ``detail``: short error string when ``success`` is False
      - ``message_id``: provider message id when ``success`` is True
      - ``recipient_id``: echo of the PSID (useful for log correlation)

    Never raises; HTTP errors and provider failures are reported via
    ``success=False`` + ``detail``.
    """
    page = _load_page_token(tenant_id)
    if not page:
        return {"success": False, "detail": "no_page"}

    url = f"{_FB_GRAPH_BASE}/me/messages"
    api_body = {
        "recipient": {"id": recipient_psid},
        "messaging_type": "RESPONSE",
        "message": {"text": content},
    }
    params = {"access_token": page["page_access_token"]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, params=params, json=api_body)
    except Exception as exc:
        logger.warning(
            "facebook_messenger: HTTP error tenant_id=%s psid=%s",
            tenant_id,
            recipient_psid,
            exc_info=True,
        )
        return {"success": False, "detail": f"http_error:{str(exc)[:160]}"}

    if resp.status_code >= 400:
        snippet = (resp.text or "")[:300]
        return {
            "success": False,
            "detail": f"http_{resp.status_code}:{snippet}",
        }

    body = {}
    try:
        body = resp.json() if resp.content else {}
    except Exception:
        body = {}

    return {
        "success": True,
        "message_id": body.get("message_id", ""),
        "recipient_id": body.get("recipient_id", recipient_psid),
    }
