"""Agent OS inbound channel bridges.

Bridges fan-in customer-facing messages from widget / email / SMS /
Facebook into the same orchestrator pipeline the chat-shell router uses,
so the OS sees every customer message — not just owner-typed ones.

Source spec: specs/agent-os-connectors-inbound_spec.md
Build plan:  plans/agent-os-connectors-inbound_plan.md

One public function per source:
  - bridge_widget(...)
  - bridge_email(...)
  - bridge_sms(...)
  - bridge_facebook(...)

All four share the same skeleton (kept private in this module):
  1. Owner toggled this bridge on? -> short-circuit if not.
  2. Already ingested this provider message? -> short-circuit if so
     (idempotency anchored on os_messages.source_ref UNIQUE index).
  3. Resolve or create os_thread for (client_id, source, source_thread_id).
  4. Append os_message with role='user', inbound_kind, source_ref.
  5. Run the orchestrator turn via shared
     ``os_thread_runner.process_user_turn``.

Bridges are fire-and-forget from the caller's perspective: webhook
handlers wrap ``bridge_*`` in ``BackgroundTasks`` so signature-verified
provider POSTs stay well under the 5s retry budget (FB/Twilio/Postmark).
Inside this module each step is awaited synchronously because the worker
is already running off the request thread.

Toggle storage (per spec §Data Model): one row per tenant in
``tenant_integrations`` with ``provider='os_inbound_bridges'`` and
``config_jsonb`` holding {widget_enabled, email_enabled, sms_enabled,
facebook_enabled, email_provider, email_inbound_address}. Helpers in
the §Toggle config section below own read/write/upsert.
"""

import logging
from typing import Any, Literal

from backend.services.os_thread_runner import process_user_turn
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

BridgeSource = Literal["widget", "email", "sms", "facebook"]
InboundKind = Literal["auto_reply", "normal", "system_notice"]

_BRIDGE_PROVIDER = "os_inbound_bridges"
_DEFAULT_CONFIG: dict[str, Any] = {
    "widget_enabled": True,
    "email_enabled": False,
    "sms_enabled": False,
    "facebook_enabled": False,
    "email_provider": None,
    "email_inbound_address": None,
}


# ---------------------------------------------------------------------------
# Toggle config (Phase 1.3)
# ---------------------------------------------------------------------------


