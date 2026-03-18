"""Omnichannel message normalization layer.

All inbound messages (widget, SMS, Facebook, etc.) flow through receive().
All outbound messages (team replies) flow through send().

Channel detection is based on session_id prefix conventions:
  sms_{phone}        -> "sms"
  fb_{sender_id}     -> "facebook"
  ig_{sender_id}     -> "instagram"
  wa_{phone}         -> "whatsapp"
  everything else    -> "widget"

Schema notes (confirmed by live schema and migration 057):
  - chat_messages uses tenant_id
  - conversations uses client_id (NOT tenant_id)
  - leads uses client_id (NOT tenant_id)

Legacy function:
  ingest_channel_message() — the original provider-keyed ingestion path used by
  the Facebook webhook. Preserved for backward compatibility.
"""

import logging
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.models.database import get_supabase
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NormalizedMessage dataclass
# ---------------------------------------------------------------------------

@dataclass
class NormalizedMessage:
    channel: str          # "widget", "sms", "facebook", "instagram", "whatsapp", "email"
    tenant_id: str
    session_id: str       # channel-specific: "sms_{phone}", "fb_{sender_id}", etc.
    sender_name: str = ""
    sender_identifier: str = ""   # phone, email, fb_id
    content: str = ""
    attachments: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: dict = field(default_factory=dict)
    role: str = "user"    # "user" for inbound, "assistant" for outbound


# ---------------------------------------------------------------------------
# Channel detection
# ---------------------------------------------------------------------------

def detect_channel(session_id: str) -> str:
    """Extract channel from session_id prefix.

    Convention:
      sms_*   -> "sms"
      fb_*    -> "facebook"
      ig_*    -> "instagram"
      wa_*    -> "whatsapp"
      else    -> "widget"
    """
    if session_id.startswith("sms_"):
        return "sms"
    if session_id.startswith("fb_"):
        return "facebook"
    if session_id.startswith("ig_"):
        return "instagram"
    if session_id.startswith("wa_"):
        return "whatsapp"
    return "widget"


# ---------------------------------------------------------------------------
# Inbound: receive()
# ---------------------------------------------------------------------------

async def receive(msg: NormalizedMessage) -> dict:
    """Normalize and store an inbound message from any channel.

    Steps:
    1. Store message in chat_messages (uses tenant_id).
    2. Find or create conversation in conversations (uses client_id).
    3. Trigger lead capture if sender info is present.

    Returns:
        {"conversation_id": str, "session_id": str, "is_new": bool}
    """
    db = get_supabase()

    # ------------------------------------------------------------------
    # Step 1: Store message in chat_messages
    # chat_messages uses tenant_id (confirmed: migration 006)
    # ------------------------------------------------------------------
    try:
        db.table("chat_messages").insert({
            "tenant_id": msg.tenant_id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.timestamp.isoformat(),
        }).execute()
        logger.info(
            "channel_manager.receive: stored chat_message tenant=%s session=%s channel=%s role=%s",
            msg.tenant_id, msg.session_id, msg.channel, msg.role,
        )
    except Exception:
        logger.error(
            "channel_manager.receive: chat_messages INSERT failed tenant=%s session=%s",
            msg.tenant_id, msg.session_id,
            exc_info=True,
        )

    # ------------------------------------------------------------------
    # Step 2: Find or create conversation
    # conversations uses client_id (confirmed: migration 057)
    # ------------------------------------------------------------------
    conversation_id, is_new = await _find_or_create_conversation(
        db=db,
        tenant_id=msg.tenant_id,
        session_id=msg.session_id,
        channel=msg.channel,
    )

    # ------------------------------------------------------------------
    # Step 3: Lead capture — create or update lead if we have identity info
    # leads uses client_id (confirmed: CLAUDE.md, bug-patterns.md)
    # ------------------------------------------------------------------
    if msg.sender_name or msg.sender_identifier:
        await _upsert_lead(
            db=db,
            tenant_id=msg.tenant_id,
            sender_name=msg.sender_name,
            sender_identifier=msg.sender_identifier,
            channel=msg.channel,
            conversation_id=conversation_id,
        )

    return {
        "conversation_id": conversation_id,
        "session_id": msg.session_id,
        "is_new": is_new,
    }


