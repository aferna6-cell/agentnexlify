"""Resend webhook endpoint for email event handling (bounces, complaints).

Handles email.bounced and email.complained events from Resend to mark
lead emails as invalid and prevent future sends.
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

_RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")


def _verify_resend_signature(payload_bytes: bytes, headers: dict) -> bool:
    """Verify Resend webhook signature using the svix headers.

    Returns True when verification passes or when no secret is configured
    (allows graceful migration — once the secret env var is set, verification
    becomes mandatory).
    """
    if not _RESEND_WEBHOOK_SECRET:
        logger.error("RESEND_WEBHOOK_SECRET not set — rejecting webhook (misconfiguration)")
        return False

    signature_header = headers.get("svix-signature", "")
    msg_id = headers.get("svix-id", "")
    timestamp = headers.get("svix-timestamp", "")

    if not signature_header or not msg_id or not timestamp:
        return False

    # Resend/Svix signs: "{msg_id}.{timestamp}.{body}"
    sign_content = f"{msg_id}.{timestamp}.".encode() + payload_bytes

    # The secret may be prefixed with "whsec_" — strip it and base64-decode
    secret = _RESEND_WEBHOOK_SECRET
    if secret.startswith("whsec_"):
        import base64
        secret_bytes = base64.b64decode(secret[6:])
    else:
        secret_bytes = secret.encode()

    expected = hmac.new(secret_bytes, sign_content, hashlib.sha256).digest()

    import base64 as b64
    expected_b64 = b64.b64encode(expected).decode()

    # Svix sends comma-separated versioned sigs: "v1,<base64>"
    for part in signature_header.split(" "):
        parts = part.split(",", 1)
        if len(parts) == 2 and parts[0] == "v1":
            if hmac.compare_digest(parts[1], expected_b64):
                return True

    return False


@router.post("/resend")
async def resend_webhook(request: Request):
    """Handle Resend webhook events.

    Supported events:
    - email.bounced: marks lead's email as bounced
    - email.complained: marks lead's email as bounced (spam complaint)
    """
    payload_bytes = await request.body()

    if not _verify_resend_signature(payload_bytes, dict(request.headers)):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = body.get("type", "")
    event_data = body.get("data", {})

    logger.info("Resend webhook received: type=%s", event_type)

    if event_type in ("email.bounced", "email.complained"):
        await _handle_bounce(event_data, event_type)
    else:
        logger.debug("Unhandled Resend event: %s", event_type)

    return {"status": "ok"}


async def _handle_bounce(event_data: dict, event_type: str) -> None:
    """Mark the lead's email as bounced, scoped to the originating tenant.

    Looks up the tenant from the email_sequence_sends or campaign_sends table
    using the Resend message ID (the 'email_id' in event data). Falls back to
    updating all matching leads only if no tenant can be identified.
    """
    to_addresses = event_data.get("to", [])
    if isinstance(to_addresses, str):
        to_addresses = [to_addresses]

    if not to_addresses:
        logger.warning("Resend bounce event with no 'to' addresses")
        return

    db = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Try to identify the originating tenant from the Resend email_id
    tenant_id = None
    resend_email_id = event_data.get("email_id")
    if resend_email_id:
        # Check email_sequence_sends first (drip sequences)
        try:
            send_res = (
                db.table("email_sequence_sends")
                .select("tenant_id")
                .eq("resend_message_id", resend_email_id)
                .limit(1)
                .execute()
            )
            if send_res.data:
                tenant_id = send_res.data[0].get("tenant_id")
        except Exception:
            logger.debug("Could not look up tenant from email_sequence_sends")

        # Check campaign_sends if not found
        if not tenant_id:
            try:
                camp_res = (
                    db.table("campaign_sends")
                    .select("tenant_id")
                    .eq("resend_message_id", resend_email_id)
                    .limit(1)
                    .execute()
                )
                if camp_res.data:
                    tenant_id = camp_res.data[0].get("tenant_id")
            except Exception:
                logger.debug("Could not look up tenant from campaign_sends")

    for email_addr in to_addresses:
        email_addr = email_addr.strip().lower()
        if not email_addr:
            continue

        try:
            query = (
                db.table("leads")
                .update({
                    "email_bounced": True,
                    "email_bounced_at": now_iso,
                })
                .eq("email", email_addr)
            )

            # Scope to tenant if we identified one; skip if unknown to prevent cross-tenant update
            if tenant_id:
                query = query.eq("client_id", tenant_id)
            else:
                logger.warning(
                    "Could not determine tenant for bounce event — "
                    "skipping lead update for email %s to prevent cross-tenant write",
                    email_addr,
                )
                continue

            result = query.execute()

            updated_count = len(result.data) if result.data else 0
            if updated_count > 0:
                logger.info(
                    "Marked %d lead(s) as email_bounced for %s (event: %s, tenant: %s)",
                    updated_count, email_addr, event_type, tenant_id or "all",
                )
            else:
                logger.debug(
                    "No leads found with email %s for bounce event", email_addr
                )
        except Exception:
            logger.exception(
                "Failed to mark email as bounced for %s", email_addr
            )