def get_bridge_config(db: Any, client_id: str) -> dict[str, Any]:
    """Return the merged bridge config for a tenant (defaults filled in).

    Missing row -> returns ``_DEFAULT_CONFIG`` copy; never raises.
    """
    result = (
        tenant_table(db, "tenant_integrations", client_id)
        .select("config_jsonb, enabled")
        .eq("provider", _BRIDGE_PROVIDER)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return dict(_DEFAULT_CONFIG)
    row = rows[0]
    if not row.get("enabled", True):
        # Row exists but the integration itself is disabled — treat every
        # per-source toggle as off so callers don't have to special-case.
        return {
            **_DEFAULT_CONFIG,
            **{k: False for k in _DEFAULT_CONFIG if k.endswith("_enabled")},
        }
    return {**_DEFAULT_CONFIG, **(row.get("config_jsonb") or {})}


def set_bridge_toggle(
    db: Any, client_id: str, source: BridgeSource, enabled: bool
) -> dict[str, Any]:
    """Upsert the per-source enabled flag for a tenant.

    Returns the post-update merged config (same shape as
    ``get_bridge_config``).
    """
    field = f"{source}_enabled"
    if field not in _DEFAULT_CONFIG:
        raise ValueError(f"Unknown bridge source: {source!r}")

    current = get_bridge_config(db, client_id)
    current[field] = bool(enabled)

    existing = (
        tenant_table(db, "tenant_integrations", client_id)
        .select("id")
        .eq("provider", _BRIDGE_PROVIDER)
        .limit(1)
        .execute()
    ).data or []

    if existing:
        tenant_table(db, "tenant_integrations", client_id).update(
            {"config_jsonb": current, "enabled": True}
        ).eq("id", existing[0]["id"]).execute()
    else:
        tenant_table(db, "tenant_integrations", client_id).insert(
            {
                "provider": _BRIDGE_PROVIDER,
                "config_jsonb": current,
                "enabled": True,
            }
        ).execute()

    return current


def is_bridge_enabled(db: Any, client_id: str, source: BridgeSource) -> bool:
    """Whether a given source bridge is on for this tenant."""
    cfg = get_bridge_config(db, client_id)
    return bool(cfg.get(f"{source}_enabled", False))


def resolve_tenant_by_inbound_phone(db: Any, to_number: str) -> str | None:
    """Cross-tenant lookup: which client owns this Twilio inbound number?

    Same shape as ``resolve_tenant_by_inbound_email`` but matches against
    ``tenants.notification_phone`` — the field every provisioned tenant
    populates when setting up Twilio. Phone matching is normalized to
    last-10-digits because Twilio sends E.164 (``+15551234567``) while
    tenants sometimes save the friendly form (``(555) 123-4567``).
    """
    if not to_number:
        return None
    needle = _normalize_phone(to_number)
    if not needle:
        return None

    result = (
        db.table("tenants")
        .select("id, notification_phone")
        .not_.is_("notification_phone", "null")
        .execute()
    )
    rows = result.data or []
    for row in rows:
        stored = _normalize_phone(row.get("notification_phone") or "")
        if stored and stored == needle:
            return row.get("id")
    return None


def _normalize_phone(raw: str) -> str:
    """Strip to last-10-digits for cross-format phone matching."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def resolve_tenant_by_inbound_email(db: Any, recipient: str) -> str | None:
    """Cross-tenant lookup: which client owns this inbound email address?

    Inbound email webhooks arrive without a tenant claim — we identify
    the tenant by the recipient address configured in the bridge config.
    Must bypass ``tenant_table`` scoping (we don't know the client_id
    yet — that's what we're resolving). Returns the matching
    ``client_id`` or ``None`` when no tenant owns this address.

    The match is case-insensitive on the local-part+domain — providers
    normalize differently and tenants paste addresses with mixed case.
    """
    if not recipient:
        return None
    needle = recipient.strip().lower()
    if not needle:
        return None

    result = (
        db.table("tenant_integrations")
        .select("client_id, config_jsonb")
        .eq("provider", _BRIDGE_PROVIDER)
        .execute()
    )
    rows = result.data or []
    for row in rows:
        cfg = row.get("config_jsonb") or {}
        addr = (cfg.get("email_inbound_address") or "").strip().lower()
        if addr and addr == needle:
            return row.get("client_id")
    return None


# ---------------------------------------------------------------------------
# Bridge entry points (Phase 1.2 skeletons — wired in later phases)
# ---------------------------------------------------------------------------


async def bridge_widget(
    db: Any,
    client_id: str,
    conversation_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Bridge a widget chat message into the OS.

    ``conversation_id`` is the widget ``conversations.id`` row.
    ``provider_message_id`` is the widget ``chat_messages.id`` row.
    Returns ``None`` if the bridge is off or the message was already
    ingested (idempotent on retry).
    """
    return await _bridge_common(
        db=db,
        client_id=client_id,
        source="widget",
        source_thread_id=conversation_id,
        provider_message_id=provider_message_id,
        user_content=user_content,
        sender_metadata=sender_metadata,
        inbound_kind="normal",
    )


async def bridge_email(
    db: Any,
    client_id: str,
    email_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any] | None = None,
    inbound_kind: InboundKind = "normal",
) -> dict[str, Any] | None:
    """Bridge an inbound email into the OS.

    ``email_thread_id`` should be a stable per-thread identifier
    (e.g. ``In-Reply-To`` chain root or provider thread ID).
    ``provider_message_id`` is the email Message-ID. ``inbound_kind``
    lets the webhook tag auto-replies / OOO so the orchestrator can skip
    routing them.
    """
    return await _bridge_common(
        db=db,
        client_id=client_id,
        source="email",
        source_thread_id=email_thread_id,
        provider_message_id=provider_message_id,
        user_content=user_content,
        sender_metadata=sender_metadata,
        inbound_kind=inbound_kind,
    )


async def bridge_sms(
    db: Any,
    client_id: str,
    sms_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any] | None = None,
    inbound_kind: InboundKind = "normal",
) -> dict[str, Any] | None:
    """Bridge an inbound SMS into the OS.

    ``sms_thread_id`` is typically the ``(from_number, to_number)`` pair
    rendered as a stable string; ``provider_message_id`` is the Twilio
    ``MessageSid``.
    """
    return await _bridge_common(
        db=db,
        client_id=client_id,
        source="sms",
        source_thread_id=sms_thread_id,
        provider_message_id=provider_message_id,
        user_content=user_content,
        sender_metadata=sender_metadata,
        inbound_kind=inbound_kind,
    )


