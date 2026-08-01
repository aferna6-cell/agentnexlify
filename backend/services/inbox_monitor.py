"""Continuous Gmail inbox monitoring — poll, bridge, triage.

Designed to be called from the 5-min automation tier (orchestrator wires
the schedule; this module only exposes the entry point). For every tenant
with a connected Gmail integration AND the email bridge toggled on
(``os_inbound_bridge`` per-tenant config), pulls new inbox messages since
the last Gmail ``historyId`` cursor, feeds each one through
``os_inbound_bridge.bridge_email`` (idempotent on ``source_ref`` — safe to
re-poll), then runs AI triage on anything that actually got bridged.

Per-tenant errors are isolated: one tenant's failure is logged and skipped,
never stops the loop for the rest.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services import gmail_connector, inbound_email_verify, inbox_triage, os_inbound_bridge

logger = logging.getLogger(__name__)

_INITIAL_POLL_MAX_RESULTS = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_inbox_poll() -> int:
    """Poll every gmail-connected, bridge-enabled tenant. Returns the total
    number of new inbound messages ingested across all tenants."""
    db = get_service_supabase()
    try:
        result = (
            db.table("integrations")
            .select("tenant_id, metadata")
            .eq("provider", gmail_connector.PROVIDER)
            .execute()
        )
    except Exception:
        logger.exception("inbox_monitor: gmail integrations query failed")
        return 0

    total_ingested = 0
    for row in result.data or []:
        tenant_id = row.get("tenant_id")
        if not tenant_id:
            continue
        try:
            if not os_inbound_bridge.is_bridge_enabled(db, tenant_id, "email"):
                continue
            total_ingested += await _poll_tenant(db, tenant_id, row.get("metadata") or {})
        except Exception:
            logger.exception("inbox_monitor: poll failed tenant_id=%s", tenant_id)
            continue

    return total_ingested


async def _poll_tenant(db: Any, tenant_id: str, metadata: dict) -> int:
    history_id = metadata.get("history_id")
    own_email = str(metadata.get("email_address") or "").strip().lower()

    if history_id:
        message_ids, latest_history_id = gmail_connector.list_history(tenant_id, history_id)
        if latest_history_id == gmail_connector.HISTORY_EXPIRED:
            message_ids, latest_history_id = _reseed(tenant_id)
    else:
        message_ids, latest_history_id = _reseed(tenant_id)

    ingested = 0
    for message_id in message_ids:
        parsed = gmail_connector.get_message(tenant_id, message_id)
        if not parsed:
            continue

        sender = str(parsed.get("sender_email") or "").strip().lower()
        if own_email and sender == own_email:
            continue  # skip messages the tenant sent themselves

        inbound_kind = (
            "auto_reply"
            if inbound_email_verify.is_auto_reply(parsed.get("headers"))
            else "normal"
        )

        try:
            bridged = await os_inbound_bridge.bridge_email(
                db=db,
                client_id=tenant_id,
                email_thread_id=parsed.get("thread_id") or message_id,
                provider_message_id=parsed.get("provider_message_id") or message_id,
                user_content=parsed.get("body_text", ""),
                sender_metadata={
                    "from": parsed.get("sender_email", ""),
                    "from_name": parsed.get("sender_name", ""),
                    "subject": parsed.get("subject", ""),
                    "provider": "gmail",
                },
                inbound_kind=inbound_kind,
            )
        except Exception:
            logger.exception(
                "inbox_monitor: bridge_email failed tenant_id=%s message_id=%s",
                tenant_id,
                message_id,
            )
            continue

        if bridged is None:
            # Bridge disabled mid-loop, or already ingested on a prior poll —
            # either way, nothing new to triage.
            continue

        ingested += 1

        if bridged.get("action") == "skipped_auto_reply":
            continue

        os_thread_id = (bridged.get("user_message") or {}).get("thread_id")
        if not os_thread_id:
            continue

        try:
            await inbox_triage.triage_inbound_email(
                db, tenant=tenant_id, parsed_email=parsed, os_thread_id=os_thread_id
            )
        except Exception:
            logger.exception(
                "inbox_monitor: triage failed tenant_id=%s message_id=%s",
                tenant_id,
                message_id,
            )

    updates: dict[str, Any] = {"last_poll_at": _now_iso()}
    if latest_history_id and latest_history_id != gmail_connector.HISTORY_EXPIRED:
        updates["history_id"] = latest_history_id
    gmail_connector.update_metadata(tenant_id, updates)

    return ingested


def _reseed(tenant_id: str) -> tuple[list[str], str | None]:
    """No usable history cursor (first poll ever, or an expired one) —
    pull the most recent inbox messages and seed a fresh cursor from the
    current profile. ``bridge_email``'s source_ref idempotency makes it
    safe to re-list messages already ingested on a prior pass."""
    profile = gmail_connector.get_profile(tenant_id)
    message_ids = gmail_connector.list_recent_message_ids(
        tenant_id, max_results=_INITIAL_POLL_MAX_RESULTS
    )
    return message_ids, profile.get("historyId")
