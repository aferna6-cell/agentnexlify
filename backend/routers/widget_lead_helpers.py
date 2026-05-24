"""Widget lead helpers: extraction, capture, enrichment orchestration.

Extracted from the widget_helpers.py god class (1,673 lines → split 2026-04-18).
Further split 2026-05-24 — conversation AI helpers moved to
widget_conversation_ai.py, owner notifications moved to
widget_lead_notifications.py.

Callers: widget_chat.py, widget_lead.py.

Multi-tenant invariant: leads table uses `client_id` (NOT tenant_id) and
`status` (NOT lead_stage). See docs/dev-knowledge/schema-log.md.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.routers.widget_conversation_ai import (
    SYSTEM_TAGS,
    _categorize_conversation,
    _extract_action_items,
    _extract_tags_from_conversation,
)
from backend.routers.widget_lead_notifications import (
    _send_new_lead_email_notification,
    _send_new_lead_sms_notification,
)
from backend.services.activity import log_activity
from backend.services.lead_scoring import score_lead_background
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

# AI model constant (mirrors widget_chat_helpers.MODEL for leaf callers that only import this module)
MODEL = "claude-sonnet-4-6"

# Re-exports so unused-import linters stay quiet and downstream patches keep working.
__all__ = [
    "MODEL",
    "SYSTEM_TAGS",
    "_build_conversation_summary",
    "_capture_leads_from_session",
    "_categorize_conversation",
    "_enrich_lead_from_message",
    "_extract_action_items",
    "_extract_lead_info",
    "_extract_service_interest",
    "_extract_tags_from_conversation",
    "_send_new_lead_email_notification",
    "_send_new_lead_sms_notification",
]

# ---------------------------------------------------------------------------
# Lead extraction patterns
# ---------------------------------------------------------------------------

NAME_RE = re.compile(
    r"(?:i'm|im|i am|my name is|this is|name's|call me)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    re.IGNORECASE,
)
# Standalone name: entire message is 1-3 capitalized words (e.g. "John Smith")
STANDALONE_NAME_RE = re.compile(
    r"^([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,2})\.?$"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}(?![a-zA-Z])")
PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[-.\s]?)?"       # optional country code: +1, +44, +91
    r"\(?\d{2,4}\)?"               # area/city code (2-4 digits, optional parens)
    r"[-.\s]?\d{2,4}"              # number group 2
    r"[-.\s]?\d{2,4}"              # number group 3
    r"(?:[-.\s]?\d{1,4})?"         # optional group 4 (longer intl numbers)
)

# Map managed-agent schema field → live `leads` table column.
# Fields the agent returns but we don't merge: source (set at lead creation).
_ENRICHMENT_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "interest": "areas_of_interest",  # live schema uses areas_of_interest
    "timeline": "timeline",
    "budget": "budget",
}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_lead_info(text: str) -> dict[str, str]:
    """Extract name, email, and phone from a user message via regex."""
    info: dict[str, str] = {}
    name_match = NAME_RE.search(text)
    if name_match:
        info["name"] = name_match.group(1).strip()
    elif STANDALONE_NAME_RE.match(text.strip()):
        info["name"] = STANDALONE_NAME_RE.match(text.strip()).group(1)
    # Strip spaces around @ to handle "sara@ test.com" or "john @ gmail.com"
    email_match = EMAIL_RE.search(re.sub(r"\s*@\s*", "@", text))
    if email_match:
        email = email_match.group(0).strip().lower()
        if " " not in email and "@" in email and "." in email.split("@")[1]:
            info["email"] = email
    phone_match = PHONE_RE.search(text)
    if phone_match:
        raw = phone_match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 7 <= len(digits) <= 15:
            info["phone"] = raw
    return info


def _extract_service_interest(messages: list[dict]) -> str | None:
    """Extract the visitor's primary service interest from user messages.
    Uses simple keyword matching — no AI call to keep it fast."""
    user_texts = " ".join(
        msg["content"].lower() for msg in messages if msg["role"] == "user"
    )
    if len(user_texts) < 20:
        return None

    interests = []
    keywords = {
        "quote": "requesting a quote",
        "estimate": "requesting an estimate",
        "price": "pricing inquiry",
        "cost": "pricing inquiry",
        "appointment": "booking appointment",
        "schedule": "scheduling",
        "repair": "repair service",
        "install": "installation",
        "consult": "consultation",
        "emergency": "emergency service",
        "order": "placing an order",
        "reserv": "reservation",
        "book": "booking",
    }
    for kw, interest in keywords.items():
        if kw in user_texts:
            interests.append(interest)

    return interests[0] if interests else None


def _build_conversation_summary(messages: list[dict[str, str]]) -> str | None:
    """Build a brief summary of the conversation from user messages.
    Returns a 1-2 sentence summary or None if too short."""
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if len(user_msgs) < 2:
        return None
    first = user_msgs[0][:150].strip()
    last = user_msgs[-1][:150].strip() if len(user_msgs) > 1 else ""
    if last and last != first:
        return f"{first} ... {last}"
    return first if len(first) > 20 else None


# ---------------------------------------------------------------------------
# Lead capture + notifications
# ---------------------------------------------------------------------------


async def _capture_leads_from_session(
    tenant_id: str, session_id: str, conversation_id: str
) -> None:
    """Background task: scan all user messages in session for contact info,
    create or update a lead.  Deduplicates by email + client_id.

    NOTE: Live Supabase leads table uses the archive schema:
      client_id (not tenant_id), status (not lead_stage), no source column.
    """
    # Import here to avoid circular dependency at module load time
    from backend.routers.widget_chat_helpers import _load_chat_history

    try:
        logger.info(
            "lead_capture START: tenant=%s session=%s conv=%s",
            tenant_id, session_id, conversation_id,
        )
        messages = _load_chat_history(tenant_id, session_id, limit=50)
        logger.info("lead_capture: loaded %d messages from session", len(messages))

        # Scan ALL user messages for contact info
        combined: dict[str, str] = {}
        for msg in messages:
            if msg["role"] != "user":
                continue
            extracted = _extract_lead_info(msg["content"])
            if extracted:
                logger.info(
                    "lead_capture: extracted from message %r → %s",
                    msg["content"][:80], extracted,
                )
            combined.update(extracted)

        logger.info("lead_capture: combined info = %s", combined)

        if not combined.get("email") and not combined.get("phone"):
            logger.info("lead_capture: no email or phone found, skipping")
            return

        db = get_service_supabase()

        # Dedup: check by email + client_id first
        if combined.get("email"):
            logger.info(
                "lead_capture: dedup check — email=%s client_id=%s",
                combined["email"], tenant_id,
            )
            try:
                existing = (
                    tenant_select(db, "leads", tenant_id, "id, name, phone, areas_of_interest, conversation_summary")
                    .eq("email", combined["email"])
                    .limit(1)
                    .execute()
                )
            except Exception as dedup_err:
                logger.error(
                    "lead_capture: dedup query FAILED: %s", dedup_err, exc_info=True,
                )
                existing = type("R", (), {"data": []})()

            if existing.data:
                lead = existing.data[0]
                logger.info("lead_capture: existing lead found id=%s", lead["id"])
                updates: dict[str, str] = {}
                suggestions: dict[str, dict] = {}
                for field, db_field in [("name", "name"), ("phone", "phone")]:
                    if combined.get(field):
                        if not lead.get(db_field):
                            updates[db_field] = combined[field]
                        elif lead[db_field] != combined[field]:
                            suggestions[db_field] = {"old": lead[db_field], "new": combined[field]}
                if combined.get("service_interest"):
                    if not lead.get("areas_of_interest"):
                        updates["areas_of_interest"] = combined["service_interest"]
                    elif lead["areas_of_interest"] != combined["service_interest"]:
                        suggestions["areas_of_interest"] = {"old": lead["areas_of_interest"], "new": combined["service_interest"]}
                summary = _build_conversation_summary(messages)
                if summary and not lead.get("conversation_summary"):
                    updates["conversation_summary"] = summary
                if suggestions:
                    try:
                        log_activity(
                            tenant_id=tenant_id,
                            activity_type="lead_suggestion",
                            description=f"AI suggests updating {', '.join(suggestions.keys())} for {lead.get('name') or lead.get('email') or 'lead'}",
                            lead_id=lead["id"],
                            metadata={"suggestions": suggestions, "source": "widget"},
                        )
                        logger.info("lead_capture: created suggestion for lead %s: %s", lead["id"], list(suggestions.keys()))
                    except Exception:
                        logger.warning("lead_capture: failed to create suggestion", exc_info=True)
                if updates:
                    tenant_update(db, "leads", tenant_id, updates).eq("id", lead["id"]).execute()
                    log_activity(
                        tenant_id=tenant_id,
                        activity_type="lead_updated",
                        description=f"Lead info captured: {', '.join(updates.keys())}",
                        lead_id=lead["id"],
                        metadata={"source": "widget", "fields": list(updates.keys())},
                    )
                    logger.info("lead_capture: updated lead %s fields=%s", lead["id"], list(updates.keys()))
                    fire_event_background(tenant_id, "lead.updated", {
                        "lead_id": lead["id"],
                        "updated_fields": list(updates.keys()),
                        "source": "widget",
                    })
                try:
                    tags = _extract_tags_from_conversation(messages)
                    if tags:
                        tenant_update(db, "leads", tenant_id, {"tags": tags}).eq("id", lead["id"]).execute()
                        logger.info("lead_capture: tagged existing lead %s with %s", lead["id"], tags)
                except Exception:
                    logger.warning("lead_capture: tag extraction failed for lead %s", lead["id"], exc_info=True)
                if conversation_id:
                    try:
                        from uuid import UUID
                        UUID(conversation_id)
                        tenant_update(db, "conversations", tenant_id, {"lead_captured": True}).eq("id", conversation_id).execute()
                        logger.info("lead_capture: set lead_captured=true on conversation %s (existing lead)", conversation_id)
                    except (ValueError, AttributeError):
                        logger.warning("lead_capture: conversation_id %r is not a UUID, skipping lead_captured update", conversation_id)
                    except Exception:
                        logger.warning("lead_capture: failed to update lead_captured on conversation %s", conversation_id, exc_info=True)
                return

        # Extract service interest from conversation context
        service_interest = _extract_service_interest(messages)

        # Create new lead — live schema: client_id, status (not tenant_id, lead_stage)
        lead_fields: dict[str, Any] = {
            "client_id": tenant_id,
            "status": "new",
            "source": "widget",
            "enrichment_source": "regex",
        }
        for key in ("name", "email", "phone"):
            if combined.get(key):
                lead_fields[key] = combined[key]
        if service_interest:
            lead_fields["areas_of_interest"] = service_interest
        summary = _build_conversation_summary(messages)
        if summary:
            lead_fields["conversation_summary"] = summary

        try:
            from uuid import UUID
            UUID(conversation_id)
            lead_fields["conversation_id"] = conversation_id
        except (ValueError, AttributeError):
            logger.debug("lead_capture: conversation_id %r is not a UUID, omitting", conversation_id)

        logger.info("lead_capture: inserting new lead with fields=%s", lead_fields)
        try:
            result = tenant_insert(db, "leads", tenant_id, lead_fields).execute()
        except Exception as insert_err:
            logger.error(
                "lead_capture: INSERT FAILED: %s — fields were %s",
                insert_err, lead_fields, exc_info=True,
            )
            return

        if result.data:
            lead_id = result.data[0]["id"]
            lead_name = combined.get("name", "New visitor")
            logger.info("lead_capture: SUCCESS lead_id=%s client_id=%s", lead_id, tenant_id)

            try:
                log_activity(
                    tenant_id=tenant_id,
                    activity_type="lead_created",
                    description=f"New lead from widget: {lead_name}",
                    lead_id=lead_id,
                    metadata={"source": "widget", "fields": list(lead_fields.keys())},
                )
            except Exception:
                logger.warning("lead_capture: log_activity failed", exc_info=True)

            try:
                fire_event_background(tenant_id, "lead.created", {
                    "lead_id": lead_id,
                    "name": combined.get("name"),
                    "email": combined.get("email"),
                    "phone": combined.get("phone"),
                    "source": "widget",
                })
            except Exception:
                logger.warning("lead_capture: fire_event_background failed", exc_info=True)

            logger.info("lead_capture: about to call trigger_sequence for lead %s", lead_id)
            try:
                from backend.services.automation_engine import trigger_sequence
                await trigger_sequence(tenant_id, lead_id, "new_lead")
                logger.info("lead_capture: trigger_sequence completed for lead %s", lead_id)
            except Exception:
                logger.warning("Failed to trigger automation for lead %s", lead_id, exc_info=True)

            try:
                from backend.routers.email_sequences import enroll_lead_in_sequences
                await enroll_lead_in_sequences(tenant_id, lead_id)
                logger.info("lead_capture: enroll_lead_in_sequences completed for lead %s", lead_id)
            except Exception:
                logger.warning("lead_capture: enroll_lead_in_sequences failed for lead %s", lead_id, exc_info=True)

            logger.info("SMS_TRIGGER: about to call SMS notification for lead %s email=%s", lead_id, combined.get("email"))
            try:
                await _send_new_lead_sms_notification(tenant_id, lead_name, combined)
            except Exception:
                logger.error("SMS_TRIGGER: FAILED for lead %s", lead_id, exc_info=True)

            try:
                await _send_new_lead_email_notification(tenant_id, lead_name, combined)
            except Exception:
                logger.error("EMAIL_TRIGGER: FAILED for lead %s", lead_id, exc_info=True)

            try:
                tags = _extract_tags_from_conversation(messages)
                if tags:
                    tenant_update(db, "leads", tenant_id, {"tags": tags}).eq("id", lead_id).execute()
                    logger.info("lead_capture: tagged new lead %s with %s", lead_id, tags)
            except Exception:
                logger.warning("lead_capture: tag extraction failed for new lead %s", lead_id, exc_info=True)

            try:
                score_lead_background(lead_id)
            except Exception:
                logger.warning("Failed to score lead %s in background", lead_id, exc_info=True)

            if conversation_id:
                try:
                    from uuid import UUID
                    UUID(conversation_id)
                    tenant_update(db, "conversations", tenant_id, {"lead_captured": True}).eq("id", conversation_id).execute()
                    logger.info("lead_capture: set lead_captured=true on conversation %s", conversation_id)
                except (ValueError, AttributeError):
                    logger.warning("lead_capture: conversation_id %r is not a UUID, skipping lead_captured update", conversation_id)
                except Exception:
                    logger.warning("lead_capture: failed to update lead_captured on conversation %s", conversation_id, exc_info=True)
        else:
            logger.warning("lead_capture: INSERT returned no data — result=%s", result)

    except Exception:
        logger.error("lead_capture FAILED: session=%s tenant=%s", session_id, tenant_id, exc_info=True)


# ---------------------------------------------------------------------------
# Structured-extractor lead enrichment (background task)
# ---------------------------------------------------------------------------


def _enrich_lead_from_message(
    tenant_id: str,
    session_id: str,
    raw_text: str,
    regex_extracted: dict[str, str],
) -> None:
    """Background task: run structured_extractor on a single user message
    and merge any new fields into the existing lead row.

    Gated by `widget_configs.enable_structured_lead_parser` at the call
    site (backend/routers/widget_chat.py). Failure modes:

      - Extractor raises ValueError (parse failure) → log warning, return.
      - Extractor raises any other exception → log exception, return.
      - No safe dedup key (no email, no phone in either dict) → log info,
        return.
      - Lead row not found yet (race with `_capture_leads_from_session`)
        → log info, return. The next message will retry naturally.

    NEVER raises. FastAPI BackgroundTasks would propagate exceptions
    into the response cycle if it did.

    Merge policy: regex wins on fields both parsers populated. Extractor
    only fills fields the regex left blank — regex is literal and cheap,
    extractor is best-effort.
    """
    from backend.services.structured_extractor import extract_structured

    try:
        result = extract_structured(
            tenant_id=tenant_id,
            raw_text=raw_text,
            target_schema="lead",
        )
    except ValueError as exc:
        logger.warning(
            "lead_enrichment: structured_extractor parse failed for session=%s: %s",
            session_id, exc,
        )
        return
    except Exception:
        logger.exception(
            "lead_enrichment: unexpected extractor error for session=%s",
            session_id,
        )
        return

    merged: dict[str, str] = dict(regex_extracted)
    fields_added: list[str] = []
    for agent_key in _ENRICHMENT_FIELD_MAP:
        val = result.get(agent_key)
        if not val:
            continue
        if not isinstance(val, str):
            val = str(val).strip()
        if not val:
            continue
        if not merged.get(agent_key):
            merged[agent_key] = val
            fields_added.append(agent_key)

    if not fields_added:
        return

    lookup_email = merged.get("email")
    lookup_phone = merged.get("phone")
    if not lookup_email and not lookup_phone:
        logger.info(
            "lead_enrichment: no email/phone in merged dict for session=%s, skipping",
            session_id,
        )
        return

    db = get_service_supabase()
    try:
        if lookup_email:
            existing = (
                tenant_select(db, "leads", tenant_id, "id, name, email, phone, areas_of_interest, timeline, budget")
                .eq("email", lookup_email)
                .limit(1)
                .execute()
            )
        else:
            existing = (
                tenant_select(db, "leads", tenant_id, "id, name, email, phone, areas_of_interest, timeline, budget")
                .eq("phone", lookup_phone)
                .limit(1)
                .execute()
            )
    except Exception:
        logger.warning(
            "lead_enrichment: lead lookup failed for session=%s", session_id, exc_info=True,
        )
        return

    if not existing.data:
        logger.info(
            "lead_enrichment: no lead found for session=%s (race with regex capture, will retry)",
            session_id,
        )
        return

    lead = existing.data[0]
    lead_id = lead["id"]

    update_payload: dict[str, str] = {}
    truly_added: list[str] = []
    for agent_key in fields_added:
        db_col = _ENRICHMENT_FIELD_MAP[agent_key]
        if not lead.get(db_col):
            update_payload[db_col] = merged[agent_key]
            truly_added.append(agent_key)

    if not update_payload:
        return

    update_payload["enrichment_source"] = "ai"

    try:
        tenant_update(db, "leads", tenant_id, update_payload).eq("id", lead_id).execute()
    except Exception:
        logger.warning(
            "lead_enrichment: leads.update failed for lead=%s session=%s",
            lead_id, session_id, exc_info=True,
        )
        return

    try:
        log_activity(
            tenant_id=tenant_id,
            activity_type="lead_enriched",
            description=f"Lead fields enriched by structured_extractor: {', '.join(truly_added)}",
            lead_id=lead_id,
            metadata={
                "session_id": session_id,
                "fields_added": truly_added,
                "source": "structured_extractor",
            },
        )
    except Exception:
        logger.warning(
            "lead_enrichment: log_activity failed for lead=%s session=%s",
            lead_id, session_id, exc_info=True,
        )
