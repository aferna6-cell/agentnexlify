"""Call intelligence: tenant lookup, AI summary, action item extraction.

Pulled out of `backend.routers.calls` so the router stays focused on HTTP
glue. Functions here own the Claude API call, JSON parsing, and Supabase
writes for voice-call post-processing.
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)

logger = logging.getLogger(__name__)


def find_tenant_by_phone(phone: str) -> dict | None:
    """Look up tenant by their configured notification_phone or Twilio number.

    Same pattern as twilio_webhooks.py._find_tenant_by_phone.
    """
    db = get_service_supabase()
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, owner_email, notification_phone, sms_notifications_enabled")
            .limit(50)
            .execute()
        )
    except Exception:
        logger.exception("Failed to query tenants for phone lookup: %s", phone)
        return None

    for tenant in result.data or []:
        tenant_phone = tenant.get("notification_phone")
        if not tenant_phone:
            continue
        # Normalize for comparison (strip spaces, dashes)
        norm_tenant = tenant_phone.replace(" ", "").replace("-", "")
        norm_phone = phone.replace(" ", "").replace("-", "")
        if norm_tenant.endswith(norm_phone[-10:]) or norm_phone.endswith(norm_tenant[-10:]):
            return tenant
    return None


async def generate_call_summary(
    call_id: str,
    tenant_id: str,
    lead_id: str | None,
    transcript_text: str,
) -> None:
    """Generate an AI summary of a call transcript and store it.

    Calls Claude to produce:
    - A one-paragraph summary
    - Action items (list)
    - Caller sentiment (positive/neutral/negative)
    - Suggested follow-up

    Then updates the call record and inserts action items into action_items table.
    This runs as a background task so it does not block the webhook response.
    """
    if not transcript_text or not transcript_text.strip():
        logger.warning("Skipping summary generation for call %s: empty transcript", call_id)
        return

    prompt = (
        "Analyze this phone call transcript and provide:\n"
        "1. A one-paragraph summary\n"
        "2. Action items (list)\n"
        "3. Caller sentiment (positive/neutral/negative)\n"
        "4. Suggested follow-up\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "action_items": ["item 1", "item 2"],\n'
        '  "sentiment": "positive|neutral|negative",\n'
        '  "follow_up": "..."\n'
        "}\n\n"
        f"Transcript:\n{transcript_text}"
    )

    try:
        llm_result = await call_claude_messages(
            operation="calls.generate_summary",
            model=resolve_string_setting("voice_chat_model", "claude-sonnet-4-6"),
            max_tokens=max(600, resolve_int_setting("voice_chat_max_tokens", 160) * 3),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            timeout=30.0,
            metadata={
                "tenant_id": tenant_id,
                "call_id": call_id,
                "transcript_chars": len(transcript_text),
            },
        )
        raw_text = llm_result.text.strip()
    except Exception:
        logger.exception("Claude API call failed for call summary, call %s", call_id)
        return

    # Parse the JSON response from Claude
    summary = ""
    action_items: list[str] = []
    sentiment = "neutral"
    follow_up = ""

    try:
        # Extract JSON from the response (Claude may wrap it in markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            parsed = json.loads(json_match.group())
            summary = parsed.get("summary", "")
            action_items = parsed.get("action_items", [])
            raw_sentiment = parsed.get("sentiment", "neutral").lower().strip()
            if raw_sentiment in ("positive", "neutral", "negative"):
                sentiment = raw_sentiment
            else:
                sentiment = "neutral"
            follow_up = parsed.get("follow_up", "")
        else:
            logger.warning("No JSON found in Claude response for call %s, using raw text", call_id)
            summary = raw_text[:500]
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Failed to parse Claude summary JSON for call %s: %s", call_id, exc)
        summary = raw_text[:500]

    # Build action_taken from follow-up and action items
    action_taken_parts: list[str] = []
    if follow_up:
        action_taken_parts.append(f"Follow-up: {follow_up}")
    if action_items:
        action_taken_parts.append("Action items: " + "; ".join(action_items))
    action_taken = " | ".join(action_taken_parts) if action_taken_parts else None

    # Update the call record with summary, sentiment, and action_taken
    db = get_service_supabase()
    try:
        update_data: dict[str, Any] = {
            "summary": summary,
            "sentiment": sentiment,
        }
        if action_taken:
            update_data["action_taken"] = action_taken

        db.table("calls").update(update_data).eq("id", call_id).eq("tenant_id", tenant_id).execute()
        logger.info(
            "Updated call %s with AI summary (sentiment=%s, %d action items)",
            call_id, sentiment, len(action_items),
        )
    except Exception:
        logger.exception("Failed to update call %s with AI summary", call_id)

    # Insert action items into action_items table
    if action_items:
        await insert_call_action_items(
            tenant_id=tenant_id,
            lead_id=lead_id,
            call_id=call_id,
            items=action_items,
        )


async def insert_call_action_items(
    tenant_id: str,
    lead_id: str | None,
    call_id: str,
    items: list[str],
) -> None:
    """Insert action items extracted from a call into the action_items table.

    Phone call action items are always high priority since they represent
    direct customer communication.
    """
    if not items:
        return

    db = get_service_supabase()
    inserted = 0
    for item_text in items:
        if not item_text or not item_text.strip():
            continue
        row: dict[str, Any] = {
            "tenant_id": tenant_id,
            "description": item_text.strip()[:500],
            "priority": "high",
            "status": "pending",
        }
        if lead_id:
            row["lead_id"] = lead_id
        try:
            db.table("action_items").insert(row).execute()
            inserted += 1
        except Exception:
            logger.exception(
                "Failed to insert action item for call %s: %s",
                call_id, item_text[:80],
            )
    if inserted:
        logger.info("Inserted %d action items from call %s for tenant %s", inserted, call_id, tenant_id)

    # Log activity for the action items creation
    log_activity(
        tenant_id=tenant_id,
        activity_type="call_action_items",
        description=f"AI extracted {inserted} action item(s) from phone call",
        lead_id=lead_id,
        metadata={"call_id": call_id, "action_item_count": inserted},
    )
