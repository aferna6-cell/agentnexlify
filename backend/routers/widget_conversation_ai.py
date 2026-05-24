"""Widget conversation AI helpers: tag extraction, categorization, action items.

Extracted from widget_lead_helpers.py (god class split 2026-05-24).
Re-exported via widget_lead_helpers for backward compatibility with existing
test patches (e.g. `patch("backend.routers.widget_lead_helpers._extract_tags_from_conversation")`).

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not add
a future-annotations import here.
"""

import json
import logging
from typing import Any

import anthropic

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages_sync
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_TAGS = [
    "New Lead", "Pricing Question", "Complaint",
    "Appointment Request", "Urgent", "Follow-up Needed",
]


def _extract_tags_from_conversation(messages: list[dict[str, str]]) -> list[str]:
    """Use Claude to extract auto-tags from conversation messages.

    Returns a list of short tags like "interested in: kitchen remodel",
    "budget: high", "timeline: urgent", "service: plumbing".
    """
    if not messages or len(messages) < 2:
        return []

    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        resp = call_claude_messages_sync(
            operation="widget.extract_tags",
            model=MODEL,
            max_tokens=200,
            temperature=0,
            system=(
                "Extract business-relevant tags from this chat conversation between a visitor and a business AI assistant. "
                "Return ONLY a JSON array of short tag strings. Tags should capture: "
                "service interests (e.g. 'interested in: kitchen remodel'), "
                "budget level (e.g. 'budget: high'), "
                "timeline urgency (e.g. 'timeline: urgent', 'timeline: 3 months'), "
                "and any other business-relevant signals (e.g. 'returning customer', 'referred by friend'). "
                "If no meaningful tags can be extracted, return []. Max 5 tags. Keep each tag under 40 chars."
            ),
            messages=[{"role": "user", "content": transcript}],
            timeout=30.0,
            metadata={"message_count": len(messages)},
        )
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tags = json.loads(raw)
        if isinstance(tags, list):
            return [str(t)[:40] for t in tags if isinstance(t, str)][:5]
    except json.JSONDecodeError:
        logger.warning("tag_extraction: Claude returned non-JSON response")
    except anthropic.APIError as e:
        logger.error("tag_extraction: Claude API error — %s", e)
    except Exception:
        logger.warning("tag_extraction: unexpected failure", exc_info=True)
    return []


def _categorize_conversation(tenant_id: str, session_id: str, messages: list[dict]) -> None:
    """Background task: AI auto-categorize conversation into preset business tags."""
    if not messages or len(messages) < 3:
        return

    db = get_service_supabase()
    try:
        tag_defs = (
            tenant_select(db, "tenant_tag_definitions", tenant_id, "tag_name")
            .eq("is_enabled", True)
            .execute()
        )
        available_tags = [t["tag_name"] for t in (tag_defs.data or [])]
    except Exception:
        available_tags = SYSTEM_TAGS

    if not available_tags:
        available_tags = SYSTEM_TAGS

    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        resp = call_claude_messages_sync(
            operation="widget.categorize_conversation",
            model=MODEL,
            max_tokens=100,
            temperature=0,
            system=(
                "Categorize this chat conversation into 1-3 tags from this list ONLY:\n"
                + ", ".join(available_tags)
                + "\n\nReturn ONLY a JSON array of matching tag names. "
                "If none match, return []. Use exact tag names from the list."
            ),
            messages=[{"role": "user", "content": transcript}],
            timeout=30.0,
            metadata={"tenant_id": tenant_id, "session_id": session_id, "tag_count": len(available_tags)},
        )
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tags = json.loads(raw)
        if not isinstance(tags, list) or not tags:
            return

        valid_tags = [t for t in tags if isinstance(t, str) and t in available_tags][:3]
        if not valid_tags:
            return

        conv = (
            tenant_select(db, "conversations", tenant_id, "tags")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        existing = []
        if conv.data:
            existing = conv.data[0].get("tags") or []

        merged = list(set(existing + valid_tags))
        tenant_update(db, "conversations", tenant_id, {"tags": merged}).eq(
            "session_id", session_id
        ).execute()

    except json.JSONDecodeError:
        logger.warning("conversation_categorize: non-JSON response")
    except anthropic.APIError as e:
        logger.warning("conversation_categorize: API error — %s", e)
    except Exception:
        logger.warning("conversation_categorize: unexpected failure", exc_info=True)


def _extract_action_items(tenant_id: str, session_id: str, messages: list[dict]) -> None:
    """Background task: AI extracts actionable items from conversation."""
    if not messages or len(messages) < 4:
        return

    transcript_lines = []
    for msg in messages[-20:]:
        role = "Visitor" if msg["role"] == "user" else "Agent"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        resp = call_claude_messages_sync(
            operation="widget.extract_action_items",
            model=MODEL,
            max_tokens=300,
            temperature=0,
            system=(
                "Extract actionable items from this business chat conversation. "
                "Action items are things the business needs to DO: send a quote, "
                "schedule a follow-up, prepare a document, call someone back, etc.\n\n"
                "Return ONLY a JSON array of objects with these fields:\n"
                '- "description": what needs to be done (max 100 chars)\n'
                '- "priority": "low", "medium", or "high"\n'
                '- "due_hint": natural language due date if mentioned, or null\n\n'
                "If no action items exist, return []. Max 3 items."
            ),
            messages=[{"role": "user", "content": transcript}],
            timeout=30.0,
            metadata={"tenant_id": tenant_id, "session_id": session_id, "message_count": len(messages)},
        )
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        items = json.loads(raw)
        if not isinstance(items, list) or not items:
            return

        db = get_service_supabase()

        conv = (
            tenant_select(db, "conversations", tenant_id, "id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        conv_id = conv.data[0]["id"] if conv.data else None

        for item in items[:3]:
            if not isinstance(item, dict) or not item.get("description"):
                continue
            data: dict[str, Any] = {
                "tenant_id": tenant_id,
                "description": str(item["description"])[:500],
                "priority": item.get("priority", "medium") if item.get("priority") in ("low", "medium", "high") else "medium",
            }
            if conv_id:
                data["conversation_id"] = conv_id
            tenant_insert(db, "action_items", tenant_id, data).execute()

    except json.JSONDecodeError:
        logger.warning("action_item_extract: non-JSON response")
    except anthropic.APIError as e:
        logger.warning("action_item_extract: API error — %s", e)
    except Exception:
        logger.warning("action_item_extract: unexpected failure", exc_info=True)
