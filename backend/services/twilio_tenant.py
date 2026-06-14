"""Per-tenant (BYO) Twilio SMS send.

Sibling to ``twilio_service.send_sms``, which uses the platform-shared
``TWILIO_ACCOUNT_SID`` / ``TWILIO_AUTH_TOKEN`` / ``TWILIO_PHONE_NUMBER``
settings for every tenant. This module is the per-tenant escape hatch:
tenants that bring their own Twilio subaccount (10DLC compliance, branded
sender ID, distinct number per location) store credentials in the
``integrations`` table tagged ``provider='twilio_byo'`` and Group B SMS
sends dispatch to those credentials instead of the platform pool.

Mirrors the dispatch shape of ``m365_mail.send_email_via_graph``:
returns ``{"success": bool, "detail": str, "message_sid": str}`` so the
OS sms action handler can branch with a single ``_pick_provider`` call.

Never raises — Twilio HTTP failures, missing credentials, and unexpected
exceptions all fold into ``{"success": False, "detail": ...}`` so the
``sms.send`` worker records a clean ``failed`` run instead of crashing.

Credential storage layout in ``integrations`` row:

* ``provider``        = ``'twilio_byo'``
* ``access_token``    = Twilio Account SID (``ACxxxxxxxx...``) — not secret
                        but unique-per-tenant; reused for the auth header
* ``refresh_token``   = Twilio Auth Token — the real shared secret
* ``metadata``        = ``{"phone_number": "+15555550000", "friendly_name": ...}``
"""

import logging
from typing import Any

import httpx

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
_PROVIDER = "twilio_byo"


def get_integration(tenant_id: str) -> dict | None:
    """Fetch the twilio_byo integration row for a tenant."""
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


def is_connected(tenant_id: str) -> bool:
    """Return True if the tenant has a twilio_byo integration row."""
    try:
        row = get_integration(tenant_id)
    except Exception:
        logger.warning(
            "twilio_tenant: integration lookup failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return False
    if not row:
        return False
    # A row with no SID/token/phone is unusable — treat as not connected so the
    # action falls back to the platform pool instead of attempting a 401.
    return bool(
        row.get("access_token")
        and row.get("refresh_token")
        and (row.get("metadata") or {}).get("phone_number")
    )


def _credentials(tenant_id: str) -> dict[str, str] | None:
    row = get_integration(tenant_id)
    if not row:
        return None
    sid = (row.get("access_token") or "").strip()
    token = (row.get("refresh_token") or "").strip()
    phone = ((row.get("metadata") or {}).get("phone_number") or "").strip()
    if not sid or not token or not phone:
        return None
    return {"account_sid": sid, "auth_token": token, "from_number": phone}


async def send_sms_via_tenant(
    *,
    tenant_id: str,
    to: str,
    body: str,
) -> dict[str, Any]:
    """Send an SMS through the tenant's own Twilio subaccount.

    Returns ``{"success": True, "detail": "sent", "message_sid": <sid>}`` on
    HTTP 201 from Twilio. Returns ``{"success": False, "detail": <error>}`` on
    any failure — never raises so the action handler can record a clean
    ``failed`` row instead of crashing the worker.
    """
    creds = _credentials(tenant_id)
    if not creds:
        return {
            "success": False,
            "detail": "no twilio_byo credentials (integration missing or incomplete)",
        }

    # Twilio segment-friendly cap — same as platform send_sms.
    if len(body) > 1600:
        body = body[:1597] + "..."

    url = f"{_TWILIO_API_BASE}/Accounts/{creds['account_sid']}/Messages.json"
    payload = {
        "From": creds["from_number"],
        "To": to,
        "Body": body,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                data=payload,
                auth=(creds["account_sid"], creds["auth_token"]),
            )
    except httpx.HTTPError as e:
        logger.warning(
            "twilio_tenant: transport error for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"transport error: {str(e)[:200]}"}
    except Exception as e:
        logger.warning(
            "twilio_tenant: unexpected failure for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return {"success": False, "detail": f"unexpected: {str(e)[:200]}"}

    if response.status_code == 201:
        try:
            sid = (response.json() or {}).get("sid", "")
        except ValueError:
            sid = ""
        return {"success": True, "detail": "sent", "message_sid": sid}

    if response.status_code in (401, 403):
        logger.error(
            "twilio_tenant: auth error for tenant %s (HTTP %s) — credentials may be revoked",
            tenant_id,
            response.status_code,
        )
        return {
            "success": False,
            "detail": (
                f"auth error (HTTP {response.status_code}) — reconnect Twilio BYO"
            ),
        }

    body_snippet = (response.text or "")[:300]
    logger.warning(
        "twilio_tenant: Twilio API returned HTTP %s for tenant %s: %s",
        response.status_code,
        tenant_id,
        body_snippet,
    )
    return {
        "success": False,
        "detail": f"twilio HTTP {response.status_code}: {body_snippet}",
    }
