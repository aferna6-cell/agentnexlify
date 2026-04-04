"""Omnichannel message ingestion layer.

Schema notes (confirmed by live schema and migration 057):
  - chat_messages uses tenant_id
  - conversations uses client_id (NOT tenant_id)
  - leads uses client_id (NOT tenant_id)
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_supabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ingest_channel_message()
# ---------------------------------------------------------------------------
# Provider-keyed ingestion path used by the Facebook webhook router which
# looks up tenants via integrations.metadata.page_id.

def ingest_channel_message(
    *,
    provider: str,
    page_id: str,
    sender_id: str,
    sender_name: str | None,
    text: str,
    timestamp_ms: int | None = None,
) -> dict | None:
    """Normalize and store an inbound channel message (legacy path).

    Args:
        provider:     Channel identifier, e.g. ``"facebook"``.
        page_id:      The tenant's page/account ID on the provider — used to
                      look up which tenant owns this channel.
        sender_id:    Opaque external ID for the sender (e.g. Facebook PSID).
        sender_name:  Display name of the sender, if provided by the channel.
        text:         The plain-text message content.
        timestamp_ms: Unix timestamp in milliseconds from the channel payload.
                      Falls back to ``now`` when omitted.

    Returns:
        A dict with keys ``tenant_id`` and ``conversation_id`` on success, or
        ``None`` when the page_id cannot be resolved to a tenant.
    """
    db = get_supabase()

    # 1. Resolve tenant from the integration record
    try:
        integration_result = (
            db.table("integrations")
            .select("tenant_id, metadata")
            .eq("provider", provider)
            .execute()
        )
        tenant_id = None
        for row in (integration_result.data or []):
            meta = row.get("metadata") or {}
            if meta.get("page_id") == page_id:
                tenant_id = row["tenant_id"]
                break
        if not tenant_id:
            logger.warning(
                "channel_manager: no tenant found for provider=%s page_id=%s",
                provider,
                page_id,
            )
            return None
    except Exception:
        logger.exception(
            "channel_manager: failed to resolve tenant for provider=%s page_id=%s",
            provider,
            page_id,
        )
        return None

    # 2. Upsert lead by external sender ID stored in lead tags / metadata.
    #    Look for a lead where a tag matches "fb_psid:<sender_id>".
    lead_id: str | None = None
    tag_marker = f"fb_psid:{sender_id}"
    try:
        existing_lead = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .contains("tags", [tag_marker])
            .limit(1)
            .execute()
        )
        if existing_lead.data:
            lead_id = existing_lead.data[0]["id"]
        else:
            new_lead = {
                "client_id": tenant_id,
                "name": sender_name or f"Facebook User {sender_id[-6:]}",
                "status": "new",
                "tags": [tag_marker],
                "conversation_summary": f"Inbound Facebook Messenger message from {sender_id}",
            }
            inserted = db.table("leads").insert(new_lead).execute()
            if inserted.data:
                lead_id = inserted.data[0]["id"]
    except Exception:
        logger.exception(
            "channel_manager: failed to upsert lead for tenant=%s sender=%s",
            tenant_id,
            sender_id,
        )
        # Continue — we can still store the message without a lead

    # 3. Upsert conversation keyed on channel session: "{provider}:{sender_id}"
    session_id = f"{provider}:{sender_id}"
    conversation_id: str | None = None
    try:
        conv_result = (
            db.table("conversations")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            conversation_id = conv_result.data[0]["id"]
        else:
            new_conv = {
                "client_id": tenant_id,
                "session_id": session_id,
                "status": "open",
                "lead_id": lead_id,
            }
            conv_insert = db.table("conversations").insert(new_conv).execute()
            if conv_insert.data:
                conversation_id = conv_insert.data[0]["id"]
    except Exception:
        logger.exception(
            "channel_manager: failed to upsert conversation for tenant=%s session=%s",
            tenant_id,
            session_id,
        )

    # 4. Append to chat_messages (canonical message store, uses tenant_id)
    if timestamp_ms:
        msg_ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
    else:
        msg_ts = datetime.now(timezone.utc).isoformat()

    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": "user",
            "content": text,
            "created_at": msg_ts,
        }).execute()
    except Exception:
        logger.exception(
            "channel_manager: failed to insert chat_message for tenant=%s session=%s",
            tenant_id,
            session_id,
        )

    return {"tenant_id": tenant_id, "conversation_id": conversation_id}
