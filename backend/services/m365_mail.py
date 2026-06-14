"""Microsoft 365 / Graph outbound email via /me/sendMail.

Sibling to ``m365_calendar`` — reuses the same OAuth integration row
(``provider='m365_calendar'``) and the same Azure AD token plumbing
(``m365_calendar.get_access_token``). Scope ``Mail.Send`` is already
granted at consent time per the OAuth flow shipped with the calendar
connector (see ``m365_calendar.SCOPES``), so no extra reconnect step is
needed when a tenant opts in to M365-backed email send.

Returns a ``{"success": bool, "detail": str, "message_id": str}`` dict
shape compatible with the Resend-backed ``email_sender.send_email``
contract so the OS email action handler can swap providers with a single
branch.

Microsoft Graph ``/me/sendMail`` returns ``202 Accepted`` with no body on
success — the closest stable identifier is the per-request ID returned
in the ``request-id`` response header. We surface that as ``message_id``
so the action_runs row has something traceable; callers that just need
a yes/no should read ``success``.
"""

import logging
from typing import Any

import httpx

from backend.services.m365_calendar import get_access_token, get_integration

logger = logging.getLogger(__name__)

_GRAPH_SEND_MAIL = "https://graph.microsoft.com/v1.0/me/sendMail"


def is_connected(tenant_id: str) -> bool:
    """Return True if the tenant has an M365 integration row."""
    try:
        return get_integration(tenant_id) is not None
    except Exception:
        logger.warning(
            "m365_mail: integration lookup failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return False


async def send_email_via_graph(
    *,
    tenant_id: str,
    to: str,
    subject: str,
    body_html: str,
    save_to_sent_items: bool = True,
) -> dict[str, Any]:
    """Send an email through Microsoft Graph using the tenant's M365 mailbox.

    Returns ``{"success": True, "detail": "sent", "message_id": <request-id>}``
    on a 202 Accepted response from Graph. Returns
    ``{"success": False, "detail": <error>}`` on any failure — never raises so
    the action handler can record a clean ``failed`` row instead of crashing
    the worker.
    """
    access_token = get_access_token(tenant_id)
    if not access_token:
        return {
            "success": False,
            "detail": "no m365 access token (integration missing or refresh failed)",
        }

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": "true" if save_to_sent_items else "false",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _GRAPH_SEND_MAIL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=message,
            )
    except httpx.HTTPError as e:
        logger.warning(
            "m365_mail: graph sendMail transport error for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"transport error: {str(e)[:200]}"}
    except Exception as e:
        logger.warning(
            "m365_mail: unexpected failure for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"unexpected: {str(e)[:200]}"}

    if response.status_code == 202:
        request_id = response.headers.get("request-id") or response.headers.get(
            "x-ms-request-id", ""
        )
        return {
            "success": True,
            "detail": "sent",
            "message_id": request_id,
        }

    if response.status_code in (401, 403):
        logger.error(
            "m365_mail: auth error for tenant %s (HTTP %s) — token may need re-consent",
            tenant_id,
            response.status_code,
        )
        return {
            "success": False,
            "detail": f"auth error (HTTP {response.status_code}) — reconnect M365",
        }

    body_snippet = (response.text or "")[:300]
    logger.warning(
        "m365_mail: graph sendMail returned HTTP %s for tenant %s: %s",
        response.status_code,
        tenant_id,
        body_snippet,
    )
    return {
        "success": False,
        "detail": f"graph HTTP {response.status_code}: {body_snippet}",
    }