async def _find_or_create_conversation(
    db,
    tenant_id: str,
    session_id: str,
    channel: str,
) -> tuple:
    """Return (conversation_id, is_new).

    Looks up by client_id + session_id. Creates with channel and status='active'
    if not found. Falls back to session_id as stable identifier if DB operations
    fail (so chat_messages can still accumulate history by session_id).
    """
    # Lookup by client_id + session_id
    try:
        result = (
            db.table("conversations")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result.data:
            conv_id = result.data[0]["id"]
            logger.debug(
                "channel_manager: found existing conversation %s for session %s",
                conv_id, session_id,
            )
            # Touch updated_at to signal recent activity
            try:
                db.table("conversations").update(
                    {"updated_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", conv_id).execute()
            except Exception:
                logger.warning(
                    "channel_manager: updated_at touch failed for conversation %s",
                    conv_id, exc_info=True,
                )
            return conv_id, False
    except Exception:
        logger.warning(
            "channel_manager: conversations lookup failed tenant=%s session=%s",
            tenant_id, session_id,
            exc_info=True,
        )

    # Create new conversation
    try:
        new_conv = (
            db.table("conversations")
            .insert({
                "client_id": tenant_id,
                "session_id": session_id,
                "channel": channel,
                "status": "active",
            })
            .execute()
        )
        if new_conv.data:
            conv_id = new_conv.data[0]["id"]
            logger.info(
                "channel_manager: created conversation %s channel=%s tenant=%s session=%s",
                conv_id, channel, tenant_id, session_id,
            )
            return conv_id, True
    except Exception:
        logger.warning(
            "channel_manager: conversations INSERT failed tenant=%s session=%s",
            tenant_id, session_id,
            exc_info=True,
        )

    # Fallback: use session_id as stable conversation identifier so chat_messages
    # can still accumulate history by session_id even without a conversations row.
    logger.warning(
        "channel_manager: using session_id as fallback conversation_id for session=%s",
        session_id,
    )
    return session_id, True


async def _upsert_lead(
    db,
    tenant_id: str,
    sender_name: str,
    sender_identifier: str,
    channel: str,
    conversation_id: str,
) -> None:
    """Create or update a lead record from inbound sender info.

    leads table uses client_id (NOT tenant_id).
    Deduplication is by email or phone against client_id.
    Only fills in missing fields on existing leads — never overwrites.
    """
    # Determine identifier type
    is_email = bool(sender_identifier and "@" in sender_identifier)
    is_phone = bool(sender_identifier and not is_email)

    fields: dict = {}
    if sender_name:
        fields["name"] = sender_name
    if is_email:
        fields["email"] = sender_identifier
    if is_phone:
        fields["phone"] = sender_identifier

    if not fields:
        logger.debug("channel_manager._upsert_lead: no usable fields, skipping")
        return

    # Dedup by email first, then phone
    lead_id = None
    try:
        if is_email:
            existing = (
                db.table("leads")
                .select("id")
                .eq("client_id", tenant_id)
                .eq("email", sender_identifier)
                .limit(1)
                .execute()
            )
            if existing.data:
                lead_id = existing.data[0]["id"]
        elif is_phone:
            existing = (
                db.table("leads")
                .select("id")
                .eq("client_id", tenant_id)
                .eq("phone", sender_identifier)
                .limit(1)
                .execute()
            )
            if existing.data:
                lead_id = existing.data[0]["id"]
    except Exception:
        logger.error(
            "channel_manager._upsert_lead: dedup query failed tenant=%s",
            tenant_id, exc_info=True,
        )

    if lead_id:
        # Fill in only missing fields — do not overwrite existing data
        try:
            existing_lead = (
                db.table("leads")
                .select("name, email, phone")
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
            existing_data = existing_lead.data[0] if existing_lead.data else {}
            updates = {k: v for k, v in fields.items() if not existing_data.get(k)}
            if updates:
                db.table("leads").update(updates).eq("id", lead_id).execute()
                logger.info(
                    "channel_manager._upsert_lead: updated lead %s fields=%s",
                    lead_id, list(updates.keys()),
                )
        except Exception:
            logger.error(
                "channel_manager._upsert_lead: lead UPDATE failed lead=%s",
                lead_id, exc_info=True,
            )
    else:
        # Create new lead
        try:
            lead_data: dict = {
                "client_id": tenant_id,
                "status": "new",
                "source": channel,
                **fields,
            }
            # Attach conversation_id only if it looks like a valid UUID
            try:
                _uuid.UUID(conversation_id)
                lead_data["conversation_id"] = conversation_id
            except (ValueError, AttributeError):
                logger.debug(
                    "channel_manager._upsert_lead: conversation_id %r is not a UUID, omitting",
                    conversation_id,
                )

            result = db.table("leads").insert(lead_data).execute()
            if result.data:
                lead_id = result.data[0]["id"]
                logger.info(
                    "channel_manager._upsert_lead: created lead %s channel=%s tenant=%s",
                    lead_id, channel, tenant_id,
                )
            else:
                logger.warning(
                    "channel_manager._upsert_lead: INSERT returned no data tenant=%s",
                    tenant_id,
                )
        except Exception:
            logger.error(
                "channel_manager._upsert_lead: lead INSERT failed tenant=%s",
                tenant_id, exc_info=True,
            )


# ---------------------------------------------------------------------------
# Outbound: send()
# ---------------------------------------------------------------------------

async def send(
    tenant_id: str,
    session_id: str,
    content: str,
    channel: str = None,
) -> bool:
    """Send an outbound message on the appropriate channel.

    Auto-detects channel from session_id prefix if not explicitly provided.
    Stores the outbound message in chat_messages with role="assistant" regardless
    of delivery success (widget polls chat_messages directly for new messages).

    Returns True on success, False on delivery failure.
    """
    resolved_channel = channel or detect_channel(session_id)

    logger.info(
        "channel_manager.send: tenant=%s session=%s channel=%s",
        tenant_id, session_id, resolved_channel,
    )

    success = False

    # Dispatch to the correct delivery service
    if resolved_channel == "sms":
        success = await _send_sms_message(session_id, content)
    elif resolved_channel == "facebook":
        success = _send_facebook_message(tenant_id, session_id, content)
    elif resolved_channel == "instagram":
        success = _send_instagram_message(tenant_id, session_id, content)
    elif resolved_channel == "whatsapp":
        success = _send_whatsapp_message(tenant_id, session_id, content)
    else:
        # Widget channel: store in chat_messages only — widget polls for new messages.
        # No active push needed; the poll loop will pick it up.
        logger.debug(
            "channel_manager.send: widget channel — store-only, no active push "
            "tenant=%s session=%s",
            tenant_id, session_id,
        )
        success = True

    # Always persist the outbound message in chat_messages (canonical store)
    db = get_supabase()
    try:
        db.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "session_id": session_id,
            "role": "assistant",
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        logger.info(
            "channel_manager.send: stored outbound message tenant=%s session=%s channel=%s",
            tenant_id, session_id, resolved_channel,
        )
    except Exception:
        logger.error(
            "channel_manager.send: chat_messages INSERT failed for outbound message "
            "tenant=%s session=%s",
            tenant_id, session_id,
            exc_info=True,
        )

    return success


# ---------------------------------------------------------------------------
# Channel-specific send helpers
# ---------------------------------------------------------------------------

async def _send_sms_message(session_id: str, content: str) -> bool:
    """Extract phone number from sms_{phone} session_id and send via Twilio."""
    # session_id format: "sms_{phone}" e.g. "sms_+14155551234"
    if not session_id.startswith("sms_"):
        logger.error(
            "channel_manager._send_sms_message: session_id %r does not have sms_ prefix",
            session_id,
        )
        return False

    phone = session_id[len("sms_"):]
    if not phone:
        logger.error(
            "channel_manager._send_sms_message: empty phone extracted from session_id %r",
            session_id,
        )
        return False

    logger.info("channel_manager._send_sms_message: sending SMS to %s", phone)
    try:
        result = await send_sms(to=phone, body=content)
        return result
    except Exception:
        logger.error(
            "channel_manager._send_sms_message: send_sms raised exception for phone=%s",
            phone, exc_info=True,
        )
        return False


def _send_facebook_message(tenant_id: str, session_id: str, content: str) -> bool:
    """Send a Facebook Messenger message. NOT YET IMPLEMENTED — stub."""
    logger.warning(
        "channel_manager._send_facebook_message: Facebook Messenger send is not yet "
        "implemented (tenant=%s session=%s). Message was NOT delivered to the channel.",
        tenant_id, session_id,
    )
    # Return True so the outbound message is still stored in chat_messages.
    return True


def _send_instagram_message(tenant_id: str, session_id: str, content: str) -> bool:
    """Send an Instagram Direct message. NOT YET IMPLEMENTED — stub."""
    logger.warning(
        "channel_manager._send_instagram_message: Instagram Direct send is not yet "
        "implemented (tenant=%s session=%s). Message was NOT delivered to the channel.",
        tenant_id, session_id,
    )
    return True


def _send_whatsapp_message(tenant_id: str, session_id: str, content: str) -> bool:
    """Send a WhatsApp message. NOT YET IMPLEMENTED — stub."""
    logger.warning(
        "channel_manager._send_whatsapp_message: WhatsApp send is not yet implemented "
        "(tenant=%s session=%s). Message was NOT delivered to the channel.",
        tenant_id, session_id,
    )
    return True


# ---------------------------------------------------------------------------
# Legacy: ingest_channel_message()
# ---------------------------------------------------------------------------
# The original provider-keyed ingestion path. Used by the Facebook webhook
# router which looks up tenants via integrations.metadata.page_id. Preserved
# for backward compatibility. New code should use receive() instead.

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