async def bridge_facebook(
    db: Any,
    client_id: str,
    fb_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Bridge a Facebook DM into the OS.

    ``fb_thread_id`` is the FB conversation ID; ``provider_message_id``
    is the FB message ID.
    """
    return await _bridge_common(
        db=db,
        client_id=client_id,
        source="facebook",
        source_thread_id=fb_thread_id,
        provider_message_id=provider_message_id,
        user_content=user_content,
        sender_metadata=sender_metadata,
        inbound_kind="normal",
    )


# ---------------------------------------------------------------------------
# Shared helpers (internal)
# ---------------------------------------------------------------------------


async def _bridge_common(
    *,
    db: Any,
    client_id: str,
    source: BridgeSource,
    source_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any] | None,
    inbound_kind: InboundKind,
) -> dict[str, Any] | None:
    """Shared bridge skeleton. See module docstring §steps."""
    if not is_bridge_enabled(db, client_id, source):
        return None

    source_ref = f"{source}:{provider_message_id}"

    if _already_ingested(db, client_id, source_ref):
        return None

    thread = _resolve_or_create_thread(
        db,
        client_id=client_id,
        source=source,
        source_thread_id=source_thread_id,
        sender_metadata=sender_metadata,
    )

    user_message_row = _append_inbound_message(
        db,
        client_id=client_id,
        thread_id=thread["id"],
        user_content=user_content,
        inbound_kind=inbound_kind,
        source_ref=source_ref,
    )

    # Auto-replies + OOO should not trigger the orchestrator — they land
    # as evidence in the thread but don't burn Sonnet tokens.
    if inbound_kind == "auto_reply":
        return {
            "user_message": user_message_row,
            "assistant_message": None,
            "action": "skipped_auto_reply",
            "agent_runs": [],
        }

    # ``background_tasks=None`` -> worker runs inline; we're already off
    # the request thread inside the webhook's BackgroundTask.
    return await process_user_turn(
        db, client_id, thread["id"], user_message_row, background_tasks=None
    )


def _already_ingested(db: Any, client_id: str, source_ref: str) -> bool:
    """True if an os_messages row with this source_ref already exists.

    Belt + suspenders for the UNIQUE partial index on
    ``(client_id, source_ref) WHERE source_ref IS NOT NULL`` from
    migration 124. Lets us short-circuit cleanly instead of catching a
    constraint violation on insert.
    """
    result = (
        tenant_table(db, "os_messages", client_id)
        .select("id")
        .eq("source_ref", source_ref)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def _resolve_or_create_thread(
    db: Any,
    *,
    client_id: str,
    source: BridgeSource,
    source_thread_id: str,
    sender_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Find the matching os_thread or create a new one.

    Dedup key (per migration 124 unique partial index):
    ``(client_id, source, source_thread_id)`` when source_thread_id is
    not NULL.
    """
    existing = (
        tenant_table(db, "os_threads", client_id)
        .select("*")
        .eq("source", source)
        .eq("source_thread_id", source_thread_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    title = _default_thread_title(source, sender_metadata)
    return (
        tenant_table(db, "os_threads", client_id)
        .insert(
            {
                "title": title,
                "source": source,
                "source_thread_id": source_thread_id,
                "source_metadata": _redact_metadata(sender_metadata),
            }
        )
        .execute()
        .data[0]
    )


def _append_inbound_message(
    db: Any,
    *,
    client_id: str,
    thread_id: str,
    user_content: str,
    inbound_kind: InboundKind,
    source_ref: str,
) -> dict[str, Any]:
    """Insert the user-role os_message that triggered this bridge."""
    return (
        tenant_table(db, "os_messages", client_id)
        .insert(
            {
                "thread_id": thread_id,
                "role": "user",
                "content": user_content,
                "inbound_kind": inbound_kind,
                "source_ref": source_ref,
            }
        )
        .execute()
        .data[0]
    )


def _default_thread_title(
    source: BridgeSource, sender_metadata: dict[str, Any] | None
) -> str:
    """Human-readable thread title for new bridged threads."""
    sender_metadata = sender_metadata or {}
    if source == "widget":
        return "Widget conversation"
    if source == "email":
        addr = sender_metadata.get("from") or sender_metadata.get("sender_email")
        return f"Email from {addr}" if addr else "Inbound email"
    if source == "sms":
        phone = sender_metadata.get("from") or sender_metadata.get("sender_phone")
        return f"SMS from {phone}" if phone else "Inbound SMS"
    if source == "facebook":
        name = sender_metadata.get("from_name") or sender_metadata.get("sender_name")
        return f"Facebook DM from {name}" if name else "Facebook DM"
    return f"Inbound {source}"


_REDACT_KEYS = {
    "access_token",
    "refresh_token",
    "id_token",
    "oauth_token",
    "client_secret",
    "authorization",
}


def _redact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip OAuth tokens and credentials from provider metadata before insert.

    Spec §Security: bridges must redact tokens from ``source_metadata``
    before persisting.
    """
    if not metadata:
        return None
    return {k: v for k, v in metadata.items() if k.lower() not in _REDACT_KEYS}
